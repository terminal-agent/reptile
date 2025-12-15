#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent environment for running rollouts and shipping data.

This module provides functionality for
- managing model configurations
- running batch evaluations (rollouts)
- transferring results via SCP to remote servers

It is designed to work in containerized environments (pods) for RL data collection.

Example:
    Run rollouts and ship results::

        python agent_env.py --target-port 23333 --rollout-size 3 --task-id "1,32,120"
"""

import os
import shlex
import tempfile
import time
import traceback
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

import paramiko
import yaml
from constants import (
  DEFAULT_CONFIG,
  DEFAULT_MODEL_NAME,
  ENV,
)
from data_processor import DataProcessor

from autopilot.cli.evaluate import valid_criteria
from autopilot.evaluation.batch_eval import batch_evaluate
from autopilot.evaluation.tasks import TASKS

# ============================================================================
# Configuration Management
# ============================================================================


def add_url_to_config(
  vllm_url: str,
  name: str = DEFAULT_MODEL_NAME,
  config_path: str = DEFAULT_CONFIG,
) -> str:
  """Adds or updates a model URL in the configuration file.

  This function reads an existing YAML configuration file (if present), adds
  or updates a model entry with the specified URL, and saves it back to disk.
  The base URL is automatically constructed to point to the /v1 endpoint.

  Args:
      vllm_url: The vLLM service URL (e.g., "http://localhost:8000/v1/").
          The function will extract the scheme and netloc to build the base URL.
      name: Model name identifier. Defaults to DEFAULT_MODEL_NAME.
      config_path: Path to the YAML configuration file. Defaults to
          DEFAULT_CONFIG. The directory will be created if it doesn't exist.

  Returns:
      The model name that was added or updated (same as the `name` parameter).

  Raises:
      OSError: If there's an issue creating the config directory or writing
          the file.
      yaml.YAMLError: If the existing config file is malformed.
  """
  data: dict = {}
  if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
      loaded = yaml.safe_load(f)
      if isinstance(loaded, dict):
        data = loaded

  if not isinstance(data.get("models"), list):
    data["models"] = []

  parts = urlsplit(vllm_url)
  base_url = urlunsplit((parts.scheme, parts.netloc, "/v1", "", ""))
  entry = {
    "name": name,
    "credentials": {"api_key": "token-abc123", "base_url": base_url},
    "parameters": {"model": ""},
    "priority": 20,
  }

  # Replace existing entry or append new one
  replaced = False
  for i, model in enumerate(data["models"]):
    if isinstance(model, dict) and model.get("name") == name:
      data["models"][i] = entry
      replaced = True
      break

  if not replaced:
    data["models"].append(entry)

  os.makedirs(os.path.dirname(config_path), exist_ok=True)
  with open(config_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(
      data,
      f,
      sort_keys=False,
      allow_unicode=True,
      indent=2,
      default_flow_style=False,
    )

  return name


# ============================================================================
# Data Processing and Transfer
# ============================================================================


def process_and_scp(
  session_dirs: list[str],
  remote_path: str,
  remote_file_name: str,
  all_tasks: list[str],
  benchmark: str,
) -> None:
  """Processes session data and transfers it to a remote server via SCP.

  This function aggregates session data using DataProcessor, saves it as a
  Parquet file, and transfers it to a remote server via SSH/SCP. The remote
  host and user are determined from environment variables or defaults.

  Args:
      session_dirs: List of session directory paths to process.
      remote_path: Remote directory path on the server where the file will be
          stored. Will be created if it doesn't exist.
      remote_file_name: Name for the output file. If it doesn't end with
          ".parquet", the extension will be added automatically.
      all_tasks: List of all task identifiers for data processing context.
      benchmark: Benchmark name to use for evaluation.
  Raises:
      paramiko.AuthenticationException: If SSH authentication fails.
      paramiko.SSHException: If there's an SSH connection error.
      OSError: If there's an issue creating the temporary file or directory.
  """
  df = DataProcessor().process_data(
    session_names=session_dirs, all_tasks=all_tasks, benchmark=benchmark
  )
  print(
    f"[info] processing {len(df)} sessions, the first 5 sessions are: {df.head(5)}"
  )

  # Create temporary local file
  tmpdir = tempfile.mkdtemp(prefix="autopilot_")
  if not remote_file_name.endswith(".parquet"):
    remote_file_name = remote_file_name + ".parquet"
  local_file = os.path.join(tmpdir, remote_file_name)
  df.to_parquet(local_file)

  # Transfer to remote server
  host = os.environ.get("VERL_HOST", ENV["VERL_HOST"])
  user = os.environ.get("VERL_USER", ENV["VERL_USER"])

  max_retries = 8
  for attempt in range(max_retries):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      ssh.connect(host, username=user)
      ssh.exec_command(f"mkdir -p {shlex.quote(remote_path)}")

      remote_file = os.path.join(remote_path, remote_file_name)
      with ssh.open_sftp() as sftp:
        sftp.put(local_file, remote_file)
        marker_local = local_file + ".done"
        marker_remote = remote_file + ".done"
        with open(marker_local, "w") as f:
          pass
        sftp.put(marker_local, marker_remote)
        os.unlink(marker_local)
      break
    except Exception:
      traceback.print_exc()
      if attempt < max_retries - 1:
        wait_time = 2**attempt
        print(f"[warning] SSH failed, retrying in {wait_time}s...")
        time.sleep(wait_time)
      else:
        raise
    finally:
      ssh.close()


# ============================================================================
# Main Rollout and Ship Workflow
# ============================================================================


def run_rollouts_and_ship_from_pod(
  target_port: int,
  remote_path: str,
  remote_file_name: str,
  rollout_k: int,
  eval_criteria: str,
  task_file: Optional[str] = None,
  task_list: Optional[list[int]] = None,
  experiment_name: Optional[str] = None,
  step: Optional[int] = None,
  benchmark: str = "swegym",
  strong_scaffold: bool = False,
  skip_rollout: bool = False,
  early_stop_ratio: Optional[float] = None,
  naive_mode: bool = False,
) -> bool:
  """Runs rollouts and ships results from pod to a remote server.

  This is the main workflow function that orchestrates the entire process:
  1. Configures the model URL in the config file
  2. Loads tasks from a file
  3. Runs batch evaluation (rollouts) for specified tasks
  4. Processes and transfers results to remote server

  The function creates a timestamped output directory for each run and uses
  batch_evaluate to execute multiple rollouts in parallel.

  Args:
      target_port: Port number for the vLLM service running locally.
      remote_path: Remote directory path on the server where results will be
          stored.
      remote_file_name: Name for the output Parquet file.
      rollout_k: Number of rollouts to run per task. Each task will be
          executed this many times.
      task_file: Path to file containing all task identifiers, one per line. If not provided, use the task names from the benchmark.
      task_list: List of task indices to run. If None, all tasks from the file
          will be executed. Indices refer to line numbers in task_file.
      benchmark: Benchmark name to use for evaluation.
      strong_scaffold: Enable strong scaffold mode to control terminal node behavior. Defaults to False.
      skip_rollout: Skip rollout and directly return the sessions from the ~/.cache/autopilot/sessions directory. Defaults to False.
      early_stop_ratio: Optional ratio for early stopping during rollouts.

  Returns:
      True if successful.

  Raises:
      RuntimeError: If no sessions are aggregated after evaluation, indicating
          the batch evaluation failed or produced no results.
      FileNotFoundError: If task_file doesn't exist.
      OSError: If there's an issue creating output directories or processing data.
      paramiko.SSHException: If remote transfer fails.
  """
  # Configure model URL
  url = f"http://localhost:{target_port}/v1/"
  model_name = add_url_to_config(url)

  # Load tasks
  # If specific task file is provided, use it, otherwise use the task names from the benchmark
  if task_file and os.path.exists(task_file):
    with open(task_file, "r", encoding="utf-8") as f:
      all_tasks = [t.strip() for t in f if t.strip()]
  else:
    try:
      task_class = TASKS.get(benchmark)
      if hasattr(task_class, "task_names"):
        all_tasks = task_class.task_names()
      else:
        all_tasks = []
    except ValueError:
      all_tasks = []

  # Build task list based on indices
  if task_list is None:
    task_list = list(range(len(all_tasks)))
  tasks = [all_tasks[i] for i in task_list] * rollout_k

  if skip_rollout:
    rl_runs_folder = os.path.join(
      os.path.expanduser("~/.cache/autopilot/rl_runs"),
      experiment_name,
    )
    ## find the folder with prefix f"step_{step}-" in out root directory
    rl_runs_step_folder = [
      os.path.join(rl_runs_folder, f)
      for f in os.listdir(rl_runs_folder)
      if f.startswith(f"step_{step}-")
    ][0]  # take the first one
    all_sessions = [
      rl_runs_session
      for rl_runs_session in os.listdir(rl_runs_step_folder)
      if "202" in rl_runs_session
    ]
  else:
    # Run batch evaluation
    timestamp = (
      f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
    )
    if experiment_name and step is not None:
      dir_name = f"step_{step}-{timestamp}"
      out_root = os.path.join(
        os.path.expanduser("~/.cache/autopilot/rl_runs"),
        experiment_name,
        dir_name,
      )
    else:
      dir_name = timestamp
      out_root = os.path.join(
        os.path.expanduser("~/.cache/autopilot/rl_runs"), dir_name
      )
    os.makedirs(out_root, exist_ok=True)

    all_sessions = batch_evaluate(
      output_dir=out_root,
      models=[model_name],
      benchmark=benchmark,
      interaction="executive_only" if not naive_mode else "naive",
      eval_criteria=eval_criteria if not naive_mode else "naive",
      task_list=tasks,
      parallel=100,
      max_steps=500,
      max_current_steps=250,
      time_out=600,
      cache_level="all" if not naive_mode else "naive",
      strong_scaffold=strong_scaffold,
      early_stop_ratio=early_stop_ratio,
    )

  print(
    f"[info, docker machine] input tasks num: {len(tasks)}, "
    f"output sessions num: {len(all_sessions)}"
  )

  if not all_sessions:
    raise RuntimeError("no sessions aggregated")

  if len(all_sessions) != len(tasks):
    print(
      f"[warning, docker machine] input tasks num: {len(tasks)}, "
      f"output sessions num: {len(all_sessions)}"
    )

  # Process and transfer results
  process_and_scp(
    all_sessions, remote_path, remote_file_name, all_tasks, benchmark=benchmark
  )
  return True


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(
    description=(
      "Run rollouts and ship results to remote server. "
      "This script executes batch evaluations for specified tasks "
      "and transfers the results via SCP."
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    "--target-port",
    type=int,
    default=23333,
    help="Port number for the vLLM service (default: 23333).",
  )
  parser.add_argument(
    "--remote-file-path",
    default=os.path.expanduser("~/tmp/verldata"),
    help="Remote directory path on server where files will be stored.",
  )
  parser.add_argument(
    "--remote-file-name",
    default="test_train.parquet",
    help="Name for the output Parquet file.",
  )
  parser.add_argument(
    "--rollout-size",
    type=int,
    default=3,
    help="Number of rollouts to run per task (default: 3).",
  )
  parser.add_argument(
    "--task-file",
    default=None,
    help="Path to file containing task identifiers (one per line). If not provided, use the task names from the benchmark.",
  )
  parser.add_argument(
    "--task-id",
    default="1,32,120",
    help=(
      "Comma-separated list of task indices to run "
      "(default: '1,32,120'). Use indices from task-file."
    ),
  )
  parser.add_argument(
    "--experiment-name",
    type=str,
    default=None,
    help="Experiment name to use as prefix for output directory.",
  )
  parser.add_argument(
    "--step",
    type=int,
    default=None,
    help="Step number to use as prefix for output directory.",
  )
  parser.add_argument(
    "--benchmark",
    type=str,
    default="swegym",
    help="Benchmark name to use for evaluation (default: swegym).",
  )
  parser.add_argument(
    "--eval-criteria",
    type=str,
    default=None,
    help="The evaluation criteria (rule-based, llm-judge, string-match, swebench, classified-pytest). If not provided, will be determined based on the benchmark.",
  )
  parser.add_argument(
    "--strong-scaffold",
    action="store_true",
    default=False,
    help="Enable strong scaffold mode to control terminal node behavior.",
  )
  parser.add_argument(
    "--skip-rollout",
    action="store_true",
    default=False,
    help="Skip rollout and directly return the sessions from the ~/.cache/autopilot/rl_runs directory.",
  )
  parser.add_argument(
    "--early-stop-ratio",
    type=float,
    default=1.0,
    help="Optional ratio for early stopping during rollouts.",
  )
  parser.add_argument(
    "--naive-mode",
    action="store_true",
    default=False,
    help="Run autopilot in naive mode. (not use docker, run autopilot in host machine directly; use naive workflow and naive evaluation)",
  )

  args = parser.parse_args()

  # Auto-complete relative task file path
  if args.task_file and not os.path.isabs(args.task_file):
    args.task_file = os.path.join(os.path.dirname(__file__), args.task_file)

  # Parse task IDs from comma-separated string to list of integers
  try:
    task_list = [int(i.strip()) for i in args.task_id.split(",") if i.strip()]
  except ValueError as e:
    raise ValueError(
      f"Invalid task-id format: {args.task_id}. "
      f"Expected comma-separated integers. Error: {e}"
    )

  # Determine the evaluation criteria
  eval_criteria = args.eval_criteria
  if eval_criteria is None:
    if args.benchmark in [
      "swebench_verified",
      "swebench_verified_focus",
      "swegym",
      "swegym_focus",
    ]:
      eval_criteria = "classified-pytest"
    elif args.benchmark in [
      "terminal_bench",
      "terminal_bench_focus",
      "terminal_bench_sample",
      "swe_bench",
    ]:
      eval_criteria = "rule-based"
    elif args.benchmark in ["mmlu_pro", "gsm8k"]:
      eval_criteria = "string-match"
    elif args.benchmark in ["locomo"]:
      eval_criteria = "llm-judge"
    else:
      raise ValueError(f"Unknown benchmark: {args.benchmark}")
  elif eval_criteria not in valid_criteria:
    raise ValueError(
      f"Invalid eval_criteria: {eval_criteria}. Must be one of: {', '.join(valid_criteria)}"
    )

  print(
    f"[info] running rollouts and shipping from pod to "
    f"{args.remote_file_path}/{args.remote_file_name}"
  )
  print(f"[info] task indices: {task_list}, rollout size: {args.rollout_size}")

  try:
    success = run_rollouts_and_ship_from_pod(
      target_port=args.target_port,
      remote_path=args.remote_file_path,
      remote_file_name=args.remote_file_name,
      rollout_k=args.rollout_size,
      task_file=args.task_file,
      task_list=task_list,
      experiment_name=args.experiment_name,
      step=args.step,
      benchmark=args.benchmark,
      eval_criteria=eval_criteria,
      strong_scaffold=args.strong_scaffold,
      skip_rollout=args.skip_rollout,
      early_stop_ratio=args.early_stop_ratio,
      naive_mode=args.naive_mode,
    )
    print("Success" if success else "Failed")
  except Exception as e:
    print(f"[error] {e}")
    raise
