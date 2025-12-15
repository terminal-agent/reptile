import argparse
import importlib
import os
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import yaml

from autopilot.cli.data import Session, sessions_path
from autopilot.data import InteractionMode
from autopilot.evaluation.tasks import Task
from autopilot.utils import console, execute_cmd

from .batch_progress import RunBatchProgressManager
from .classified_pytest import run_classified_pytest_eval
from .naive_eval import extract_solution
from .reload_eval import reload_eval_fn
from .report_utils import generate_token_report
from .swebench_eval import run_swebench_eval


def run_single_eval(
  task: Task,
  output_dir: str,
  reload: str = "",
  reload_eval_path: str = "",
  interaction: str = "executive_only",
  terminal: bool = False,
  model: Optional[str] = None,
  log_to_mongodb: bool = False,
  log_to_github: bool = False,
  eval_criteria: str = "rule-based",
  editor: str = "",
  eval_only: bool = False,
  cache_level: str = "all",
  progress_manager: Optional[RunBatchProgressManager] = None,
  strong_scaffold: bool = False,
) -> tuple:
  """
  Run evaluation for a single task.
  Args:
      task (Task): Task configuration.
      eval_only (bool): If True, skip workflow execution and only run evaluation.
                        Assumes the container is already running with completed work.
  Returns:
      (success, session_name): Tuple of success status and session name.
  """

  # Verify container is running when in eval_only mode
  if eval_only:
    result = subprocess.run(
      ["docker", "inspect", "-f", "{{.State.Running}}", task.container_name],
      capture_output=True,
      text=True,
    )
    assert result.returncode == 0 and result.stdout.strip() == "true", (
      f"Container {task.container_name} is not running. "
      f"eval_only mode requires the container to be already set up and running."
    )

  if eval_criteria == "naive" or interaction == "naive":
    if task.benchmark not in ["gsm8k", "mmlu_pro"]:
      raise ValueError(
        f"Naive evaluation is only supported for the gsm8k and mmlu_pro benchmark. Got {task.benchmark}."
      )

  # Set cache_level for the task
  task.cache_level = cache_level
  # Pass interaction mode to the task
  task.interaction_mode = InteractionMode(interaction)

  # Set progress manager for the task if provided
  if progress_manager:
    task.progress_manager = progress_manager

  # first run the sandbox
  if not eval_only and task.cache_level != "naive":
    task.launch_container()

  # run the autopilot process
  session_name = task.session_name

  # Prepare environment variables for evaluation
  envs = os.environ.copy()
  envs.update(task.envs)

  # Ensure output directory exists
  os.makedirs(os.path.join(output_dir, session_name), exist_ok=True)

  if not eval_only:
    if progress_manager:
      progress_manager.update_instance_status(
        task.session_name, "Building autopilot..."
      )
    if reload_eval_path:
      try:
        reload_step = int(reload.split(":")[-1])
        task.max_steps = (
          reload_step + 3
        )  # allow 3 more steps: [llm, terminal, llm]
        interaction = "executive_only"
      except ValueError as e:
        console.print(
          f"Reloading {reload} failed, correct format is <branch>:<traj>:<step>, "
          "where both <traj> and <step> are integers."
        )
        raise e

    cmd = [
      "autopilot",
      "run",
      "--no-terminal" if not terminal else "--terminal",
      "--task",
      task.description,
      "--name",
      session_name,
      "--interaction",
      interaction,
      "--max-steps",
      str(task.max_steps),
      "--max-current-steps",
      str(task.max_current_steps),
      "--max-time",
      str(task.time_out),
      "--reload",
      reload,
      "--log-to-github" if log_to_github else "--no-log-to-github",
      "--log-to-mongodb" if log_to_mongodb else "--no-log-to-mongodb",
    ]
    if task.cache_level != "naive":
      cmd.extend(["--sandbox", task.container_name])
    if editor:
      cmd.extend(["--editor", editor])
    if model:
      cmd.extend(["--model", model])
    if strong_scaffold:
      cmd.append("--strong-scaffold")

    output_file = os.path.join(output_dir, session_name, "output.txt")
    history_file = os.path.join(sessions_path, session_name, "history.yml")

    # Monitor history.yml in background thread to track step progress
    monitoring_active = threading.Event()
    monitoring_active.set()

    def monitor_steps():
      last_step = -1
      while monitoring_active.is_set():
        if os.path.exists(history_file):
          try:
            with open(history_file, "rt") as f:
              history = yaml.safe_load(f)
              if history:
                # Get the current step number from the history
                # history is a list, each item has 'step' and 'traj' fields
                # We use the step from the last item in the current trajectory
                current_step = len(history) - 1
                if current_step > last_step:
                  last_step = current_step
                  if progress_manager:
                    progress_manager.update_instance_status(
                      task.session_name,
                      f"Running autopilot... (step {current_step + 1}/{task.max_steps})",
                    )
          except Exception:
            pass  # Ignore errors when reading file (file might be locked or incomplete)
        time.sleep(1)  # Check every second

    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_steps, daemon=True)
    monitor_thread.start()

    try:
      with open(output_file, "wt") as f:
        subprocess.run(
          cmd,
          stdout=f,
          stderr=f,
          env=envs,
          text=True,
          check=True,
        )
    finally:
      # Stop monitoring after process completes
      monitoring_active.clear()
      time.sleep(0.5)  # wait for final update of progress manager

    files_to_copy_to_host = task.files_to_copy_to_host(
      host_dir=os.path.join(output_dir, session_name)
    )
    task.copy_to_host(files_to_copy_to_host)

  if progress_manager:
    progress_manager.update_instance_status(task.session_name, "Evaluating...")

  if reload_eval_path:
    history_file = os.path.join(sessions_path, session_name, "history.yml")
    session = Session(history_file)
    # Extract the completion steps after the reload step
    completion_steps = session.trajs[-1][reload_step + 1 :]
    eval_output_file = os.path.join(output_dir, session_name, "eval_output.txt")
    success, eval_output_file = reload_eval_fn(
      completion_steps, reload, reload_eval_path, Path(eval_output_file)
    )
    if progress_manager:
      progress_manager.update_instance_status(
        task.session_name, "Cleaning up Docker..."
      )
    task.cleanup_resources()
    return success, eval_output_file

  is_eval_timeout = False
  if eval_criteria == "swebench":
    # run the SWE-bench official evaluation
    success, eval_output_file = run_swebench_eval(
      task, output_dir, session_name
    )
  elif eval_criteria == "naive":
    # parse the last llm step output
    if not hasattr(task, "answer"):
      raise ValueError(
        "For eval_criteria 'naive', the task must have 'answer' property."
      )
    history_file = os.path.join(sessions_path, session_name, "history.yml")
    session = Session(history_file)
    prediction = session.trajs[-1][-1]["content"].strip()
    if "gsm8k" in task.benchmark.lower():
      extract_type = "gsm8k"
    elif "mmlu" in task.benchmark.lower():
      extract_type = "mmlu"
    else:
      raise NotImplementedError(
        f"For eval_criteria 'naive', the answer parser for benchmark {task.benchmark} is not implemented."
      )
    prediction = extract_solution(
      prediction, extract_type=extract_type, method="strict"
    )

    eval_output_file = os.path.join(output_dir, session_name, "eval_output.txt")
    with open(eval_output_file, "wt", encoding="utf-8", errors="replace") as f:
      f.write(f"Answer: {task.answer}\nPrediction: {prediction}\n")
    success = prediction == task.answer
  else:
    # run the `run-tests.sh` script then parse the output based on `eval_criteria`
    env_args = [
      arg for k, v in task.envs.items() for arg in ("--env", f"{k}={v}")
    ]
    eval_output_file = os.path.join(output_dir, session_name, "eval_output.txt")
    with open(eval_output_file, "wt", encoding="utf-8", errors="replace") as f:
      try:
        subprocess.run(
          [
            "docker",
            "exec",
            *env_args,
            task.container_name,
            "bash",
            "-c",
            task.eval_script,
          ],
          stdout=f,
          stderr=f,
          env=envs,
          text=True,
          timeout=task.eval_time_out,
        )
      except subprocess.TimeoutExpired:
        f.write(f"\nEvaluation timed out after {task.eval_time_out} seconds\n")
        is_eval_timeout = True
        console.print(
          f"[yellow]Evaluation timed out after {task.eval_time_out} seconds in {task.container_name}[/yellow]"
        )
    with open(eval_output_file, "rt", encoding="utf-8", errors="replace") as f:
      eval_output = f.read()
    if eval_criteria == "rule-based":
      success = "Tests passed!" in eval_output.strip()
    elif eval_criteria == "llm-judge":
      if not hasattr(task, "answer") or not hasattr(task, "question"):
        raise ValueError(
          "For eval_criteria 'llm-judge', the task must have 'answer' and 'question' property."
        )
      project_dir = Path(__file__).parent.parent.parent
      llm_judge_result = execute_cmd(
        [
          "python",
          os.path.join(project_dir, "tools", "llm_judge.py"),
          shlex.quote(str(task.question)),
          shlex.quote(str(task.answer)),
          shlex.quote(str(eval_output.strip())),
        ]
      )
      success = llm_judge_result == "True"

    elif eval_criteria == "string-match":
      if not hasattr(task, "answer"):
        raise ValueError(
          "For eval_criteria 'string-match', the task must have 'answer' property."
        )
      else:
        success = task.answer == eval_output.strip()
    elif eval_criteria == "classified-pytest":
      success, classified_pytest_eval_output_file = run_classified_pytest_eval(
        task, output_dir, session_name, env_args, envs, task.eval_time_out
      )
    else:
      # Handle unknown eval_criteria
      console.print(
        f"[yellow]Unknown eval_criteria: {eval_criteria}, defaulting to False[/yellow]"
      )
      success = False
  success = success and not is_eval_timeout

  eval_result_yml_file = os.path.join(
    output_dir, session_name, "eval_result.yml"
  )
  with open(eval_result_yml_file, "wt") as f:
    yaml.dump(
      {
        "success": success,
        "eval_timeout": is_eval_timeout,
        "eval_criteria": eval_criteria,
      },
      f,
    )

  # Only cleanup resources if we launched them (not in eval_only mode)
  if not eval_only:
    if task.cache_level != "naive":
      if progress_manager:
        progress_manager.update_instance_status(
          task.session_name, "Cleaning up Docker..."
        )
      task.cleanup_resources()
    workspace = os.path.join(sessions_path, session_name)
    generate_token_report(workspace)
    os.system(
      f"cp {workspace}/other_info.yml {output_dir}/{session_name}/other_info.yml && "
      f"cp {workspace}/history.yml {output_dir}/{session_name}/history.yml &&"
      f"cp {workspace}/system_prompt.txt {output_dir}/{session_name}/system_prompt.txt"
    )  # record model info

    # upload the eval output to the git repo
    shutil.copy(eval_output_file, workspace)
    shutil.copy(eval_result_yml_file, workspace)
    if eval_criteria == "classified-pytest":
      shutil.copy(classified_pytest_eval_output_file, workspace)

    # upload the eval output to the git repo
    if log_to_github:
      git_cmd = f'git -C "{workspace}" add eval_output.txt'
      git_cmd += f' && git -C "{workspace}" add eval_result.yml'
      if eval_criteria == "classified-pytest":
        git_cmd += (
          f' && git -C "{workspace}" add eval_output_classified_pytest.txt'
        )
      git_cmd += f' && git -C "{workspace}" commit -m "add evaluation output"'
      git_cmd += f' && git -C "{workspace}" push origin {session_name}'
      subprocess.run(
        git_cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
      )

  return success, eval_output_file
