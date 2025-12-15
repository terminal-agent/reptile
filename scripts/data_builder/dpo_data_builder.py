"""DPO data preparation script for terminal agent training.

This module processes YAML history files and system prompts to create
Direct Preference Optimization (DPO) training data by identifying trajectory
branches as preference pairs (chosen vs rejected).
"""

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yaml
from git import GitCommandError
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from tqdm import tqdm

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autopilot.cli.data import initialize_repo, repo_path
from data_builder.utils import (
  HISTORY_FILE,
  SYSTEM_PROMPT_FILE,
  TEST_FILE,
  TEST_SAMPLES,
  TRAIN_FILE,
  create_mistral_message,
  deduplicate_branches,
  is_invalid_branch,
)

# Constants
# Minimum: system message + at least 1 context turn = 2 messages
MIN_MESSAGES_THRESHOLD = 2


def dpo_data_from_edits(
  yaml_file: str,
  system_prompt_file: str,
  use_summarize_only: bool = False,
) -> Optional[List[Dict[str, Any]]]:
  """Extract DPO preference pairs from YAML history files.

  The key insight: when trajectories branch (traj changes), we have a preference
  point. The context before the branch is shared, and we create chosen/rejected
  pairs based on the diverging paths.

  Args:
      yaml_file: Path to the YAML history file
      system_prompt_file: Path to the system prompt file
      use_summarize_only: If True, only use data that contains summarize steps

  Returns:
      List of DPO data dictionaries with chosen/rejected pairs, or None if invalid
  """
  with open(yaml_file) as f:
    history = yaml.safe_load(f)
  with open(system_prompt_file) as f:
    system_prompt: str = f.read().strip()

  if not history:
    return None

  num_trajectories = history[-1]["traj"] + 1

  # DPO requires multiple trajectories (branches) to create preference pairs
  if num_trajectories == 1:
    return None

  if use_summarize_only:
    if not any("# summary" in item["content"].lower() for item in history):
      print(
        f"[warning, data processor] Skipping {yaml_file} due to no summarize steps"
      )
      return None

  # Group history items by (traj, step) to identify preference points
  # Key: (traj, step), Value: history item
  step_items: Dict[
    int, List[tuple[int, Dict]]
  ] = {}  # step -> [(traj, item), ...]

  for item in history:
    if item["content"] == "":
      return None

    # Normalize roles
    if item["role"] == "terminal":
      item["role"] = "user"
    elif item["role"] == "llm":
      item["role"] = "assistant"

    trajectory, step = item["traj"], item["step"]

    if step not in step_items:
      step_items[step] = []
    step_items[step].append((trajectory, item))

  # Find steps with multiple trajectories (preference points)
  preference_steps: List[Dict[str, Any]] = []
  for step, items in step_items.items():
    if len(items) > 1:
      # Multiple trajectories at this step = preference data point
      # Only include if ALL items at this step are LLM (assistant) steps
      if all(item[1]["role"] == "assistant" for item in items):
        # Sort by trajectory number
        items.sort(key=lambda x: x[0])
        preference_steps.append(
          {
            "step": step,
            "trajectories": items,
          }
        )

  if len(preference_steps) == 0:
    return None

  # Build full trajectories for context extraction
  trajectories: List[List[Dict]] = [[] for _ in range(num_trajectories)]
  prev_trajectory = 0

  for item in history:
    trajectory, step = item["traj"], item["step"]

    if trajectory != prev_trajectory:
      # Copy the previous trajectory up to the branch point
      trajectories[trajectory].extend(trajectories[prev_trajectory][:step])
      prev_trajectory = trajectory

    trajectories[trajectory].append(item)

  # Create DPO samples from preference steps
  dpo_samples = []

  for pref_step_info in preference_steps:
    step = pref_step_info["step"]
    traj_items: List[tuple[int, Dict]] = pref_step_info["trajectories"]

    # The last trajectory at this step is the chosen one
    chosen_traj, chosen_item = traj_items[-1]

    # All other trajectories at this step are rejected
    for rejected_traj, rejected_item in traj_items[:-1]:
      # Context: all items before this step in the chosen trajectory
      context = [
        item for item in trajectories[chosen_traj] if item["step"] < step
      ]

      # Add prefix for each item's content
      labeled_context = []
      for i, item in enumerate(context):
        content = item["content"]
        if not content.startswith("<label"):
          content = f"<label:{i}>\n{content}"
        labeled_context.append({"role": item["role"], "content": content})

      chosen_label = f"<label:{step}>\n{chosen_item['content']}"
      rejected_label = f"<label:{step}>\n{rejected_item['content']}"

      # Build the DPO sample
      messages = [
        {"role": "system", "content": system_prompt}
      ] + labeled_context

      chosen = [{"role": chosen_item["role"], "content": chosen_label}]
      rejected = [{"role": rejected_item["role"], "content": rejected_label}]

      dpo_samples.append(
        {
          "messages": messages,
          "chosen": chosen,
          "rejected": rejected,
          "branch_point": step,
          "chosen_traj": chosen_traj,
          "rejected_traj": rejected_traj,
        }
      )

  if len(dpo_samples) == 0:
    return None

  return dpo_samples


def _process_branch_data(
  repo,
  branch: str,
  tokenizer: MistralTokenizer,
  use_summarize_only: bool = False,
  train_on_summarize_only: bool = False,
) -> Optional[List[Dict]]:
  """Process DPO data from a single branch.

  Args:
      repo: Git repository object
      branch: Branch name to process
      tokenizer: Tokenizer for encoding messages
      use_summarize_only: If True, only use data that contains summarize steps
      train_on_summarize_only: If True, only train on messages that contain summarize steps

  Returns:
      List of DPO training data dictionaries or None if invalid
  """
  try:
    repo.git.checkout(f"origin/{branch}")
  except GitCommandError as e:
    print(f"Skipping {branch}: {e}")
    return None

  history_file = os.path.join(repo_path, HISTORY_FILE)
  system_prompt_file = os.path.join(repo_path, SYSTEM_PROMPT_FILE)

  if not os.path.exists(history_file) or not os.path.exists(system_prompt_file):
    return None

  dpo_samples = dpo_data_from_edits(
    yaml_file=history_file,
    system_prompt_file=system_prompt_file,
    use_summarize_only=use_summarize_only,
  )

  if dpo_samples is None:
    return None

  # Filter samples with sufficient context
  dpo_samples = [
    sample
    for sample in dpo_samples
    if len(sample["messages"]) >= MIN_MESSAGES_THRESHOLD
  ]

  if len(dpo_samples) == 0:
    return None

  # Process and add tokenization info
  results: List[Dict] = []
  for sample in dpo_samples:
    # Tokenize the full sequence (messages + chosen)
    full_messages_chosen = sample["messages"] + sample["chosen"]
    full_messages_rejected = sample["messages"] + sample["rejected"]

    tokens_chosen = tokenizer.encode_chat_completion(
      ChatCompletionRequest(
        messages=[
          create_mistral_message(d)
          if i < len(full_messages_chosen) - 1
          else create_mistral_message(d, last_assistant=True)
          for i, d in enumerate(full_messages_chosen)
        ]
      )
    ).tokens

    tokens_rejected = tokenizer.encode_chat_completion(
      ChatCompletionRequest(
        messages=[
          create_mistral_message(d)
          if i < len(full_messages_rejected) - 1
          else create_mistral_message(d, last_assistant=True)
          for i, d in enumerate(full_messages_rejected)
        ]
      )
    ).tokens

    # Determine edit_steps based on train_on_summarize_only flag
    if train_on_summarize_only:
      # Check if chosen or rejected step contains summarize
      edit_steps = []
      if "# summary" in sample["chosen"][0]["content"].lower():
        edit_steps.append(sample["branch_point"])
    else:
      edit_steps = [sample["branch_point"]]

    results.append(
      {
        "branch": branch,
        "messages": sample["messages"],
        "chosen": sample["chosen"],
        "rejected": sample["rejected"],
        "edit_steps": edit_steps,
        "tokens_chosen": len(tokens_chosen),
        "tokens_rejected": len(tokens_rejected),
        "tokens": max(len(tokens_chosen), len(tokens_rejected)),
        "num_steps": len(sample["messages"]),
        "chosen_traj": sample["chosen_traj"],
        "rejected_traj": sample["rejected_traj"],
      }
    )

  return results


def build_training_data(
  tokenizer: MistralTokenizer,
  print_detail: bool = False,
  keep_all_branches: bool = False,
  use_summarize_only: bool = False,
  train_on_summarize_only: bool = False,
  branch: Optional[str] = None,
  tasks_dirs: Optional[List[str]] = None,
  forbidden_prefixes: Optional[List[str]] = None,
) -> List[Dict]:
  """Build DPO training data from repository branches.

  Args:
      tokenizer: Mistral tokenizer for encoding messages
      print_detail: Whether to print detailed statistics
      keep_all_branches: If True, keep all branches in each group. If False, keep only the latest one.
      use_summarize_only: If True, only use data that contains summarize steps
      train_on_summarize_only: If True, only train on messages that contain summarize steps
      branch: If specified, only process this specific branch
      tasks_dirs: List of task directories to filter out. If None, uses default.
      forbidden_prefixes: List of branch prefixes to exclude. If None, uses default.

  Returns:
      List of DPO training data dictionaries
  """
  print(f"Initializing repository at {repo_path}")
  repo = initialize_repo(repo_path)

  origin = repo.remotes.origin
  origin.fetch(prune=True)

  if branch:
    # Process only the specified branch
    branches = [branch]
    print(f"Processing single branch: {branch}")
  else:
    # Process all branches
    branches = [
      ref.remote_head
      for ref in origin.refs
      if ref.remote_head != "HEAD"
      and not is_invalid_branch(
        ref.remote_head,
        tasks_dirs=tasks_dirs,
        forbidden_prefixes=forbidden_prefixes,
      )
    ]
    branches = deduplicate_branches(branches, keep_all=keep_all_branches)

  training_data = []
  skipped_single_traj = 0

  for branch in tqdm(branches):
    data = _process_branch_data(
      repo,
      branch,
      tokenizer,
      use_summarize_only=use_summarize_only,
      train_on_summarize_only=train_on_summarize_only,
    )
    if data:
      training_data.extend(data)
    else:
      skipped_single_traj += 1

  print(f"## Collected {len(training_data)} DPO preference pairs")
  print(
    f"## Skipped {skipped_single_traj} branches (single trajectory or invalid)"
  )
  _print_statistics(training_data, print_detail)
  return training_data


def _print_statistics(training_data: List[Dict], print_detail: bool) -> None:
  """Print statistics about the DPO training data."""
  if len(training_data) == 0:
    print("No DPO data collected!")
    return

  tokens_chosen = [item["tokens_chosen"] for item in training_data]
  tokens_rejected = [item["tokens_rejected"] for item in training_data]
  steps = [item["num_steps"] for item in training_data]

  print("\n## DPO Statistics Summary:")
  print(
    f"{'Metric':<25} {'Chosen Tokens':<15} {'Rejected Tokens':<15} {'Steps':<12}"
  )
  print("-" * 67)
  print(
    f"{'Total samples:':<25} {len(tokens_chosen):<15} {len(tokens_rejected):<15} {len(steps):<12}"
  )
  print(
    f"{'Min:':<25} {np.min(tokens_chosen):<15} {np.min(tokens_rejected):<15} {np.min(steps):<12}"
  )
  print(
    f"{'Max:':<25} {np.max(tokens_chosen):<15} {np.max(tokens_rejected):<15} {np.max(steps):<12}"
  )
  print(
    f"{'Mean:':<25} {np.mean(tokens_chosen):<15.2f} {np.mean(tokens_rejected):<15.2f} {np.mean(steps):<12.2f}"
  )
  print(
    f"{'Median:':<25} {np.median(tokens_chosen):<15} {np.median(tokens_rejected):<15} {np.median(steps):<12}"
  )
  print(
    f"{'95th percentile:':<25} {np.percentile(tokens_chosen, 95):<15.2f} "
    f"{np.percentile(tokens_rejected, 95):<15.2f} {np.percentile(steps, 95):<12.2f}"
  )

  if print_detail:
    print("\n## DPO Data Summary Table:")
    print(f"{'Branch':<50} {'Tokens (C/R)':<15} {'Steps':<6}")
    print("-" * 73)
    for item in training_data:
      tokens_str = f"{item['tokens_chosen']}/{item['tokens_rejected']}"
      print(f"{item['branch']:<50} {tokens_str:<15} {item['num_steps']:<6}")


def main() -> None:
  """Main function to process DPO training data and save to parquet files."""
  parser = argparse.ArgumentParser(
    description="Prepare DPO data for terminal agent training"
  )
  parser.add_argument(
    "--keep-all-branches",
    action="store_true",
    help="Keep all branches in each group instead of only the latest one",
  )
  parser.add_argument(
    "--use-summarize-only",
    action="store_true",
    help="Only use branches that contain summarize steps",
  )
  parser.add_argument(
    "--train-on-summarize-only",
    action="store_true",
    help="Only train on messages that contain summarize steps",
  )
  parser.add_argument(
    "--print-detail", action="store_true", help="Print detailed statistics"
  )
  parser.add_argument(
    "--branch",
    type=str,
    default=None,
    help="Specific branch name to process (e.g., 'django__django-12345-20241101-123456-abcd'). If not specified, all branches will be processed.",
  )
  parser.add_argument(
    "--tasks-dirs",
    type=str,
    nargs="*",
    default=None,
    help="List of task directories to filter out. If not specified, uses default TASKS_DIR.",
  )
  parser.add_argument(
    "--forbidden-prefixes",
    type=str,
    nargs="*",
    default=None,
    help="List of branch prefixes to exclude. If not specified, uses empty list.",
  )
  args = parser.parse_args()

  tokenizer = MistralTokenizer.from_hf_hub("mistralai/Devstral-Small-2507")
  training_data = build_training_data(
    tokenizer,
    print_detail=args.print_detail,
    keep_all_branches=args.keep_all_branches,
    use_summarize_only=args.use_summarize_only,
    train_on_summarize_only=args.train_on_summarize_only,
    branch=args.branch,
    tasks_dirs=args.tasks_dirs,
    forbidden_prefixes=args.forbidden_prefixes,
  )

  if len(training_data) == 0:
    print("No DPO data collected. Exiting without creating files.")
    return

  df = pd.DataFrame(training_data)

  script_path = os.path.dirname(os.path.abspath(__file__))
  if args.use_summarize_only:
    # only train on sessions that contain summarize steps
    if args.train_on_summarize_only:
      # only compute loss on summarize steps
      DATA_DIR = "data/dpo_only_summarize/"
    else:
      DATA_DIR = "data/dpo_summarize/"
  elif args.keep_all_branches:
    # train on all sessions
    DATA_DIR = "data/all_dpo/"
  else:
    # train on unique sessions
    DATA_DIR = "data/unique_dpo/"
  local_dir = os.path.join(script_path, DATA_DIR)
  local_dir = os.path.expanduser(local_dir)

  if not os.path.exists(local_dir):
    os.makedirs(local_dir)

  train_path = os.path.join(local_dir, TRAIN_FILE)
  test_path = os.path.join(local_dir, TEST_FILE)

  df.to_parquet(train_path)
  df[:TEST_SAMPLES].to_parquet(test_path)

  print("\n## Saved DPO data:")
  print(f"  Train: {train_path} ({len(df)} samples)")
  print(f"  Test:  {test_path} ({min(TEST_SAMPLES, len(df))} samples)")


if __name__ == "__main__":
  main()
