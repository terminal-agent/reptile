import getpass
import gzip
import json
import os
import time
from queue import Queue
from threading import Lock, Thread
from typing import TYPE_CHECKING, List, Optional, Union

import yaml
from pymongo import MongoClient

from autopilot.config import GLOBAL_CONFIG
from autopilot.constants import _CACHE_ROOT
from autopilot.data import ContextData, WorkflowConfig
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS
from autopilot.utils import execute_cmd

from .base_hook import BaseHook

if TYPE_CHECKING:
  from autopilot.node.base import BaseNode
  from autopilot.workflow.base import BaseWorkflow

__all__ = ["GitHubTelemetryHook", "TelemetryHook"]


class TelemetryHook(BaseHook):
  """
  TelemetryHook is a hook that is used to record the data of the workflow and save it to a remote destination.
  """

  pass


class GitHubTelemetryHook(TelemetryHook):
  """
  GitHubTelemetryHook is a hook that is used to record the data of the workflow and save it to a remote GitHub repository.

  Args:
    remote_url (str): The URL of the remote GitHub repository.
    ssh_key_path (str): The path to the SSH key for the remote GitHub repository.
    name (Optional[str]): The name of the session. If not provided, a timestamp in hex will be used.
    push (bool): Whether to push the data to the remote GitHub repository.
  """

  def __init__(
    self,
    remote_url: str,
    ssh_key_path: str,
    name: Optional[str] = None,
    push: bool = True,
  ):
    super().__init__(
      priority=100
    )  # higher priority to ensure the telemetry is recorded
    self.remote_url = remote_url
    self.ssh_key_path = ssh_key_path
    self.push = push

    user_key = os.path.expanduser("~/.ssh/id_rsa")
    try:
      execute_cmd(
        ["git", "ls-remote", "--exit-code", remote_url],
        env={
          "GIT_SSH_COMMAND": f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        },
      )
    except Exception:
      if os.path.exists(user_key):
        self.ssh_key_path = user_key  # Fallback to user key

    if name is None:
      # we use a timestamp in hex to represent the session name
      self.name = (
        f"session-{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
      )
    else:
      self.name = name

    self.workspace = _CACHE_ROOT
    self.repo_dir = self.workspace.joinpath("sessions", self.name)
    self.push_queue: Queue[bool] = Queue()
    self.branch_mutex = Lock()
    self.last_turning_info_hash: Optional[int] = None

  def _init_workspace(self) -> None:
    """
    Initialize the workspace for the telemetry hook.
    """
    self.repo_dir.mkdir(parents=True, exist_ok=True)

  def _init_repo(self) -> None:
    """
    Initialize a empty git repo.
    """
    with self.branch_mutex:
      # initialize
      self.git("init")
      self.git("branch", "-m", self.name)
      username = getpass.getuser()

      # config user name and email if not set
      result = self.git("config", "user.name")
      if result is None or not result.strip():
        self.git("config", "user.name", username)

      result = self.git("config", "user.email")
      if result is None or not result.strip():
        self.git("config", "user.email", f"{username}@users.noreply.github.com")

      # set remote
      if self.remote_url:
        self.git("remote", "add", "origin", self.remote_url)

  def _start_push_loop(self) -> None:
    """
    Create a thread to asynchronously push the data to the remote GitHub repository.
    """

    def push():
      while self.push_queue.get():
        self.push_to_remote()

    self.push_thread = Thread(target=push)
    self.push_thread.daemon = True
    self.push_thread.start()

  # ========================
  # Git operations
  # ========================
  def _async_push(self) -> None:
    """
    Asynchronously push the data to the remote GitHub repository.
    """
    self.push_queue.put(True)

  def git(self, *command) -> Optional[str]:
    """
    Execute a git command.

    Args:
      command (str): The git command to execute.

    Returns:
      The output of the git command.
    """
    command_list = ["git", "-C", str(self.repo_dir), *command]
    env = {
      "GIT_SSH_COMMAND": (
        f"ssh -i {self.ssh_key_path} "
        "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
      )
    }

    try:
      result: str = execute_cmd(command_list, env=env)
      return result
    except Exception as e:
      if self.push:
        self.disable()
        print(
          f"failed to execute git command: {command}, disabling github telemetry for this session"
        )
      return None

  def _record_system_prompt(self, system_prompt: str) -> None:
    """
    Record the system prompt to the remote GitHub repository.

    Args:
      system_prompt (str): The system prompt to record.
    """
    sys_prompt_path = self.repo_dir.joinpath("system_prompt.txt")
    with open(sys_prompt_path, "wt") as f:
      f.write(system_prompt)

    with self.branch_mutex:
      self.git("add", sys_prompt_path)
      self.git("commit", "-m", "system prompt")

  def _record_other_info(self, workflow_config: WorkflowConfig) -> None:
    """
    Record the other info to the remote GitHub repository.

    Args:
      workflow_config (WorkflowConfig): The workflow config to record.
    """
    # locate the target model
    model_by_arg = workflow_config.model

    if model_by_arg is None:
      model_config = GLOBAL_CONFIG.models
      model_list = [(config.name, config.priority) for config in model_config]
      model_list.sort(key=lambda x: x[1], reverse=True)
      model_name = model_list[0][0]
    else:
      model_name = model_by_arg

    info = {
      "model_name": model_name,
      "username": getpass.getuser(),
      "max_steps": workflow_config.max_steps,
      "max_current_steps": workflow_config.max_current_steps,
      "time_out": workflow_config.time_out,
    }
    info_path = self.repo_dir.joinpath("other_info.yml")
    with open(info_path, "wt") as f:
      yaml.safe_dump(info, f)

    with self.branch_mutex:
      self.git("add", info_path)
      self.git("commit", "-m", "other info")

  def push_to_remote(self) -> None:
    """
    Explicitly push to remote repository.
    """
    if self.remote_url:
      with self.branch_mutex:
        try:
          self.git("push", "-u", "origin", self.name)
        except Exception as e:
          print(f"failed to push to remote: {e}")

  # ========================
  # Hooks
  # ========================
  def pre_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    self._init_workspace()
    self._init_repo()
    self._record_system_prompt(workflow.workflow_config.system_prompt)
    self._record_other_info(workflow.workflow_config)
    self._start_push_loop()

  def post_node_execute(self, data: ContextData, node: "BaseNode") -> None:
    filepath = self.repo_dir.joinpath("history.yml")

    if filepath.exists():
      # read the current num_steps
      with open(filepath, "rt") as f:
        history = yaml.safe_load(f)
      num_steps = len(history)
    else:
      num_steps = 0

    new_steps = data.history[num_steps:]

    if len(new_steps) > 0:
      with open(filepath, "at") as f:
        for step_data in new_steps:
          f.write(yaml.safe_dump([step_data.to_dict()]))
          f.write("\n")

      # Record vLLM info separately
      vllm_info_path = self.repo_dir.joinpath("vllm_info.json.gz")
      vllm_info_data = {}
      if vllm_info_path.exists():
        with gzip.open(vllm_info_path, "rt") as f:
          vllm_info_data = json.load(f)

      for step_data in new_steps:
        step_key = f"{step_data.step}"
        vllm_info_data[step_key] = data.vllm_info_map[step_data.step].to_dict()

      # Save as gzip-compressed JSON to reduce file size
      with gzip.open(vllm_info_path, "wt", compresslevel=6) as f:
        json.dump(vllm_info_data, f, separators=(",", ":"))

      with self.branch_mutex:
        self.git("add", filepath)
        self.git("commit", "-m", f"step {num_steps}")

        if self.remote_url and self.push:
          self._async_push()

    if data.turning_info:
      current_turning_info_str = str(sorted(data.turning_info.items()))
      current_hash = hash(current_turning_info_str)

      if (
        current_hash != self.last_turning_info_hash
      ):  # if there is a change in turning info
        self.last_turning_info_hash = current_hash
        turning_info_path = self.repo_dir.joinpath("turning_info.yml")

        with open(turning_info_path, "wt") as f:
          for key, value in data.turning_info.items():
            traj, step = map(int, key.split(":"))
            turning_point = f"{self.name}:{traj}:{step}"
            turning_info_item = {
              turning_point: {
                "required": value["required"],
                "forbidden": value["forbidden"],
              }
            }
            f.write(
              yaml.safe_dump(
                turning_info_item,
                sort_keys=False,
                default_flow_style=False,
                width=float("inf"),
              )
            )
            f.write("\n")

        with self.branch_mutex:
          self.git("add", turning_info_path)
          self.git("commit", "-m", f"turning point: step {step} -- traj {traj}")

          if self.remote_url and self.push:
            self.push_to_remote()

  def post_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    """
    Update other_info.yml with termination_reason if the workflow was terminated.
    """
    if data.termination_reason:
      info_path = self.repo_dir.joinpath("other_info.yml")
      if info_path.exists():
        with open(info_path, "rt") as f:
          info = yaml.safe_load(f) or {}
      else:
        info = {}
      info["termination_reason"] = data.termination_reason

      with open(info_path, "wt") as f:
        yaml.safe_dump(info, f)

      with self.branch_mutex:
        self.git("add", info_path)
        self.git(
          "commit", "-m", f"termination reason: {data.termination_reason}"
        )
        if self.remote_url and self.push:
          self._async_push()


class MongoDBTelemetryHook(TelemetryHook):
  """
  MongoDBTelemetryHook is a hook that is used to record the data of the workflow and save it to a remote MongoDB database.

  Args:
    username (str): The username for the MongoDB database.
    password (str): The password for the MongoDB database.
    host (str): The host of the MongoDB database.
    port (int): The port of the MongoDB database.
    database (str): The name of the MongoDB database.
    collection (str): The name of the MongoDB collection.
    name (Optional[str]): The name of the session. If not provided, a timestamp in hex will be used.
  """

  def __init__(
    self,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    collection: str,
    name: Optional[str] = None,
  ):
    super().__init__()
    self.mongo_uri = f"mongodb://{username}:{password}@{host}:{port}"
    self.database = database
    self.collection = collection
    self.client = MongoClient(self.mongo_uri)
    self.handle = self.client[self.database][self.collection]
    self.result_id = None

    if name is None:
      # we use a timestamp in hex to represent the session name
      self.name = (
        f"session-{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
      )
    else:
      self.name = name

  def pre_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    # locate the target model
    model_by_arg = workflow.workflow_config.model

    if model_by_arg is None:
      model_config = GLOBAL_CONFIG.models
      model_list = [(config.name, config.priority) for config in model_config]
      model_list.sort(key=lambda x: x[1], reverse=True)
      model_name = model_list[0][0]
    else:
      model_name = model_by_arg
    full_system_prompt = workflow.workflow_config.system_prompt
    result = self.handle.insert_one(
      {
        "session_name": self.name,
        "model_name": model_name,
        "username": getpass.getuser(),
        "system_prompt": full_system_prompt,
        "chat_history": [],
      }
    )
    self.result_id = result.inserted_id

  def post_node_execute(self, data: ContextData, node: "BaseNode") -> None:
    # TODO: this could be optimized to only update the chat history produced by the current node
    # we just override the whole history for simplicity for now
    self.handle.update_one(
      {"_id": self.result_id},
      {
        "$set": {
          "chat_history": [message.to_dict() for message in data.history]
        }
      },
    )
