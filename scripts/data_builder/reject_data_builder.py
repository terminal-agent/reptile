"""SFT data preparation script for terminal agent training.

This module processes YAML history files and system prompts to create
structured training data for fine-tuning language models.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from tqdm import tqdm

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sft_data_builder import _print_statistics, sft_data_from_edits

from autopilot.constants import _CACHE_ROOT
from data_builder.utils import (
  HISTORY_FILE,
  METADATA_FILE,
  SWEBENCH_EVAL_FILE,
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


def _process_session_data(
  session_dir: str,
  session_name: str,
  tokenizer: MistralTokenizer,
  use_summarize_only: bool = False,
  train_on_summarize_only: bool = False,
) -> Optional[List[Dict]]:
  """Process data from a single session directory.

  Args:
      session_dir: Path to the session directory
      session_name: Name of the session (used for identification)
      tokenizer: Tokenizer for encoding messages
      use_summarize_only: If True, only use data that contains summarize steps
      train_on_summarize_only: If True, only train on messages that contain summarize steps

  Returns:
      Training data dictionary or None if invalid
  """
  history_file = os.path.join(session_dir, HISTORY_FILE)
  system_prompt_file = os.path.join(session_dir, SYSTEM_PROMPT_FILE)
  metadata_file = os.path.join(session_dir, METADATA_FILE)
  evaluation_file = os.path.join(session_dir, SWEBENCH_EVAL_FILE)

  ### skip incomplete sessions
  if (
    not os.path.exists(history_file)
    or not os.path.exists(system_prompt_file)
    or not os.path.exists(evaluation_file)
    or not os.path.exists(metadata_file)
  ):
    return None

  ### skip fail and exception sessions
  if (
    "SUCCESS: False" in open(evaluation_file).read()
    or "termination_reason" in open(metadata_file).read()
  ):
    return None

  multiturn_data = sft_data_from_edits(
    yaml_file=history_file,
    system_prompt_file=system_prompt_file,
    use_summarize_only=use_summarize_only,
    rejection_sample=True,
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
        "branch": session_name,
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
  """Build training data from session directories.

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
  sessions_path = str(_CACHE_ROOT / "sessions")
  print(f"Reading sessions from {sessions_path}")

  if not os.path.exists(sessions_path):
    print(f"Warning: Sessions directory {sessions_path} does not exist")
    return []

  # Get all session directories
  session_dirs = [
    os.path.join(sessions_path, d)
    for d in os.listdir(sessions_path)
    if os.path.isdir(os.path.join(sessions_path, d))
    and not is_invalid_branch(
      d,
      tasks_dirs=tasks_dirs,
      forbidden_prefixes=forbidden_prefixes,
    )
  ]

  # Extract session names for deduplication
  session_names = [os.path.basename(d) for d in session_dirs]
  session_names = deduplicate_branches(
    session_names, keep_all=keep_all_branches
  )

  # Filter session_dirs to match deduplicated names
  session_dirs = [
    d for d in session_dirs if os.path.basename(d) in session_names
  ]

  training_data = []
  for session_dir in tqdm(session_dirs):
    session_name = os.path.basename(session_dir)
    data = _process_session_data(
      session_dir,
      session_name,
      tokenizer,
      use_summarize_only=use_summarize_only,
      train_on_summarize_only=train_on_summarize_only,
    )
    if data:
      training_data.extend(data)

  print(f"## Collected {len(training_data)} data")
  _print_statistics(training_data, print_detail)
  return training_data


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
    default=[
      "external/terminal-bench/tasks",
      "external/swebench-verified/tasks",
    ],
    help="List of task directories to filter out. If not specified, uses default TASKS_DIR.",
  )
  parser.add_argument(
    "--forbidden-prefixes",
    type=str,
    nargs="*",
    default=["sglang-grep-tree", "save-", "session-"],
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
      DATA_DIR = "data/only_summarize_reject_sampling/"
    else:
      DATA_DIR = "data/summarize_reject_sampling/"
  elif args.keep_all_branches:
    # train on all sessions
    DATA_DIR = "data/all_reject_sampling/"
  else:
    # train on unique sessions
    DATA_DIR = "data/unique_reject_sampling/"

  local_dir = os.path.join(script_path, DATA_DIR)
  local_dir = os.path.expanduser(local_dir)

  if not os.path.exists(local_dir):
    os.makedirs(local_dir)

  df.to_parquet(os.path.join(local_dir, TRAIN_FILE))
  df[:TEST_SAMPLES].to_parquet(os.path.join(local_dir, TEST_FILE))


if __name__ == "__main__":
  main()
