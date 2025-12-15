import argparse
import concurrent.futures
import importlib
import os
import traceback
from pathlib import Path
from typing import Any, Optional

import psutil
import yaml
from rich.live import Live

from autopilot.config import GLOBAL_CONFIG
from autopilot.evaluation.tasks import TASKS
from autopilot.utils import console

from .batch_progress import RunBatchProgressManager
from .cleanup_utils import (
  cleanup_zombie_processes,
  send_sigint_to_autopilot_processes,
)
from .report_utils import generate_report
from .single_eval import run_single_eval

PROJECT_DIR = Path(__file__).parent.parent.parent


def _update_status_with_termination_reason(
  status: str, output_dir: str, session_name: str
) -> str:
  """Read termination_reason from other_info.yml and update status if available."""
  other_info_file = os.path.join(output_dir, session_name, "other_info.yml")
  if os.path.exists(other_info_file):
    try:
      with open(other_info_file, "rt") as f:
        other_info = yaml.safe_load(f) or {}
        termination_reason = other_info.get("termination_reason")
        if termination_reason:
          return f"{status} ({termination_reason})"
    except Exception:
      pass  # Ignore errors when reading file
  return status


def _handle_task_exception(
  task: Optional[Any],
  task_name: str,
  output_dir: str,
  progress_manager: RunBatchProgressManager,
) -> Any:
  """Handle exception during task evaluation.

  Args:
    task: The task object (may be None if task creation failed)
    task_name: The name of the task
    output_dir: Output directory for error logs
    progress_manager: Progress manager for status updates

  Returns:
    task: minimal task object with session_name
  """
  if task is None:
    # If task creation failed, use task_name as session_name and create minimal task object
    session_name = f"bug-{task_name}"
    task = type("Task", (), {"session_name": session_name})()
  else:
    session_name = task.session_name
    # Cleanup resources for buggy tasks
    try:
      task.cleanup_resources()
    except Exception as cleanup_error:
      # Log cleanup error but don't fail the task
      console.print(
        f"[yellow]Failed to cleanup resources for {session_name}: {cleanup_error}[/yellow]"
      )
  if session_name not in progress_manager._spinner_tasks:
    progress_manager.on_instance_start(session_name)
  progress_manager.update_instance_status(session_name, "Task eval broken")

  output_file = os.path.join(output_dir, session_name, "bug.txt")
  os.makedirs(os.path.dirname(output_file), exist_ok=True)
  with open(output_file, "wt") as f:
    traceback.print_exc(file=f)

  return task


# Type alias for evaluation results (unified format: task_name, model, status, session_name, reload_arg)
EvaluationResult = tuple[str, str, str, str, str]


def batch_evaluate(
  output_dir: str,
  models: list[str],
  parallel: int = 4,
  benchmark: str = "terminal_bench",
  interaction: str = "executive_only",
  log_to_mongodb: bool = False,
  log_to_github: bool = False,
  eval_criteria: str = "rule-based",
  editor: str = "",
  task_list: Optional[list[str]] = None,
  max_steps: Optional[int] = None,
  max_current_steps: Optional[int] = None,
  time_out: Optional[int] = None,
  cache_level: str = "all",
  reload_eval_path: str = "",
  strong_scaffold: bool = False,
  early_stop_ratio: float = 1.0,
) -> list[str]:
  """
  Batch evaluate all tasks in the given benchmark.
  Args:
      output_dir (str): Directory to store results.
      models (list[str]): List of models to evaluate.
      parallel (int): Number of parallel workers.
      benchmark (str): Benchmark type.
      task_list (list[str]): List of tasks to evaluate. Default is None, which means evaluate all tasks in the benchmark.
      max_steps (int): Maximum number of steps for each task. Default is None, which means use the default max steps for each task.
      max_current_steps (int): Maximum number of steps in current branch. Default is None, which means use the default max current steps for each task.
      time_out (int): Maximum time in seconds for each task. Default is None, which means use the default time out for each task.
      reload_eval_path (str): Relative path to the reload evaluation yml file. If provided, enables reload mode.
      early_stop_ratio (float): If provided, stops evaluation after early_stop_ratio * len(task_names) rollouts complete.

  Returns:
      List of session names.
  """
  # Check for incompatible parameters
  if early_stop_ratio < 1.0 and reload_eval_path:
    raise ValueError(
      "early_stop_ratio is incompatible with reload_eval_path. "
      "Please use only one of these parameters."
    )

  if early_stop_ratio > 1.0:
    early_stop_ratio = 1.0
    console.print(
      f"[yellow]Early stopping ratio is greater than 1.0. Setting it to 1.0.[/yellow]"
    )

  benchmark_class = TASKS.get(benchmark)
  is_reload_mode = bool(reload_eval_path)

  if is_reload_mode:
    reload_eval_abspath = PROJECT_DIR / reload_eval_path
    with open(reload_eval_abspath, "r") as f:
      reload_eval_yml = yaml.safe_load(f)
    task_names = list(reload_eval_yml.keys())
    console.print(
      f"[green]Found {len(task_names)} reload tasks to evaluate[/green]"
    )
  else:
    if task_list is None:
      task_names = benchmark_class.task_names()
    else:
      task_names = [
        task_name
        for task_name in task_list
        if task_name in benchmark_class.task_names()
      ]
    console.print(f"[green]Found {len(task_names)} tasks to evaluate[/green]")

  # Calculate early stopping threshold
  early_stop_threshold = None
  if early_stop_ratio is not None and early_stop_ratio < 1.0:
    early_stop_threshold = int(early_stop_ratio * len(task_names))
    console.print(
      f"[yellow]Early stopping enabled: will stop after {early_stop_threshold} rollouts complete[/yellow]"
    )

  # Prepare tasks for execution
  if is_reload_mode:
    tasks_to_execute: list[tuple[str, str, str]] = []
    # Distribute models evenly across tasks
    if len(models) > len(task_names):
      console.print(
        f"[yellow]Warning: More models ({len(models)}) than tasks ({len(task_names)}). Some models will be evaluated on fewer tasks.[/yellow]"
      )
    for i, reload_arg in enumerate(task_names):
      model_index = i % len(models)
      tasks_to_execute.append(
        (models[model_index], reload_arg, reload_eval_path)
      )

    num_instances = len(tasks_to_execute)
    progress_manager = RunBatchProgressManager(num_instances)

    def reload_worker(
      task_info: tuple[str, str, str],
    ) -> EvaluationResult:
      model, reload_arg, reload_eval_path = task_info
      task_name = reload_arg.split("-202")[0]
      task = None
      try:
        task = benchmark_class.from_name(task_name, benchmark)
        session_name = task.session_name
        progress_manager.on_instance_start(session_name)
        progress_manager.update_instance_status(
          session_name, "Building docker container..."
        )
        os.makedirs(os.path.join(output_dir, session_name), exist_ok=True)
        success, output_file = run_single_eval(
          task,
          output_dir,
          reload=reload_arg,
          reload_eval_path=reload_eval_path,
          model=model,
          log_to_mongodb=log_to_mongodb,
          log_to_github=log_to_github,
          eval_criteria=eval_criteria,
          editor=editor,
          cache_level=cache_level,
          progress_manager=progress_manager,
          strong_scaffold=strong_scaffold,
        )
        status = "Succeed" if success else "Fail"
      except Exception:
        # The evaluation should normally finish no matter it succeed or fail.
        # If any exception is caught here, it must be
        # 1. the bug of the code
        # 2. the docker container crashed
        success = False
        task = _handle_task_exception(
          task, task_name, output_dir, progress_manager
        )
        session_name = task.session_name
        status = "Bug"

      # Update status with termination_reason if available
      status = _update_status_with_termination_reason(
        status, output_dir, session_name
      )

      progress_manager.on_instance_end(session_name, status)
      return (task_name, model, status, session_name, reload_arg)

    total_parallel = parallel * len(models)
    reload_results: list[EvaluationResult] = []
    with Live(
      progress_manager.render_group,
      refresh_per_second=2,
      vertical_overflow="visible",
    ):
      with concurrent.futures.ThreadPoolExecutor(
        max_workers=total_parallel
      ) as executor:
        reload_futures = {
          executor.submit(reload_worker, task): task
          for task in tasks_to_execute
        }
        for future in concurrent.futures.as_completed(reload_futures):
          task_result = future.result()
          reload_results.append(task_result)
    generate_report(output_dir, reload_results)
    session_names = [task_result[3] for task_result in reload_results]
  else:
    tasks_to_execute_normal: list[tuple[str, str]] = []
    # Distribute models evenly across tasks
    if len(models) > len(task_names):
      console.print(
        f"[yellow]Warning: More models ({len(models)}) than tasks ({len(task_names)}). Some models will be evaluated on fewer tasks.[/yellow]"
      )
    for i, task_name in enumerate(task_names):
      model_index = i % len(models)
      tasks_to_execute_normal.append((task_name, models[model_index]))

    num_instances = len(tasks_to_execute_normal)
    progress_manager = RunBatchProgressManager(num_instances)

    def worker(
      task_info: tuple[str, str],
    ) -> EvaluationResult:
      task_name, model = task_info
      task = None
      try:
        task = benchmark_class.from_name(task_name, benchmark)
        if max_steps is not None:
          task.max_steps = max_steps
        if max_current_steps is not None:
          task.max_current_steps = max_current_steps
        if time_out is not None:
          task.time_out = time_out
        session_name = task.session_name
        progress_manager.on_instance_start(session_name)
        progress_manager.update_instance_status(
          session_name, "Building docker container..."
        )
        os.makedirs(os.path.join(output_dir, session_name), exist_ok=True)
        success, output_file = run_single_eval(
          task,
          output_dir,
          model=model,
          log_to_mongodb=log_to_mongodb,
          log_to_github=log_to_github,
          editor=editor,
          eval_criteria=eval_criteria,
          interaction=interaction,
          cache_level=cache_level,
          progress_manager=progress_manager,
          strong_scaffold=strong_scaffold,
        )
        status = "Succeed" if success else "Fail"
      except Exception:
        # The evaluation should normally finish no matter it succeed or fail.
        # If any exception is caught here, it must be
        # 1. the bug of the code
        # 2. the docker container crashed
        success = False
        task = _handle_task_exception(
          task, task_name, output_dir, progress_manager
        )
        session_name = task.session_name
        status = "Bug"

      # Update status with termination_reason if available
      status = _update_status_with_termination_reason(
        status, output_dir, session_name
      )

      progress_manager.on_instance_end(session_name, status)
      return (task_name, model, status, session_name, "")

    total_parallel = parallel * len(models)
    # Collect the results and the completed tasks
    # The completed tasks are used for cleanup in case of early stopping,
    # since we need to call task.cleanup_resources() for early stopped tasks.
    normal_results: list[EvaluationResult] = []
    with Live(
      progress_manager.render_group,
      refresh_per_second=2,
      vertical_overflow="visible",
    ):
      with concurrent.futures.ThreadPoolExecutor(
        max_workers=total_parallel
      ) as executor:
        normal_futures = {
          executor.submit(worker, task): task
          for task in tasks_to_execute_normal
        }
        early_stopped = False
        sigint_session_names: list[str] = []
        for future in concurrent.futures.as_completed(normal_futures):
          # Skip cancelled futures (they are handled after shutdown)
          if future.cancelled():
            continue
          task_result = future.result()
          normal_results.append(task_result)
          if early_stopped:
            # All ended tasks (success, failed, or bug) are marked as done.
            # Cancelled futures are also marked as done.
            # If early_stopped and all futures are ended or cancelled, break.
            if all(f.done() for f in normal_futures):
              break
          # Check early stopping condition
          if (
            early_stop_threshold is not None
            and len(normal_results) >= early_stop_threshold
            and not early_stopped
          ):
            # For already-running tasks, send SIGINT to running autopilot processes to trigger graceful shutdown
            sigint_session_names = send_sigint_to_autopilot_processes()
            # For to-be-running tasks, shut down the executor to prevent new tasks from starting
            executor.shutdown(wait=False, cancel_futures=True)

            # Update cancelled tasks status to results
            for future_key, task_info in normal_futures.items():
              if future_key.cancelled():
                task_name, model = task_info
                session_name = f"cancelled-{task_name}"
                cancelled_result: EvaluationResult = (
                  task_name,
                  model,
                  "Cancelled",
                  session_name,
                  "",
                )
                normal_results.append(cancelled_result)
                # Update progress manager for cancelled tasks
                if session_name not in progress_manager._spinner_tasks:
                  progress_manager.on_instance_start(session_name)
                progress_manager.update_instance_status(
                  session_name, "Cancelled"
                )
                progress_manager.on_instance_end(session_name, "Cancelled")

            console.print(
              f"[green]Early stopping triggered: {len(normal_results)} (early_stop_threshold: {early_stop_threshold}) rollouts completed[/green]\n"
              f"[green]Shutting down autopilot evaluations...[/green]"
            )
            # Gracefully kill autopilot child processes that are not yet completed
            cleanup_zombie_processes(timeout=10)
            early_stopped = True

    # Label the tasks that are interrupted by SIGINT
    for i, result in enumerate(normal_results):
      if result[3] in sigint_session_names:
        normal_results[i] = (
          result[0],
          result[1],
          "Interrupted",
          result[3],
          result[4],
        )

    generate_report(output_dir, normal_results)
    session_names = [task_result[3] for task_result in normal_results]

  return session_names
