import os
import stat
from pathlib import Path
from typing import List, Optional

from typing_extensions import override

from . import swe_bench
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "swebench_verified"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "swe-bench")
TASK_DIR = os.path.join(PROJECT_DIR, "external", "swebench-verified")


@TASKS.register(BENCH_NAME)
class SWEBenchVerifiedTask(swe_bench.SWEBenchTask):
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
    task_names = [
      os.path.basename(task_file)
      for task_file in task_files
      if os.path.isdir(task_file)
    ]
    return task_names
