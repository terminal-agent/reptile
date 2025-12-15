import os
from pathlib import Path
from typing import List, Optional

from typing_extensions import override

from . import swe_bench
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "swegym"
TASK_DIR = os.path.join(PROJECT_DIR, "external", "swegym")


@TASKS.register(BENCH_NAME)
class SWEGymTask(swe_bench.SWEBenchTask):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @override
  def generate_solution(self) -> Optional[str]:
    """Directly use solution.sh"""
    solution_sh_path = os.path.join(self.dir, "solution.sh")

    if os.path.exists(solution_sh_path):
      return solution_sh_path
    raise FileNotFoundError(f"solution.sh not found in {self.dir}")

  @property
  def dir(self):
    return os.path.join(TASK_DIR, "tasks", self.name)

  @classmethod
  def task_names(self) -> List:
    import glob

    task_files = glob.glob(os.path.join(TASK_DIR, "tasks", "*"))
    # skip task name containing `project-monai__monai` due large docker images size
    task_names = [
      os.path.basename(task_file)
      for task_file in task_files
      if os.path.isdir(task_file)
      and "project-monai__monai" not in os.path.basename(task_file)
    ]

    valid_task_names = [
      line.strip()
      for line in open("scripts/rl_training/swegym_valid_tasks.txt").readlines()
      if line.strip()
    ]

    return [
      task_name for task_name in task_names if task_name in valid_task_names
    ]
