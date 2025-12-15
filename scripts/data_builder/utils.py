"""Shared utility functions for data preparation scripts.

This module contains common functionality used by both SFT and DPO data
preparation scripts, including message creation, branch filtering, and
deduplication logic.
"""

import os
import re
from typing import Dict, List, Optional, Tuple, Union

from mistral_common.protocol.instruct.messages import (
  AssistantMessage,
  SystemMessage,
  UserMessage,
)

# Constants
TIMESTAMP_PATTERN = r"\d{8}-(\d{6})"
TASKS_DIR = "external/terminal-bench/tasks"
HISTORY_FILE = "history.yml"
SYSTEM_PROMPT_FILE = "system_prompt.txt"
METADATA_FILE = "other_info.yml"
SWEBENCH_EVAL_FILE = "eval_output_classified_pytest.txt"

TRAIN_FILE = "train.parquet"
TEST_FILE = "test.parquet"
TEST_SAMPLES = 20


def create_mistral_message(
  message_data: Dict[str, str], last_assistant: bool = False
) -> Union[SystemMessage, UserMessage, AssistantMessage]:
  """Create a Mistral message object from dictionary data.

  Args:
      message_data: Dictionary containing 'role' and 'content' keys
      last_assistant: Whether this is the last assistant message (adds prefix)

  Returns:
      Appropriate Mistral message object based on role

  Raises:
      ValueError: If role is not recognized
  """
  if message_data["role"] == "system":
    return SystemMessage(content=message_data["content"])
  elif message_data["role"] == "user":
    return UserMessage(content=message_data["content"])
  elif message_data["role"] == "assistant":
    if last_assistant:
      return AssistantMessage(content=message_data["content"], prefix=True)
    else:
      return AssistantMessage(content=message_data["content"])
  else:
    raise ValueError(f"Unknown role: {message_data['role']}")


def is_invalid_branch(
  branch: str,
  tasks_dirs: Optional[List[str]] = None,
  forbidden_prefixes: Optional[List[str]] = None,
) -> bool:
  """Check if a branch name is invalid for processing.

  Args:
      branch: The branch name to check
      tasks_dirs: List of directories containing task names to filter out.
                  Default: [TASKS_DIR].
      forbidden_prefixes: List of branch name prefixes to exclude.
                          Default: [].

  Returns:
      True if branch should be skipped, False otherwise
  """
  if tasks_dirs is None:
    tasks_dirs = [TASKS_DIR]
  if forbidden_prefixes is None:
    forbidden_prefixes = []

  # Get task names from all specified directories
  task_names = set()
  for tasks_dir in tasks_dirs:
    try:
      if os.path.exists(tasks_dir):
        for item in os.listdir(tasks_dir):
          if os.path.isdir(os.path.join(tasks_dir, item)):
            task_names.add(item)
    except Exception as e:
      print(f"Warning: Could not load task names from {tasks_dir}: {e}")

  # Check if branch name starts with any task name
  for task_name in task_names:
    if branch.startswith(task_name):
      return True

  # Check if branch name starts with any forbidden prefix
  for prefix in forbidden_prefixes:
    if branch.startswith(prefix):
      return True

  return False


def deduplicate_branches(
  branches: List[str], keep_all: bool = False
) -> List[str]:
  """Remove duplicate branches based on timestamp patterns.

  Args:
      branches: List of branch names to deduplicate
      keep_all: If True, keep all branches in each group. If False, keep only the latest one.

  Returns:
      List of deduplicated branch names
  """
  # Group branches by their prefix (everything before the timestamp)
  branch_groups: Dict[str, List[Tuple[str, Optional[str]]]] = {}

  for branch in branches:
    # Find the timestamp pattern in the branch name
    match = re.search(TIMESTAMP_PATTERN, branch)
    if match:
      timestamp = match.group(1)
      # Get the prefix (everything before the timestamp)
      prefix = branch[: match.start()]

      if prefix not in branch_groups:
        branch_groups[prefix] = []
      branch_groups[prefix].append((branch, timestamp))
    else:
      # If no timestamp found, treat the whole branch name as unique
      branch_groups[branch] = [(branch, None)]

  # For each group, keep branches based on keep_all flag
  deduplicated_branches = []
  for prefix, branch_list in branch_groups.items():
    if prefix.startswith("session-"):
      deduplicated_branches.extend([b[0] for b in branch_list])
    elif len(branch_list) == 1:
      deduplicated_branches.append(branch_list[0][0])
    else:
      if keep_all:
        # Keep all branches in the group
        deduplicated_branches.extend([b[0] for b in branch_list])
      else:
        # Sort by timestamp and take the latest one
        latest_branch = max(
          branch_list, key=lambda x: x[1] if x[1] else "00000000-000000"
        )
        deduplicated_branches.append(latest_branch[0])
  return deduplicated_branches
