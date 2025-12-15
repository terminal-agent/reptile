import os
from pathlib import Path
from typing import List

from . import terminal_bench
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "terminal_bench_sample"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "terminal-bench")


@TASKS.register(BENCH_NAME)
class TerminalBenchSampleTask(terminal_bench.TerminalBenchTask):
  """
  This task is a sample of terminal_bench.Task.
  It is used to unit-test the batch_eval.py.
  """

  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @property
  def dir(self):
    return os.path.join(BENCH_DIR, "tasks", self.name)

  @classmethod
  def task_names(self) -> List:
    unit_test_list = [
      "hello-world",
      "hello-world",
    ]  # hello-world is the easiest task, no risk of failure
    tasks = []
    for item in unit_test_list:
      item_path = os.path.join(f"{BENCH_DIR}/tasks", item)
      if os.path.isdir(item_path):
        tasks.append(item)
    return tasks
