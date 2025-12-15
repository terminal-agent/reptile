from __future__ import annotations

from typing import TYPE_CHECKING

from autopilot.data import ContextData

if TYPE_CHECKING:
  from autopilot.data import ContextData
  from autopilot.node.base import BaseNode
  from autopilot.workflow.base import BaseWorkflow

import os
import time

from autopilot.constants import _CACHE_ROOT
from autopilot.utils import execute_cmd

from .base_hook import BaseHook

__all__ = ["CheckpointingHook"]


class CheckpointingHook(BaseHook):
  """
  CheckpointingHook is a hook that is used to checkpoint the workflow.
  """

  def __init__(self):
    super().__init__()
    # we use a timestamp in hex to represent the session name
    self.name = (
      f"checkpoint-{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
    )
    self.workspace = _CACHE_ROOT
    self.ckpt_dir = self.workspace.joinpath("checkpoints", self.name)

  def _init_repo(self) -> None:
    """
    Create a mirrow git repo for checkpointing.
    """
    self.ckpt_dir.mkdir(parents=True, exist_ok=True)
    self.git("init")
    self.commit()

  def git(self, *command: str) -> str:
    """
    Execute a git command with the given arguments.

    Args:
        *command: Variable length git command arguments (e.g., "add", ".", or "commit", "-m", "message").

    Returns:
        The output of the git command.
    """
    # TODO (FrankLeeeee): create a GitMixin class to handle the common git logic
    cmd = ["git", "-C", str(self.ckpt_dir), *command]
    env = {"GIT_DIR": str(self.ckpt_dir), "GIT_WORK_TREE": os.getcwd()}
    return execute_cmd(cmd, env=env)

  def commit(self) -> None:
    """
    Commit the changes to the git repo.
    """
    # if there is anything to commit
    git_status = self.git("status", "--porcelain")

    if git_status:
      total_size = 0
      for line in git_status.split("\n"):
        path = line.split()[1]
        total_size += self._get_size(path)

      total_size_mb = total_size / (1024 * 1024)
      while True:
        response = input(
          f"The checkpointing size is {total_size_mb:.2f} MB, do you still want to enable checkpointing? [Y/N]  "
        ).upper()
        if response == "Y":
          break
        elif response == "N":
          self.disable()
          print("Disabling checkpointing for this session")
          return
        else:
          continue

      self.git("add", ".")
      self.git("commit", "-m", "checkpoint")

  def _get_size(self, path: str) -> int:
    """
    Get the total size (in bytes) of a file or directory.

    Args:
        path (str): The path to the file or directory.

    Returns:
        The total size of the file or directory in bytes.
    """
    if os.path.isfile(path):
      return os.path.getsize(path)
    elif os.path.isdir(path):
      total_size = 0
      for dirpath, _, filenames in os.walk(path):
        for f in filenames:
          fp = os.path.join(dirpath, f)
          if os.path.isfile(fp):  # avoid broken symlinks
            total_size += os.path.getsize(fp)
      return total_size
    else:
      raise ValueError(f"{path} is neither a file nor a directory")

  def pre_run_execute(self, data: ContextData, workflow: BaseWorkflow) -> None:
    # create a mirror git repo for checkpointing
    self._init_repo()

  def post_node_execute(self, data: ContextData, node: "BaseNode") -> None:
    # commit the changes after each node execution
    self.commit()
