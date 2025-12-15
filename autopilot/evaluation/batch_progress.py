"""This module contains an auxiliary class for rendering progress of a batch run."""

import collections
import time
from datetime import timedelta
from pathlib import Path
from threading import Lock

import yaml
from rich.console import Group
from rich.progress import (
  BarColumn,
  MofNCompleteColumn,
  Progress,
  SpinnerColumn,
  TaskID,
  TaskProgressColumn,
  TextColumn,
  TimeElapsedColumn,
)
from rich.table import Table


def _shorten_str(s: str, max_len: int, shorten_left=False) -> str:
  if len(s) > max_len:
    s = (
      ("..." + s[-max_len + 3 :])
      if shorten_left
      else (s[: max_len - 3] + "...")
    )
  return f"{s:<{max_len}}"


class RunBatchProgressManager:
  def __init__(
    self,
    num_instances: int,
    yaml_report_path: Path | None = None,
  ):
    """This class manages a progress bar/UI for run-batch

    Args:
        num_instances: Number of task instances
        yaml_report_path: Path to save a yaml report of the instances and their exit statuses
    """

    self._spinner_tasks: dict[str, TaskID] = {}
    """We need to map instance ID to the task ID that is used by the rich progress bar."""

    self._lock = Lock()
    self._start_time = time.time()
    self._total_instances = num_instances
    self._last_table_update = 0.0
    self._table_update_interval = (
      1.0  # Throttle table updates to avoid tmux rendering issues
    )
    self._last_eta_update = 0.0
    self._eta_update_interval = (
      0.5  # Throttle ETA updates to reduce rendering load
    )
    self._last_status_update: dict[
      str, float
    ] = {}  # Per-instance status update throttling
    self._status_update_interval = (
      0.5  # Throttle status updates to reduce rendering load
    )

    self._instances_by_exit_status: collections.defaultdict[
      str | None, list[str]
    ] = collections.defaultdict(list)
    self._main_progress_bar = Progress(
      SpinnerColumn(spinner_name="dots2"),
      TextColumn("[progress.description]{task.description}"),
      BarColumn(),
      MofNCompleteColumn(),
      TaskProgressColumn(),
      TimeElapsedColumn(),
      TextColumn("[cyan]{task.fields[eta]}[/cyan]"),
      # Wait 5 min before estimating speed
      speed_estimate_period=60 * 5,
    )
    self._task_progress_bar = Progress(
      SpinnerColumn(spinner_name="dots2"),
      TextColumn("{task.fields[instance_id]}"),
      TextColumn("{task.fields[status]}"),
      TimeElapsedColumn(),
    )
    """Task progress bar for individual instances. There's only one progress bar
        with one task for each instance.
        """

    self._main_task_id = self._main_progress_bar.add_task(
      "[cyan]Overall Progress", total=num_instances, eta=""
    )

    self.render_group = Group(
      Table(), self._task_progress_bar, self._main_progress_bar
    )
    self._yaml_report_path = yaml_report_path

  @property
  def n_completed(self) -> int:
    return sum(
      len(instances) for instances in self._instances_by_exit_status.values()
    )

  def _get_eta_text(self) -> str:
    """Calculate estimated time remaining based on current progress."""
    try:
      estimated_remaining = (
        (time.time() - self._start_time)
        / self.n_completed
        * (self._total_instances - self.n_completed)
      )
      return f"eta: {timedelta(seconds=int(estimated_remaining))}"
    except ZeroDivisionError:
      return ""

  def update_exit_status_table(self):
    # Throttle table updates to avoid frequent re-rendering in tmux
    current_time = time.time()
    if current_time - self._last_table_update < self._table_update_interval:
      return
    self._last_table_update = current_time

    # We cannot update the existing table, so we need to create a new one and
    # assign it back to the render group.
    t = Table()
    t.add_column("Exit Status")
    t.add_column("Count", justify="right", style="bold cyan")
    t.add_column("Most recent instances")
    try:
      with self._lock:
        t.show_header = True
        # Sort by number of instances in descending order
        sorted_items = sorted(
          self._instances_by_exit_status.items(),
          key=lambda x: len(x[1]),
          reverse=True,
        )
        for status, instances in sorted_items:
          # Display recent instances, one per line for better readability
          recent_instances = list(reversed(instances))[:10]
          instances_str = "\n".join(recent_instances)
          if len(instances) > 10:
            instances_str += f"\n... and {len(instances) - 10} more"
          t.add_row(status, str(len(instances)), instances_str)
        # Update render group inside lock to avoid race condition with Live refresh
        self.render_group.renderables[0] = t
    except Exception:
      # Silently ignore rendering errors in tmux to prevent crashes
      pass

  def _update_eta(self) -> None:
    # Throttle ETA updates to reduce rendering load in tmux
    current_time = time.time()
    if current_time - self._last_eta_update < self._eta_update_interval:
      return
    self._last_eta_update = current_time
    with self._lock:
      try:
        self._main_progress_bar.update(
          self._main_task_id,
          eta=self._get_eta_text(),
        )
      except Exception:
        # Silently ignore rendering errors in tmux
        pass

  def update_instance_status(self, instance_id: str, message: str):
    # Throttle status updates per instance to reduce rendering load
    current_time = time.time()
    last_update = self._last_status_update.get(instance_id, 0)
    if current_time - last_update < self._status_update_interval:
      return
    self._last_status_update[instance_id] = current_time

    with self._lock:
      try:
        self._task_progress_bar.update(
          self._spinner_tasks[instance_id],
          status=_shorten_str(message, 35),
          instance_id=_shorten_str(instance_id, 55, shorten_left=True),
        )
      except (KeyError, Exception):
        # Silently ignore rendering errors or missing task IDs
        pass
    self._update_eta()

  def on_instance_start(self, instance_id: str):
    with self._lock:
      self._spinner_tasks[instance_id] = self._task_progress_bar.add_task(
        description=f"Task {instance_id}",
        status="Task initialized",
        total=None,
        instance_id=instance_id,
      )

  def on_instance_end(self, instance_id: str, exit_status: str | None) -> None:
    self._instances_by_exit_status[exit_status].append(instance_id)
    # Clean up status update tracking for this instance
    self._last_status_update.pop(instance_id, None)
    with self._lock:
      try:
        self._task_progress_bar.remove_task(self._spinner_tasks[instance_id])
      except KeyError:
        pass
      self._main_progress_bar.update(
        self._main_task_id,
        advance=1,
        eta=self._get_eta_text(),
        description="[cyan]Overall Progress",
      )
    self.update_exit_status_table()
    self._update_eta()
    if self._yaml_report_path is not None:
      self._save_overview_data_yaml(self._yaml_report_path)

  def on_uncaught_exception(
    self, instance_id: str, exception: Exception
  ) -> None:
    self.on_instance_end(instance_id, f"Uncaught {type(exception).__name__}")

  def print_report(self) -> None:
    """Print complete list of instances and their exit statuses."""
    for status, instances in self._instances_by_exit_status.items():
      print(f"{status}: {len(instances)}")
      for instance in instances:
        print(f"  {instance}")

  def _get_overview_data(self) -> dict:
    """Get data like exit statuses, etc."""
    return {
      # convert defaultdict to dict because of serialization
      "instances_by_exit_status": dict(self._instances_by_exit_status),
    }

  def _save_overview_data_yaml(self, path: Path) -> None:
    """Save a yaml report of the instances and their exit statuses."""
    with self._lock:
      path.write_text(yaml.dump(self._get_overview_data(), indent=4))
