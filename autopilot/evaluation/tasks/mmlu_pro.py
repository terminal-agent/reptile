import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from typing_extensions import override

from autopilot.data import InteractionMode
from autopilot.prompts import MMLU_PRO_PROMPT, MMLU_PRO_PROMPT_PAPER_VERSION
from autopilot.utils import console, execute_cmd, get_platform

from . import base
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "mmlu_pro"
# In MMLU-Pro, each task is a single question, so there is no specific directory for each task. BENCH_DIR is just a placeholder.
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "MMLU-Pro")

# common docker dir is in autopilot/tools/mmlu_pro_dockerfile
COMMONS_MMLU_DOCKER_DIR = os.path.join(PROJECT_DIR, "tools", "mmlu_pro")


@TASKS.register(BENCH_NAME)
class MMLUProTask(base.Task):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    # self.name is an integer index to MMLU_PRO_DATASET test set
    super().__init__(name, benchmark)

  @property
  def dir(self):
    # In MMLU-Pro, each task is a single question, so there is no specific directory for each task. This method is just a placeholder.
    return os.path.join(BENCH_DIR, "tasks", self.name)

  def launch_container(self) -> None:
    dockerfile_path = os.path.join(COMMONS_MMLU_DOCKER_DIR, "Dockerfile")
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
            os.path.join(COMMONS_MMLU_DOCKER_DIR, "build_image"),
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
  def mmlu_instance(self):
    index = int(self.name)
    with open(
      os.path.join(BENCH_DIR, "tasks", self.name, "instance.json"), "r"
    ) as f:
      instance = json.load(f)
    return instance

  @property
  def description(self) -> str:
    question = self.mmlu_instance["question"]
    options = self.mmlu_instance["options"]
    template = (
      MMLU_PRO_PROMPT_PAPER_VERSION
      if self.interaction_mode == InteractionMode.NAIVE
      else MMLU_PRO_PROMPT
    )  # use the query template from paper for naive mode

    filled_template: str = template.format(
      question=question,
      options="\n".join(
        [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)]
      ),
    )
    return filled_template

  @property
  def answer(self) -> str:
    answer: str = self.mmlu_instance["answer"]
    return answer

  @property
  def files_to_copy(self) -> list:
    host_script_path = os.path.join(COMMONS_MMLU_DOCKER_DIR, "test_script.sh")
    files = [(host_script_path, self.eval_script)]
    return files

  def files_to_copy_to_host(self, host_dir: str) -> List[Tuple[str, str]]:
    return []

  @property
  def eval_script(self):
    return "/tmp/tasks/shared_scripts/test_script.sh"

  @property
  def container_name(self):
    return f"{BENCH_NAME}_{self.session_name}"

  @property
  def envs(self) -> dict:
    project_name = f"{BENCH_NAME}"
    log_path = "/logs" if get_platform() != "darwin" else "/tmp/logs"
    return {
      "MMLU_PRO_TASK_BUILD_CONTEXT_DIR": COMMONS_MMLU_DOCKER_DIR,
      "MMLU_PRO_TASK_DOCKER_CLIENT_IMAGE_NAME": project_name,
      "MMLU_PRO_TASK_DOCKER_NAME_PREFIX": self.container_name,
      "MMLU_PRO_TEST_DIR": os.path.join(COMMONS_MMLU_DOCKER_DIR, "tests"),
      "MMLU_PRO_TASK_LOGS_PATH": log_path,
      "MMLU_PRO_CONTAINER_LOGS_PATH": log_path,
      "MMLU_PRO_TASK_DOCKER_CLIENT_CONTAINER_NAME": self.container_name,
      "COMPOSE_PROJECT_NAME": self.container_name,
      "COMPOSE_DOCKER_CLI_BUILD": "1",
      "DOCKER_BUILDKIT": "1",
      "TEST_DIR": f"/tmp/tasks/{self.name}/tests",
      "TASK_DIR": f"/tmp/tasks/{self.name}",
    }

  @property
  def compose_file(self) -> str:
    options = []
    options.append(os.path.join(COMMONS_MMLU_DOCKER_DIR, "docker-compose.yaml"))
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

  @override
  def generate_solution(self) -> Optional[str]:
    return None

  @classmethod
  def task_names(self) -> List:
    import glob

    task_files = glob.glob(os.path.join(BENCH_DIR, "tasks", "*"))
    task_names = [
      os.path.basename(task_file)
      for task_file in task_files
      if os.path.isdir(task_file)
    ]
    return task_names
