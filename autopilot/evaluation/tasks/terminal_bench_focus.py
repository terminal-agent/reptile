import os
from pathlib import Path
from typing import List

from . import terminal_bench
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "terminal_bench_focus"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "terminal-bench")


@TASKS.register(BENCH_NAME)
class TerminalBenchFocusTask(terminal_bench.TerminalBenchTask):
  """
  This task is the focus task selected for evaluation.
  It is used to evaluate the performance of the autopilot agent.
  """

  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @property
  def dir(self):
    return os.path.join(BENCH_DIR, "tasks", self.name)

  @classmethod
  def task_names(self) -> List:
    unit_test_list = [
      ### devstral can do but not stable enough
      "attention-mil",
      "broken-python",
      "chem-property-targeting",
      "conda-env-conflict-resolution",
      "create-bucket",
      "cross-entropy-method",
      "csv-to-parquet",
      "eval-mteb",
      "fix-pandas-version",
      "fix-permissions",
      "heterogeneous-dates",
      "hf-model-inference",
      "logistic-regression-divergence",
      "mlflow-register",
      "new-encrypt-command",
      "organization-json-generator",
      "pandas-sql-query",
      "polyglot-c-py",
      "privilege-escalation",
      "prove-plus-comm",
      "recover-obfuscated-files",
      "stable-parallel-kmeans",
      "swe-bench-fsspec",
      "swe-bench-langcodes",
      "vim-terminal-task",
      ### deepseek3.1 can do but devstral cannot do
      "assign-seats",
      "configure-git-webserver",
      "extract-elf",
      "get-bitcoin-nodes",
      "git-workflow-hack",
      "grid-pattern-transform",
      "incompatible-python-fasttext",
      "jq-data-processing",
      "openssl-selfsigned-cert",
      "pandas-etl",
      "parallel-particle-simulator",
      "processing-pipeline",
      "security-vulhub-minio",
      "setup-custom-dev-env",
      "sqlite-with-gcov",
    ]
    tasks = []
    for item in unit_test_list:
      item_path = os.path.join(f"{BENCH_DIR}/tasks", item)
      if os.path.isdir(item_path):
        tasks.append(item)
    return tasks
