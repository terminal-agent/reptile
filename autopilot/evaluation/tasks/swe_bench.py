import os
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from typing_extensions import override

from autopilot.utils import console, execute_cmd, get_platform

from . import base
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "swe_bench"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "swe-bench")


@TASKS.register(BENCH_NAME)
class SWEBenchTask(base.Task):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    super().__init__(name, benchmark)

  @property
  def dir(self):
    return os.path.join(BENCH_DIR, "tasks", self.name)

  @property
  def description(self) -> str:
    task_yaml_path = os.path.join(self.dir, "task.yaml")
    with open(task_yaml_path, "r") as f:
      task_yaml = yaml.safe_load(f)
    description: str = task_yaml["descriptions"][0]["description"]
    return description

  @property
  def files_to_copy(self) -> list:
    host_eval_script = f"{PROJECT_DIR}/external/test_script.sh"
    files = [
      (f"{self.dir}/.", f"/tmp/tasks/{self.name}"),
      (f"{BENCH_DIR}/shared/scripts/.", "/tmp/tasks/shared_scripts"),
      (f"{BENCH_DIR}/shared/scripts/.", f"/tmp/tasks/{self.name}/tests"),
      (host_eval_script, self.eval_script),
    ]

    # Generate solution.sh on-the-fly if it exists
    solution_path = self.generate_solution()
    if solution_path:
      files.append((solution_path, "/tmp/tasks/shared_scripts/solution.sh"))
    return files

  def files_to_copy_to_host(self, host_dir: str) -> List[Tuple[str, str]]:
    files = [
      ("/tmp/tasks/patch.txt", os.path.join(host_dir, "patch.txt")),
    ]
    return files

  @property
  def eval_script(self):
    return "/tmp/tasks/shared_scripts/test_script.sh"

  @property
  def compose_file(self) -> str:
    options = []
    task_file = os.path.join(self.dir, "task.yaml")
    env_name = None
    with open(task_file, "r") as f:
      task_yaml = yaml.safe_load(f)
      env_name = task_yaml["env_name"]
    if env_name:
      options.append(
        f"{BENCH_DIR}/shared/environments/{env_name}/docker-compose.yaml"
      )
    options.append(os.path.join(self.dir, "docker-compose.yaml"))
    options.append(f"{BENCH_DIR}/shared/defaults/docker-compose.yaml")
    original_file = None
    for option in options:
      if os.path.exists(option):
        original_file = option
        break

    if not original_file:
      raise FileNotFoundError(
        f"No docker-compose.yaml found for task {self.name}"
      )

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
    return f"{BENCH_NAME}_{self.session_name}"

  @property
  def envs(self) -> dict:
    project_name = f"{BENCH_NAME}_{self.name}"
    log_path = "/logs" if get_platform() != "darwin" else "/tmp/logs"
    return {
      "SWE_BENCH_TASK_BUILD_CONTEXT_DIR": self.dir,
      "SWE_BENCH_TASK_DOCKER_CLIENT_IMAGE_NAME": project_name,
      "SWE_BENCH_TASK_DOCKER_NAME_PREFIX": self.container_name,
      "SWE_BENCH_TEST_DIR": os.path.join(self.dir, "tests"),
      "SWE_BENCH_TASK_LOGS_PATH": log_path,
      "SWE_BENCH_CONTAINER_LOGS_PATH": log_path,
      "SWE_BENCH_TASK_DOCKER_CLIENT_CONTAINER_NAME": self.container_name,
      "COMPOSE_PROJECT_NAME": self.container_name,
      "COMPOSE_DOCKER_CLI_BUILD": "1",
      "DOCKER_BUILDKIT": "1",
      "TEST_DIR": f"/tmp/tasks/{self.name}/tests",
      "TASK_DIR": f"/tmp/tasks/{self.name}",
    }

  @classmethod
  def task_names(self) -> List:
    return [
      "django-10924",
      "django-15061",
      "requests-1963",
      "requests-2148",
      "requests-2674",
      "requests-863",
      "sglang-6709",
      "sglang-6709-easy-1",
      "sglang-6709-easy-2",
      "sglang-6709-hard",
      "sglang-6709-medium",
      "xarray-3364",
      "xarray-4248",
      "xarray-4493",
      "xarray-5131",
    ]

  def launch_container(self):
    dockerfile_path = os.path.join(self.dir, "Dockerfile")
    with open(dockerfile_path, "r") as f:
      first_line = f.readline().strip()
      image_name = first_line.split()[-1].split(":")[0]
    tag = "latest"
    try:
      execute_cmd(["docker", "image", "inspect", f"{image_name}:{tag}"])
    except RuntimeError:
      console.print(
        f"[green]{self.name} Building image {image_name}:{tag}[/green]"
      )
      try:
        execute_cmd(
          [
            "docker",
            "buildx",
            "build",
            "-t",
            f"{image_name}:{tag}",
            "--load",
            os.path.join(self.dir, "build_image"),
          ]
        )
        console.print(
          f"[green]{self.name} Image {image_name}:{tag} built successfully.[/green]"
        )
      except RuntimeError as e:
        console.print(
          f"[red]{self.name} Image {image_name}:{tag} build failed."
        )
        raise e
    super().launch_container()

  @property
  def test_metadata(self):
    """Get test metadata from task.yaml"""
    task_yaml_path = os.path.join(self.dir, "task.yaml")
    with open(task_yaml_path, "r") as f:
      task_yaml = yaml.safe_load(f)
    return task_yaml.get("test_metadata", {})

  @property
  def fail_to_pass_tests(self):
    """Get FAIL_TO_PASS test list"""
    return self.test_metadata.get("fail_to_pass_tests", [])

  @property
  def pass_to_pass_tests(self):
    """Get PASS_TO_PASS test list"""
    return self.test_metadata.get("pass_to_pass_tests", [])

  @override
  def generate_solution(self) -> Optional[str]:
    return None
