import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import docker

from autopilot.data import InteractionMode
from autopilot.evaluation.batch_progress import RunBatchProgressManager
from autopilot.evaluation.docker_utils import clean_images, list_images
from autopilot.utils import execute_cmd


class Task(ABC):
  def __init__(self, name: str, benchmark: str) -> None:
    self.name = name
    self.benchmark = benchmark
    self.session_name = (
      f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
    )
    self.max_steps = 500
    self.max_current_steps = 250
    self.time_out = 1800
    self.eval_time_out = 600
    self.cache_level = "env"
    self.interaction_mode: "InteractionMode" = InteractionMode.INTERACTIVE
    self.progress_manager: "RunBatchProgressManager | None" = None

    if self.benchmark in ["gsm8k", "locomo", "mmlu_pro"]:
      self.cache_level = "all"  # for the above benchmarks, they share the same docker image, no need to clean up

  @property
  @abstractmethod
  def compose_file(self) -> str:
    """Returns the path to the Docker Compose file for this task.

    Returns:
        str: Path to the docker-compose.yaml file.
    """
    pass

  @property
  @abstractmethod
  def container_name(self) -> str:
    """Returns the Docker container name for this task.

    Returns:
        str: Unique container name for the task instance.
    """
    pass

  @property
  @abstractmethod
  def description(self) -> str:
    """Returns the task description for the autopilot agent.

    Returns:
        str: Human-readable task instruction.
    """
    pass

  @property
  @abstractmethod
  def eval_script(self) -> str:
    """Returns the path to the evaluation script inside the container.

    Returns:
        str: Container path to the evaluation script.
    """
    pass

  @property
  @abstractmethod
  def envs(self) -> Dict[str, str]:
    """Returns environment variables for Docker operations.

    Returns:
        dict: Environment variables as key-value pairs.
    """
    pass

  @property
  @abstractmethod
  def files_to_copy(self) -> List[Tuple[str, str]]:
    """Returns list of files to copy into the container.

    Returns:
        list: List of (source_path, target_path) tuples.
    """
    pass

  @abstractmethod
  def generate_solution(self) -> Optional[str]:
    """Return solution.sh as an executable gold solution.

    Returns:
        str: Path to the solution.sh file. If not found, return None.
    """
    pass

  @abstractmethod
  def files_to_copy_to_host(self, host_dir: str) -> List[Tuple[str, str]]:
    """Returns list of files to copy from the container to the host.

    Returns:
        list: List of (container_path, host_path) tuples. If None, no files are copied to the host.
    """
    pass

  @classmethod
  def from_name(cls, name: str, benchmark: str) -> "Task":
    return cls(name, benchmark)

  def launch_container(self) -> None:
    # launch_container and copy files inside
    if self.progress_manager:
      self.progress_manager.update_instance_status(
        self.session_name, "Building Docker image..."
      )
    execute_cmd(
      [
        "docker",
        "compose",
        "-f",
        self.compose_file,
        "up",
        "--build",
        "--pull",
        "missing",
        "-d",
      ],
      env=self.envs,
    )
    for source, target in self.files_to_copy:
      dir = os.path.dirname(target)
      execute_cmd(["docker", "exec", self.container_name, "mkdir", "-p", dir])
      execute_cmd(["docker", "cp", source, f"{self.container_name}:{target}"])

  def copy_to_host(self, files_to_copy_to_host: List[Tuple[str, str]]) -> None:
    if not files_to_copy_to_host:
      return
    for container_path, host_path in files_to_copy_to_host:
      try:
        execute_cmd(
          ["docker", "cp", f"{self.container_name}:{container_path}", host_path]
        )
      except RuntimeError as e:
        pass

  def cleanup_resources(self) -> None:
    # ============================================================================
    # cleanup docker container
    # ============================================================================
    if self.progress_manager:
      self.progress_manager.update_instance_status(
        self.session_name, "Stopping container..."
      )
    # First try: graceful stop then remove
    try:
      execute_cmd(
        ["docker", "container", "stop", "--time", "10", self.container_name],
        env=self.envs,
      )
    except RuntimeError:
      pass  # Container might not exist or already stopped

    container_removed = False
    try:
      execute_cmd(
        ["docker", "container", "rm", "-v", self.container_name],
        env=self.envs,
      )
      container_removed = True
    except RuntimeError:
      pass  # Try kill then remove below

    if not container_removed:
      # Second try: kill then remove without -f
      try:
        execute_cmd(
          ["docker", "container", "kill", self.container_name],
          env=self.envs,
        )
        execute_cmd(
          ["docker", "container", "rm", "-v", self.container_name],
          env=self.envs,
        )
        container_removed = True
      except RuntimeError:
        pass  # Try force remove below

    if not container_removed:
      # Last try: force remove (may leave dangling resources) - try 3 times
      for attempt in range(3):
        try:
          execute_cmd(
            ["docker", "container", "rm", "-f", "-v", self.container_name],
            env=self.envs,
          )
          container_removed = True
          break
        except RuntimeError as e:
          if attempt == 2:
            print(
              f"Warning: Failed to force remove container {self.container_name} after 3 attempts: {e}"
            )

    # ============================================================================
    # cleanup docker images - based on cache level
    # ============================================================================
    if self.progress_manager:
      self.progress_manager.update_instance_status(
        self.session_name, "Cleaning images..."
      )
    try:
      docker_client = docker.from_env()
      clean_images(
        client=docker_client,
        prior_images=set(),  # Empty set means clean all relevant images
        cache_level=self.cache_level,
        clean=True,
      )
    except Exception as e:
      print(f"Warning: Failed to clean Docker images: {e}")
