import os
from pathlib import Path
from typing import List, Optional

from typing_extensions import override

from . import swegym
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "swegym_focus"
TASK_DIR = os.path.join(PROJECT_DIR, "external", "swegym")


@TASKS.register(BENCH_NAME)
class SWEGymFocusTask(swegym.SWEGymTask):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @classmethod
  def task_names(self) -> List:
    task_names = [
      line.strip()
      for line in open(
        "scripts/rl_training/swegym_focus_valid_tasks.txt"
      ).readlines()
      if line.strip()
    ]

    return task_names
