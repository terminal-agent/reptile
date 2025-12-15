import os
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from typing_extensions import override

from autopilot.utils import get_platform

from . import base
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "terminal_bench"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "terminal-bench")


@TASKS.register(BENCH_NAME)
class TerminalBenchTask(base.Task):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @override
  def generate_solution(self) -> Optional[str]:
    """Generate solution.sh from solution.yaml file"""
    solution_yaml_path = os.path.join(self.dir, "solution.yaml")
    solution_sh_path = os.path.join(self.dir, "solution.sh")

    if os.path.exists(solution_sh_path):
      return solution_sh_path
    if not os.path.exists(solution_yaml_path):
      return None

    with open(solution_yaml_path, "r") as f:
      solution_yaml = yaml.safe_load(f)
    with open(solution_sh_path, "w") as f:
      f.write("#!/bin/bash\n")
      for cmd_obj in solution_yaml:
        f.write(cmd_obj["command"].rstrip() + "\n")
    return solution_sh_path

  @property
  def dir(self):
    return os.path.join(BENCH_DIR, "tasks", self.name)

  @property
  def description(self) -> str:
    task_yaml_path = os.path.join(self.dir, "task.yaml")
    with open(task_yaml_path, "r") as f:
      task_yaml = yaml.safe_load(f)
    description: str = task_yaml["instruction"]
    return description

  @property
  def files_to_copy(self) -> list:
    host_eval_script = f"{PROJECT_DIR}/external/test_script.sh"
    files = [
      (self.dir, f"/tmp/tasks/{self.name}"),
      (
        f"{BENCH_DIR}/adapters/deveval/templates/acceptance_testing/tests/run-uv-pytest.sh",
        "/tmp/tasks/shared_scripts/",
      ),
      (
        f"{BENCH_DIR}/adapters/deveval/templates/acceptance_testing/tests/setup-uv-pytest.sh",
        "/tmp/tasks/shared_scripts/",
      ),
      (host_eval_script, self.eval_script),
    ]

    # Generate solution.sh on-the-fly if it exists
    solution_path = self.generate_solution()
    if solution_path:
      files.append((solution_path, "/tmp/tasks/shared_scripts/solution.sh"))

    return files

  def files_to_copy_to_host(self, host_dir: str) -> List[Tuple[str, str]]:
    return []

  @property
  def eval_script(self):
    return "/tmp/tasks/shared_scripts/test_script.sh"

  @property
  def compose_file(self) -> str:
    options = []
    options.append(os.path.join(self.dir, "docker-compose.yaml"))
    options.append(
      f"{BENCH_DIR}/adapters/deveval/templates/acceptance_testing/docker-compose.yaml"
    )
    original_file = None
    for option in options:
      if os.path.exists(option):
        original_file = option
        break

    if not original_file:
      raise FileNotFoundError(
        f"No docker-compose.yaml found for task {self.name}"
      )

    not_patch_list = ["simple-sheets-put"]
    if self.name in not_patch_list:
      return original_file

    modified_file = os.path.join(
      os.path.dirname(original_file),
      "patched-docker-compose.yaml",
    )

    if not os.path.exists(modified_file):
      with open(original_file, "r") as f:
        compose_config = yaml.safe_load(f)

      if "services" in compose_config:
        for service_name, service_config in compose_config["services"].items():
          if "networks" in service_config:
            del service_config["networks"]
          service_config["network_mode"] = "bridge"

      with open(modified_file, "w") as f:
        yaml.dump(compose_config, f)

    return modified_file

  @property
  def container_name(self):
    return f"{BENCH_NAME}_{self.session_name}".replace(".", "-")

  @property
  def envs(self) -> dict:
    project_name = f"{BENCH_NAME}_{self.name}".replace(".", "-")
    log_path = (
      "/t_bench_logs" if get_platform() != "darwin" else "/tmp/t_bench_logs"
    )
    agent_log_path = (
      "/t_bench_agent_logs"
      if get_platform() != "darwin"
      else "/tmp/t_bench_agent_logs"
    )
    return {
      "T_BENCH_TASK_BUILD_CONTEXT_DIR": self.dir,
      "T_BENCH_TASK_DOCKER_CLIENT_IMAGE_NAME": project_name,
      "T_BENCH_TASK_DOCKER_NAME_PREFIX": self.container_name,
      "T_BENCH_TEST_DIR": os.path.join(self.dir, "tests"),
      "T_BENCH_TASK_LOGS_PATH": log_path,
      "T_BENCH_TASK_AGENT_LOGS_PATH": agent_log_path,
      "T_BENCH_CONTAINER_LOGS_PATH": log_path,
      "T_BENCH_CONTAINER_AGENT_LOGS_PATH": agent_log_path,
      "T_BENCH_TASK_DOCKER_CLIENT_CONTAINER_NAME": self.container_name,
      "COMPOSE_PROJECT_NAME": self.container_name,
      "COMPOSE_DOCKER_CLI_BUILD": "1",
      "DOCKER_BUILDKIT": "1",
      "TEST_DIR": f"/tmp/tasks/{self.name}/tests",
      "TASK_DIR": f"/tmp/tasks/{self.name}",
    }

  @classmethod
  def task_names(self) -> List:
    disabled_list = {
      "broken-networking",  # env bug
      "build-initramfs-qemu",  # env bug
      "build-tcc-qemu",  # env bug
      "extract-safely",  # env bug, cannot setup container due to space limit, where uv cannot install
      "spring-messaging-vul",  # env bug
      "mixed-integer-programming",  # env bug
      "security-celery-redis-rce",  # env bug
      "build-linux-kernel-qemu",  # too long git clone time, cannot quit TUI
      "predicate-pushdown-bench",  # too long eval time, 10 minutes to complete
      "reshard-c4-data",  # too long eval time, 10 minutes to complete
      "simple-sheets-put",  # docker network issue
    }
    tasks = []
    for item in os.listdir(f"{BENCH_DIR}/tasks"):
      if item in disabled_list:
        print(f"Skipping {item}")
        continue
      item_path = os.path.join(f"{BENCH_DIR}/tasks", item)
      if os.path.isdir(item_path):
        tasks.append(item)
    return tasks
