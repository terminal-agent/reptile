"""SFT data preparation script for terminal agent training.

This module processes YAML history files and system prompts to create
structured training data for fine-tuning language models.
"""

import argparse
import os
import sys
from collections import Counter
from typing import Dict, List, Optional

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
MIN_MESSAGES_THRESHOLD = 10


def sft_data_from_edits(
  yaml_file: str,
  system_prompt_file: str,
  rejection_sample: bool = False,
  use_summarize_only: bool = False,
  add_prefix: bool = False,
) -> Optional[List[List[Dict[str, str]]]]:
  """Extract SFT data from YAML history and system prompt files.

  Args:
      yaml_file: Path to the YAML history file
      system_prompt_file: Path to the system prompt file
      rejection_sample: If True, sample single-trajectory data. This is used for rejection sampling.
      use_summarize_only: If True, only use data that contains summarize steps
      add_prefix: If True, add prefix to each item['content']
  Returns:
      List of message dictionaries for training, or None if invalid data
  """
  with open(yaml_file) as f:
    history = yaml.safe_load(f)
  with open(system_prompt_file) as f:
    system_prompt: str = f.read().strip()

  num_trajectories = history[-1]["traj"] + 1

  # Skip no-edit data if not rejection sampling
  if not rejection_sample and num_trajectories == 1:
    return None

  # Skip multi-trajectory data if rejection sampling
  if rejection_sample and num_trajectories > 1:
    print(
      f"[warning, data processor] Skipping {yaml_file} due to more than "
      "one trajectory (e.g., summarize, subagent) and rejection sampling"
    )
    return None

  if use_summarize_only:
    if not any("# summary" in item["content"].lower() for item in history):
      print(
        f"[warning, data processor] Skipping {yaml_file} due to no summarize steps"
      )
      return None

  trajectories: List[List[Dict]] = [[] for _ in range(num_trajectories)]
  results: List[List[Dict]] = []

  # we only keep two types of trajectories:
  # 1. the trajectories that call the `summary` tool
  # 2. the latest trajectory, which assumed to be the best trajectory

  # this flag is used to prevent the latest trajectory with `summary` tool call from being added twice
  latest_trajectory_with_summary_added = False

  prev_trajectory, prev_step = 0, -1
  for item in history:
    latest_trajectory_with_summary_added = False
    if item["content"] == "":
      return None

    # Normalize roles
    if item["role"] == "terminal":
      item["role"] = "user"
    elif item["role"] == "llm":
      item["role"] = "assistant"

    trajectory, step = item["traj"], item["step"]

    if trajectory != prev_trajectory:
      if step < prev_step and "# summary" in item["content"].lower():
        # a summarize step happened in the previous trajectory
        # save a copy of previous trajectory as is
        results.append(trajectories[prev_trajectory])
        latest_trajectory_with_summary_added = True
      trajectories[trajectory].extend(trajectories[prev_trajectory][:step])

    prev_trajectory, prev_step = trajectory, step
    trajectories[trajectory].append(item)

  if not latest_trajectory_with_summary_added:
    results.append(trajectories[-1])

  # Add prefix for each item['content'] (optional)
  if add_prefix:
    for i_traj, traj in enumerate(results):
      for i, item in enumerate(traj):
        if not item["content"].startswith("<label"):
          item["content"] = f"<label:{i}>\n{item['content']}"

  return [
    ([{"role": "system", "content": system_prompt}] + traj) for traj in results
  ]


def _process_branch_data(
  repo,
  branch: str,
  tokenizer: MistralTokenizer,
  use_summarize_only: bool = False,
  train_on_summarize_only: bool = False,
) -> Optional[List[Dict]]:
  """Process data from a single branch.

  Args:
      repo: Git repository object
      branch: Branch name to process
      tokenizer: Tokenizer for encoding messages
      use_summarize_only: If True, only use data that contains summarize steps
      train_on_summarize_only: If True, only train on messages that contain summarize steps

  Returns:
      Training data dictionary or None if invalid
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

  multiturn_data = sft_data_from_edits(
    yaml_file=history_file,
    system_prompt_file=system_prompt_file,
    use_summarize_only=use_summarize_only,
  )
  if multiturn_data is None or all(
    len(d) < MIN_MESSAGES_THRESHOLD for d in multiturn_data
  ):
    return None
  multiturn_data = [
    d for d in multiturn_data if len(d) >= MIN_MESSAGES_THRESHOLD
  ]

  for i, d in enumerate(multiturn_data):
    if d[-1]["role"] == "user":
      multiturn_data[i] = d[:-1]

  multiturn_data = [
    [{"content": item["content"], "role": item["role"]} for item in rollout]
    for rollout in multiturn_data
  ]

  results: List[Dict] = []
  for rollout in multiturn_data:
    tokens = tokenizer.encode_chat_completion(
      ChatCompletionRequest(
        messages=[
          create_mistral_message(d)
          if len(rollout) - i > 1
          else create_mistral_message(d, last_assistant=True)
          for i, d in enumerate(rollout)
        ]
      )
    ).tokens
    results.append(
      {
        "branch": branch,
        "messages": rollout,
        "edit_steps": [len(rollout) - 1]
        if train_on_summarize_only
        else list(range(len(rollout))),
        "tokens": len(tokens),
        "num_steps": len(rollout),
      }
    )
  if len(results) == 0:
    return None
  return results


def build_training_data(
  tokenizer: MistralTokenizer,
  print_detail: bool = False,
  keep_all_branches: bool = False,
  use_summarize_only: bool = False,
  train_on_summarize_only: bool = False,
  tasks_dirs: Optional[List[str]] = None,
  forbidden_prefixes: Optional[List[str]] = None,
) -> List[Dict]:
  """Build training data from repository branches.

  Args:
      tokenizer: Mistral tokenizer for encoding messages
      print_detail: Whether to print detailed statistics
      keep_all_branches: If True, keep all branches in each group. If False, keep only the latest one.
      use_summarize_only: If True, only use data that contains summarize steps
      train_on_summarize_only: If True, only train on messages that contain summarize steps
      tasks_dirs: List of task directories to filter out. If None, uses default.
      forbidden_prefixes: List of branch prefixes to exclude. If None, uses default.

  Returns:
      List of training data dictionaries
  """
  print(f"Initializing repository at {repo_path}")
  repo = initialize_repo(repo_path)

  origin = repo.remotes.origin
  origin.fetch(prune=True)

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

  print(f"## Collected {len(training_data)} data")
  _print_statistics(training_data, print_detail)
  return training_data


def _print_statistics(training_data: List[Dict], print_detail: bool) -> None:
  """Print statistics about the training data."""
  tokens = [item["tokens"] for item in training_data]
  steps = [item["num_steps"] for item in training_data]
  branches = [
    branch.split("-202")[0]
    for branch in [item["branch"] for item in training_data]
  ]
  branches_counter = Counter(branches)

  summary_tool_calls = [
    ("summarize(" in "".join(x["content"] for x in item["messages"]))
    for item in training_data
  ]

  print(f"## Branches Count: {branches_counter}")
  print("## Statistics Summary:")
  print(f"{'Metric':<20} {'Tokens':<12} {'Steps':<12}")
  print("-" * 44)
  print(f"{'Total samples:':<20} {len(tokens):<12} {len(steps):<12}")
  print(f"{'Min:':<20} {np.min(tokens):<12} {np.min(steps):<12}")
  print(f"{'Max:':<20} {np.max(tokens):<12} {np.max(steps):<12}")
  print(f"{'Mean:':<20} {np.mean(tokens):<12.2f} {np.mean(steps):<12.2f}")
  print(f"{'Median:':<20} {np.median(tokens):<12} {np.median(steps):<12}")
  print(f"{'Summary Total:':<20} {np.sum(summary_tool_calls):<12} {'--':<12}")
  print(
    f"{'95th percentile:':<20} {np.percentile(tokens, 95):<12.2f} {np.percentile(steps, 95):<12.2f}"
  )

  if print_detail:
    print("\n## Data summary table:")
    print(f"{'Branch':<50} {'Tokens':<8} {'Steps':<6}")
    print("-" * 66)
    for item in training_data:
      print(f"{item['branch']:<50} {item['tokens']:<8} {item['num_steps']:<6}")


def main() -> None:
  """Main function to process training data and save to parquet files."""
  parser = argparse.ArgumentParser(
    description="Prepare SFT data for terminal agent training"
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
    default=["sglang-grep-tree", "save-"],
    help="List of branch prefixes to exclude. If not specified, uses default list.",
  )
  args = parser.parse_args()

  tokenizer = MistralTokenizer.from_hf_hub("mistralai/Devstral-Small-2507")
  training_data = build_training_data(
    tokenizer,
    print_detail=args.print_detail,
    keep_all_branches=args.keep_all_branches,
    use_summarize_only=args.use_summarize_only,
    train_on_summarize_only=args.train_on_summarize_only,
    tasks_dirs=args.tasks_dirs,
    forbidden_prefixes=args.forbidden_prefixes,
  )

  df = pd.DataFrame(training_data)

  script_path = os.path.dirname(os.path.abspath(__file__))
  if args.use_summarize_only:
    # only train on sessions that contain summarize steps
    if args.train_on_summarize_only:
      # only compute loss on summarize steps
      DATA_DIR = "data/only_summarize/"
    else:
      DATA_DIR = "data/summarize/"
  elif args.keep_all_branches:
    # train on all sessions
    DATA_DIR = "data/all_sft/"
  else:
    # train on unique sessions
    DATA_DIR = "data/unique_sft/"
  local_dir = os.path.join(script_path, DATA_DIR)
  local_dir = os.path.expanduser(local_dir)

  if not os.path.exists(local_dir):
    os.makedirs(local_dir)

  df.to_parquet(os.path.join(local_dir, TRAIN_FILE))
  df[:TEST_SAMPLES].to_parquet(os.path.join(local_dir, TEST_FILE))


if __name__ == "__main__":
  main()
