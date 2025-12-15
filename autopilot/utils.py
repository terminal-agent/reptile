import os
import random
import re
import shutil
import socket
import subprocess
from abc import ABC, ABCMeta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from rich.console import Console

console = Console()


def get_platform() -> str:
  import sys

  p_name = sys.platform
  for name in ("linux", "darwin", "win32"):
    if p_name.startswith(name):
      return name

  return p_name


def get_unused_port(host: str = "127.0.0.1") -> int:
  """
  Returns an unused port on the specified host (default is localhost).

  Args:
    host (str): the host to check for unused ports

  Returns:
    port (int): an unused port on the specified host
  """
  while True:
    # Generate a random port between 1024 and 65535 (the dynamic/private port range)
    port = random.randint(1024, 65535)

    # Try to bind a socket to the chosen port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      try:
        s.bind((host, port))  # Try binding to the random port
        return port  # If successful, this port is available
      except socket.error:
        continue  # If port is in use, try again with another port


@lru_cache(maxsize=32)
def extract_commands(content: str) -> List[Tuple[str, str]]:
  """
  Extracts the codes from all code blocks.

  Args:
    content (str): The content from which to extract code blocks.

  Returns:
    List[Tuple[str, str]]: A list of tuples where each tuple contains the
      command type (e.g., "bash", "python") and the command itself.
  """
  commands = re.findall(r"```(.*?)\n((?:[^\n]|\n(?!```))*)\n```", content)
  return [(cmd_type, cmd.strip(" \n\r\t")) for cmd_type, cmd in commands]


def execute_cmd(
  cmd: Union[str, List[str]],
  stdin: Optional[str] = None,
  env: Optional[Dict[str, str]] = None,
) -> str:
  """
  Executes a command and returns its output, raise error if the command fails.

  Args:
    cmd (Union[str, List[str]]):
      The command to execute. Can be a string or a list of strings.
      Sometimes list of strings is more convenient, e.g. no need to escape.
    stdin (str, optional):
      Input to send to the command's stdin. Defaults to None.
    env (dict, optional):
      Environment variables to set for the command. Defaults to None.

  Returns:
    stdout (str): the output of the command
  """
  if env is not None:
    env = dict(os.environ, **env)
  result = subprocess.run(
    cmd,
    shell=isinstance(cmd, str),
    input=stdin.encode() if stdin else None,
    capture_output=True,
    env=env,
    text=False,
  )
  if result.returncode != 0:
    raise RuntimeError(
      f"Failed to run {cmd}, \n"
      f"stdout: {result.stdout!r}\n"
      f"stderr: {result.stderr!r}\n"
      f"env: {env}\n"
    )
  stdout = result.stdout.decode("utf-8", errors="ignore")
  return stdout.strip()


def check_system_commands_exist() -> None:
  """
  Check if the system commands such as tmux and git exist. If not, raise an error.
  """
  missing_cmds = []
  for cmd in ["tmux", "git"]:
    if shutil.which(cmd) is None:
      missing_cmds.append(cmd)
  if missing_cmds:
    raise EnvironmentError(
      f"Missing system commands: {', '.join(missing_cmds)}. "
      "Please install them and ensure they are in your PATH."
    )


def safe_get(obj: Any, path: str, default: Any = None) -> Any:
  """
  Safely get a nested attribute from an object using dot notation.
  Example: safe_get(response, "choices.0.message.content")

  Args:
    obj (Any): The object to traverse.
    path (str): The dot-separated path to the attribute.
    default (Any, optional): The value to return if the attribute is missing or None. Defaults to None.

  Returns:
    Any: The value of the attribute or the default value.
  """
  for attr in path.split("."):
    if obj is None:
      return default
    # Handle list indices in path (e.g. "choices.0")
    if isinstance(obj, list) and attr.isdigit():
      try:
        obj = obj[int(attr)]
      except IndexError:
        return default
    else:
      obj = getattr(obj, attr, None)
  return obj if obj is not None else default


def ensure_list(val: Any) -> List[Any] | None:
  """
  Ensure that a value is a list. If it's None, return None.
  If it's a single value, wrap it in a list.

  Args:
    val (Any): The value to check.

  Returns:
    List[Any] | None: The value as a list or None.
  """
  if val is None:
    return None
  return val if isinstance(val, list) else [val]


class Singleton(type):
  """
  Singleton is a metaclass that ensures that only one instance of a class is created.

  Usage:
    class MyClass(metaclass=Singleton):
      pass
  """

  _instances: Dict[Type[Any], Any] = {}

  def __call__(cls, *args: Any, **kwargs: Any) -> Any:
    if cls not in cls._instances:
      cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
    return cls._instances[cls]


class SingletonABCMeta(ABCMeta):
  """
  SingletonABCMeta is a metaclass that ensures that only one instance of a class is created. It is a combination of ABCMeta and Singleton and is used for abstract classes.

  Usage:
    class MyClass(metaclass=SingletonABCMeta):
      pass
  """

  _instances: Dict[Type[Any], Any] = {}

  def __call__(cls, *args: Any, **kwargs: Any) -> Any:
    if cls not in cls._instances:
      cls._instances[cls] = super().__call__(*args, **kwargs)
    return cls._instances[cls]
