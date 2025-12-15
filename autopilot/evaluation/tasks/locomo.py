import json
import os
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from datasets import load_dataset
from typing_extensions import override

from autopilot.prompts import LOCOMO_PROMPT
from autopilot.utils import console, execute_cmd, get_platform

from . import base
from .registry import TASKS

PROJECT_DIR = Path(__file__).parent.parent.parent.parent
BENCH_NAME = "locomo"
BENCH_DIR = os.path.join(PROJECT_DIR, "external", "locomo")

# common docker dir is in autopilot/tools/locomo/dockerfile
COMMONS_LOCOMO_DOCKER_DIR = os.path.join(PROJECT_DIR, "tools", "locomo")


def load_locomo():
  dataset = json.load(
    open(os.path.join(BENCH_DIR, "data", "locomo10.json"), "r")
  )

  return dataset


@TASKS.register(BENCH_NAME)
class LocomoTask(base.Task):
  def __init__(self, name: str, benchmark: str = BENCH_NAME):
    self.locomo_dataset = load_locomo()
    # self.name is in the format of <conversation_id>_<question_id>
    super().__init__(name, benchmark)

  @property
  def dir(self):
    # This is a placeholder, as Locomo tasks do not have a specific directory.
    return os.path.join(BENCH_DIR, "tasks", self.name)

  def launch_container(self) -> None:
    dockerfile_path = os.path.join(COMMONS_LOCOMO_DOCKER_DIR, "Dockerfile")
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
            os.path.join(COMMONS_LOCOMO_DOCKER_DIR, "build_image"),
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

    self.write_conversation()

  def write_conversation(self):
    # Write a conversation.txt file with the conversation
    conversation = self.locomo_instance["conversation"]
    conversation_file = os.path.join("/testbed", "conversation.txt")
    execute_cmd(
      [
        "docker",
        "exec",
        self.container_name,
        "bash",
        "-c",  # conversation contains single, double quotes and backticks
        f"echo {shlex.quote(conversation)} > {conversation_file}",
      ]
    )
    return

  def process_conversation(self, conversation):
    all_sessions = []
    # Get speaker names
    speaker_a = conversation["speaker_a"]
    speaker_b = conversation["speaker_b"]

    for key in conversation.keys():
      # We extract "session_\d+" keys
      if (
        key in ["speaker_a", "speaker_b"] or "date" in key or "timestamp" in key
      ):
        continue

      # The date_time_key is in the format of "session_\d+_date_time"
      date_time_key = key + "_date_time"
      timestamp = conversation[date_time_key]
      # timestamp is in the format of "1:56 pm on 8 May, 2023"
      # convert it to sortable format "2023-05-08 13:56"
      dt = datetime.strptime(timestamp, "%I:%M %p on %d %B, %Y")
      sortable_timestamp = dt.strftime("%Y-%m-%d %H:%M")

      chats = conversation[key]

      messages = []
      for chat in chats:
        if chat["speaker"] == speaker_a:
          messages.append(f"{speaker_a}: {chat['text']}")
        elif chat["speaker"] == speaker_b:
          messages.append(f"{speaker_b}: {chat['text']}")
        else:
          raise ValueError(f"Unknown speaker: {chat['speaker']}")
      all_sessions.append((sortable_timestamp, timestamp, messages))

    all_sessions.sort()
    formatted_sessions = [
      f"At {session[1]}: \n\n" + "\n".join(session[2])
      for session in all_sessions
    ]
    return "\n\n".join(formatted_sessions)

  @property
  def locomo_instance(self):
    """
    {
        "question": "When did Caroline go to the LGBTQ support group?",
        "answer": "7 May 2023",
        "evidence": [
          "D1:3"
        ],
        "category": 2
      }
    """
    conversation_id = int(self.name.split("_")[0])
    question_id = int(self.name.split("_")[1])

    conversation = self.process_conversation(
      self.locomo_dataset[conversation_id]["conversation"]
    )
    question = str(
      self.locomo_dataset[conversation_id]["qa"][question_id]["question"]
    )
    answer = str(
      self.locomo_dataset[conversation_id]["qa"][question_id]["answer"]
    )

    return {
      "conversation": conversation,
      "answer": answer,
      "question": question,
    }

  @property
  def description(self) -> str:
    conversation = self.locomo_instance["conversation"]
    question = self.locomo_instance["question"]

    # read the conversation, and answer the question
    template = LOCOMO_PROMPT

    filled_template: str = template.format(
      conversation=conversation,
      question=question,
    )
    return filled_template

  @property
  def answer(self) -> str:
    answer: str = self.locomo_instance["answer"]
    return str(answer)

  @property
  def question(self) -> str:
    question: str = self.locomo_instance["question"]
    return str(question)

  @property
  def files_to_copy(self) -> list:
    # use llm_judge.py as the evaluation script to decide if the answer is correct
    # It will read /tmp/tasks/answer.txt for the gold answer
    # and read the model's answer from /testbed/answer.txt
    host_script_path = os.path.join(COMMONS_LOCOMO_DOCKER_DIR, "test_script.sh")

    files = [(host_script_path, self.eval_script)]
    return files

  def files_to_copy_to_host(self, host_dir: str) -> List[Tuple[str, str]]:
    return []

  @property
  def eval_script(self):
    return "/tmp/tasks/shared_scripts/test_script.sh"

  @property
  def llm_judge_script(self):
    return "/tmp/tasks/shared_scripts/llm_judge.py"

  @property
  def container_name(self):
    return f"{BENCH_NAME}_{self.session_name}"

  @property
  def envs(self) -> dict:
    project_name = f"{BENCH_NAME}"
    log_path = "/logs" if get_platform() != "darwin" else "/tmp/logs"
    return {
      "LOCOMO_TASK_BUILD_CONTEXT_DIR": COMMONS_LOCOMO_DOCKER_DIR,
      "LOCOMO_TASK_DOCKER_CLIENT_IMAGE_NAME": project_name,
      "LOCOMO_TASK_DOCKER_NAME_PREFIX": self.container_name,
      "LOCOMO_TEST_DIR": os.path.join(COMMONS_LOCOMO_DOCKER_DIR, "tests"),
      "LOCOMO_TASK_LOGS_PATH": log_path,
      "LOCOMO_CONTAINER_LOGS_PATH": log_path,
      "LOCOMO_TASK_DOCKER_CLIENT_CONTAINER_NAME": self.container_name,
      "COMPOSE_PROJECT_NAME": self.container_name,
      "COMPOSE_DOCKER_CLI_BUILD": "1",
      "DOCKER_BUILDKIT": "1",
      "TEST_DIR": f"/tmp/tasks/{self.name}/tests",
      "TASK_DIR": f"/tmp/tasks/{self.name}",
    }

  @property
  def compose_file(self) -> str:
    options = []
    options.append(
      os.path.join(COMMONS_LOCOMO_DOCKER_DIR, "docker-compose.yaml")
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
  def task_names(cls) -> List:
    # Return list of string indices for all test instances
    instance = cls(
      name="dummy"
    )  # Create a dummy instance to access locomo_dataset
    return [
      f"{i}_{j}"
      for i in range(len(instance.locomo_dataset))
      for j in range(len(instance.locomo_dataset[i]["qa"]))
    ]
