"""Data processor for processing session data to build SFT data.

Processes session directories containing YAML history files, system prompts,
and evaluation outputs to create structured training data for RL.
"""

import gzip
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict

import pandas as pd
import yaml
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
  from data_builder import create_mistral_message, sft_data_from_edits
except ImportError as e:
  raise ImportError(
    f"Failed to import from data_builder package: {e}. "
    "Please ensure scripts/data_builder/ is accessible."
  ) from e

# ============================================================================
# Configuration
# ============================================================================

SESSIONS_ROOT = Path(os.path.expanduser("~/.cache/autopilot/sessions"))
DEFAULT_SESSION_DIR = Path(__file__).parent / "default_session"


class Message(TypedDict):
  content: str
  role: str
  token_ids: Optional[List[int]] = None
  extra_info: Optional[Dict] = None


@dataclass
class SessionData:
  """Processed session data for training."""

  task_id: int
  success: bool
  branch: str
  messages: List[Message]
  edit_steps: List[int]
  tokens: int
  num_steps: int
  termination_reason: Optional[str] = None
  fallback_reason: Optional[str] = None


# ============================================================================
# Utilities
# ============================================================================


def load_yaml(path: Path) -> Optional[Dict]:
  """Safely load YAML file."""
  try:
    with open(path) as f:
      return yaml.safe_load(f)
  except Exception as e:
    print(f"[warning] Error reading {path}: {e}")
    return None


def fix_empty_content(history: List[Dict]) -> Tuple[List[Dict], bool]:
  """Replace empty content fields with placeholder."""
  modified = False
  for item in history:
    if item.get("content") == "":
      item["content"] = "No content"
      modified = True
  return history, modified


def build_training_data(
  yaml_file: Path,
  system_prompt_file: Path,
  rejection_sample: bool = False,
  add_prefix: bool = False,
) -> Optional[List[Dict]]:
  """Extract SFT data from YAML history."""
  history = load_yaml(yaml_file)
  if not history:
    return None

  history, has_empty = fix_empty_content(history)

  if has_empty:
    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".yml", delete=False
    ) as tmp:
      yaml.dump(history, tmp)
      tmp_path = tmp.name
    try:
      return sft_data_from_edits(
        tmp_path,
        str(system_prompt_file),
        rejection_sample=rejection_sample,
        add_prefix=add_prefix,
      )
    finally:
      os.unlink(tmp_path)

  return sft_data_from_edits(
    str(yaml_file),
    str(system_prompt_file),
    rejection_sample=rejection_sample,
    add_prefix=add_prefix,
  )


# ============================================================================
# Session Handler
# ============================================================================


class SessionHandler:
  """Manages session file resolution and validation."""

  def __init__(self, sessions_root: Path = SESSIONS_ROOT):
    self.sessions_root = sessions_root

  def get_files(self, branch: str) -> Tuple[Dict[str, Path], Optional[str]]:
    """Get session file paths with fallback to default directory.

    Returns:
        (file_paths_dict, fallback_reason)
    """
    # Resolve session directory
    session_dir = Path(branch) if "/" in branch else self.sessions_root / branch
    fallback_reason = None

    # Build file paths
    files = {
      "session_dir": session_dir,
      "history": session_dir / "history.yml",
      "system_prompt": session_dir / "system_prompt.txt",
      "eval_result": session_dir / "eval_result.yml",
      "other_info": session_dir / "other_info.yml",
      "vllm_info": session_dir / "vllm_info.json.gz",
    }

    # Determine specific fallback reason
    if session_dir != DEFAULT_SESSION_DIR:
      if not session_dir.exists():
        fallback_reason = f"Session directory not found: {session_dir}"
      elif not all(
        files[k].exists()
        for k in [
          "history",
          "system_prompt",
          "eval_result",
          "other_info",
          "vllm_info",
        ]
      ):
        fallback_reason = "Missing required session files"

      # Apply fallback if needed
      if fallback_reason:
        session_dir = DEFAULT_SESSION_DIR
        print(f"[warning] {fallback_reason}, using default")
        # Rebuild file paths for default dir
        files = {
          "session_dir": session_dir,
          "history": session_dir / "history.yml",
          "system_prompt": session_dir / "system_prompt.txt",
          "eval_result": session_dir / "eval_result.yml",
          "other_info": session_dir / "other_info.yml",
          "vllm_info": session_dir / "vllm_info.json.gz",
        }

    return files, fallback_reason


# ============================================================================
# Data Processor
# ============================================================================


class DataProcessor:
  """Converts session data to training DataFrames."""

  def __init__(self, model_name: str = "mistralai/Devstral-Small-2505"):
    self.tokenizer = MistralTokenizer.from_hf_hub(model_name)
    self.session_handler = SessionHandler()

  def process_data(
    self,
    session_names: List[str],
    all_tasks: List[str],
    benchmark: str,
    add_prefix: bool = False,
  ) -> pd.DataFrame:
    """Process sessions and return DataFrame with training data."""
    all_data = []
    self.benchmark = benchmark

    for branch in tqdm(sorted(session_names), desc="Processing sessions"):
      try:
        session_data = self._process_session(
          branch, all_tasks, add_prefix=add_prefix
        )
        all_data.extend(session_data)
      except Exception as e:
        print(f"[warning] Skipping {branch}: {e}")

    print(f"[info] Processed {len(all_data)} sessions")
    return pd.DataFrame([asdict(d) for d in all_data])

  def _process_session(
    self, branch: str, all_tasks: List[str], add_prefix: bool = False
  ) -> List[SessionData]:
    """Process single session. Always fallback to DEFAULT_SESSION_DIR on any file/data issues."""
    branch_name = branch.split("/")[-1] if "/" in branch else branch

    # Validate branch format - report error, don't fallback
    if (
      self.benchmark not in ["gsm8k", "locomo", "mmlu_pro"]
      and "__" not in branch_name
    ):
      print(f"[error] Invalid branch format (missing '__'): {branch_name}")
      return []

    # Get files (with automatic fallback for missing dir/files)
    files, fallback_reason = self.session_handler.get_files(branch)

    # Check success
    is_success = self._check_success(files["eval_result"])

    # Get termination reason
    termination_reason = None
    if files["other_info"].exists():
      info = load_yaml(files["other_info"])
      termination_reason = info.get("termination_reason") if info else None

    # Build training data with fallback on no valid data
    multiturn_data = build_training_data(
      files["history"],
      files["system_prompt"],
      rejection_sample=True,
      add_prefix=add_prefix,
    )

    if not multiturn_data and files["session_dir"] != DEFAULT_SESSION_DIR:
      fallback_reason = "No valid data in history.yml"
      files, _ = self.session_handler.get_files(str(DEFAULT_SESSION_DIR))
      multiturn_data = build_training_data(
        files["history"],
        files["system_prompt"],
        rejection_sample=True,
        add_prefix=add_prefix,
      )

    # If still no data, force use DEFAULT (should not happen if DEFAULT is properly set up)
    if not multiturn_data:
      print(
        f"[warning] No valid data for {branch_name}, forcing DEFAULT_SESSION_DIR"
      )
      if files["session_dir"] != DEFAULT_SESSION_DIR:
        fallback_reason = "No valid data - forced DEFAULT"
        files, _ = self.session_handler.get_files(str(DEFAULT_SESSION_DIR))
        multiturn_data = build_training_data(
          files["history"],
          files["system_prompt"],
          rejection_sample=True,
          add_prefix=add_prefix,
        )

      # If DEFAULT truly has no data, this is a critical error
      if not multiturn_data:
        print(f"[error] CRITICAL: DEFAULT_SESSION_DIR has no valid data!")
        return []

    # Find task ID - if not found, use task_id=0 from DEFAULT
    task_id = next(
      (i for i, t in enumerate(all_tasks) if branch_name.startswith(t)), None
    )
    if task_id is None:
      print(
        f"[warning] Could not find task_id for {branch_name}, using task_id=0"
      )
      if not fallback_reason:
        fallback_reason = "Task ID not found - using default task_id=0"
      task_id = 0

    # Load vllm_info.json.gz
    vllm_info = {}
    try:
      with gzip.open(files["vllm_info"], "rt") as f:
        vllm_info = json.load(f)
    except Exception as e:
      print(f"[warning] Error loading vllm_info.json.gz: {e}")

    # Process rollouts
    results = []
    for rollout in multiturn_data:
      if rollout and rollout[-1]["role"] == "user":
        rollout = rollout[:-1]

      messages = [
        {"content": m["content"], "role": m["role"]} for m in rollout
      ]  # trim the messages dictionary to only include content and role
      tokens = self._tokenize(messages)

      # append the vllm token ids to the messages
      prompt_prefix_len = 0
      for i, m in enumerate(rollout):
        step = m.get("step", i)
        step_key = str(step)

        # Get vllm info for this step
        step_vllm_info = vllm_info.get(step_key, {})
        token_ids = step_vllm_info.get("token_ids")
        prompt_token_ids = step_vllm_info.get("prompt_token_ids")

        if i < len(messages):
          if token_ids is not None:
            # Background: only assistant-role response has token_ids, user-role is None
            # Update the user-role message's token_ids by prompt_token_ids
            messages[i - 1]["token_ids"] = prompt_token_ids[prompt_prefix_len:]
            # Update the assistant-role message's token_ids by token_ids
            messages[i]["token_ids"] = token_ids
            prompt_prefix_len = len(prompt_token_ids) + len(token_ids)

      results.append(
        SessionData(
          task_id=task_id,
          success=is_success,
          branch=branch_name,
          messages=messages,
          edit_steps=list(range(len(messages))),
          tokens=len(tokens),
          num_steps=len(messages),
          termination_reason=termination_reason,
          fallback_reason=fallback_reason,
        )
      )

    return results

  def _check_success(self, eval_result_file: Path) -> bool:
    """Check if tests passed."""
    with open(eval_result_file, "r") as f:
      eval_result = yaml.safe_load(f)
    return eval_result.get("success", False)

  def _tokenize(self, messages: List[Dict]) -> List:
    """Tokenize messages."""
    mistral_msgs = [
      create_mistral_message(m, last_assistant=(i == len(messages) - 1))
      for i, m in enumerate(messages)
    ]
    return self.tokenizer.encode_chat_completion(
      ChatCompletionRequest(messages=mistral_msgs)
    ).tokens


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
  dp = DataProcessor()
  df = dp.process_data(
    session_names=["5431-20251201-082436-0991"],
    all_tasks=["5431"],
    benchmark="gsm8k",
  )
  print(df.head())
