import os
import shlex
import time
import uuid
from typing import List, Optional, Tuple, Union

from autopilot.config import GLOBAL_CONFIG
from autopilot.utils import execute_cmd

from .term import Term

_session = None
_in_isolated_mode = False
# If running in a tmux session, check if we should reuse it
# Only reuse if it's an autopilot session (session name starts with "autopilot_")
# Otherwise, we're in a parent tmux and should create an isolated session to avoid joining panes
if os.environ.get("TMUX", None):
  current_session = execute_cmd(
    "tmux display-message -p '#{session_name}'"
  ).strip(" \n\r\t")
  if current_session.startswith("autopilot_"):
    _session = current_session
  else:
    _in_isolated_mode = True


def attach():
  """
  Attach to the tmux session via global session ID _session.
  """
  if _session is None:
    raise RuntimeError("attach is called before any tmux session is created.")
  os.system(f"tmux attach -t {_session}")


def break_pane(pane_id: str) -> None:
  """
  Break the pane.

  Args:
    pane_id (str): the ID of the pane to break
  """
  execute_cmd(f"tmux break-pane -s {pane_id}")


def kill_pane(pane_id: str) -> None:
  """
  Kill the pane.

  Args:
    pane_id (str): the ID of the pane to kill
  """
  execute_cmd(f"tmux kill-pane -t {pane_id}")


def kill_session(session_name: str) -> None:
  """
  Kill the session.

  Args:
    session_name (str): the name of the session to kill
  """
  execute_cmd(f"tmux kill-session -t {session_name}")


def select_pane(pane_id: str) -> None:
  """
  Select the pane.

  Args:
    pane_id (str): the ID of the pane to select
  """
  execute_cmd(f"tmux select-pane -t {pane_id}")


def join_pane(left: str, right: str) -> None:
  """
  Join the pane.

  Args:
    left (str): the ID of the left pane
    right (str): the ID of the right pane
  """
  try:
    break_pane(right)
  except Exception:
    # if the right pane is already broken, we can ignore the error
    pass
  execute_cmd(f"tmux join-pane -h -s {left} -t {right} -b")


def paste_to_pane(pane_id: str, text: str) -> None:
  """
  Paste the text to the pane.

  Args:
    pane_id (int): the ID of the pane to paste to
    text (str): the text to paste
  """
  execute_cmd(
    ["tmux", "load-buffer", "-b", f"buffer{pane_id}", "-"],
    stdin=text,
  )
  execute_cmd(
    [
      "tmux",
      "paste-buffer",
      "-b",
      f"buffer{pane_id}",
      "-p",
      "-t",
      f"%{pane_id}",
    ]
  )


def new_pane(
  cmd: Optional[Union[str, List[str], Tuple[str]]] = None,
  env: Optional[dict[str, str]] = None,
) -> str:
  """
  Create a global tmux session for current process if it doesn't exist.

  Args:
    cmd (Optional[Union[str, List[str], Tuple[str]]]): the command to run in the pane
    env (Optional[dict[str, str]]): the environment variables to set in the pane

  Returns:
    pane_id (str): the ID of the new pane
  """
  pwd = os.getcwd()
  if cmd is None:
    cmd = []
  elif isinstance(cmd, str):
    cmd = [cmd]
  elif not isinstance(cmd, (list, tuple)):
    raise ValueError("cmd must be a string, list or tuple")

  if env:
    env_vars = [f"{k}={shlex.quote(v)}" for k, v in env.items()]
    cmd = env_vars + list(cmd)

  global _session
  # If we have a session, reuse existing session
  if _session is not None:
    pane_id = execute_cmd(
      [
        "tmux",
        "new-window",
        "-t",
        f"{_session}:",
        "-c",
        pwd,
        "-P",
        "-F",
        "#{pane_id}",
      ]
    )
    if cmd:
      paste_to_pane(pane_id.replace("%", ""), " ".join(cmd))
      execute_cmd(["tmux", "send-keys", "-t", pane_id, "enter"])
    return str(pane_id)

  # Create a new isolated session (increment the session name to avoid conflict)
  _session = f"autopilot_{os.getpid()}_{uuid.uuid4().hex[:8]}"
  pane_id = execute_cmd(
    [
      "tmux",
      "new-session",
      "-d",
      "-s",
      _session,
      "-c",
      pwd,
      "-P",
      "-F",
      "#{pane_id}",
    ]
  )
  if cmd:
    paste_to_pane(pane_id.replace("%", ""), " ".join(cmd))
    execute_cmd(["tmux", "send-keys", "-t", pane_id, "enter"])

  # wait until tmux is up
  while True:
    try:
      execute_cmd(["tmux", "has-session"])
      break
    except Exception:
      time.sleep(1)
      continue

  return str(pane_id)


class Tmux(Term):
  @classmethod
  def _new_window(cls):
    # default to a plain bashrc file
    rcfile = os.path.dirname(os.path.abspath(__file__)) + "/default_bashrc"
    rcfile = os.path.abspath(rcfile)
    pane_id = new_pane(
      ["bash", "--rcfile", rcfile]
      if GLOBAL_CONFIG.session.use_default_bashrc
      else []
    )
    # Only join to parent tmux pane if we're not in isolated mode
    # In isolated mode (running in parent tmux), don't join panes to maintain isolation
    autopilot_pane_id = os.environ.get("TMUX_PANE", None)
    if autopilot_pane_id is not None and not _in_isolated_mode:
      join_pane(pane_id, autopilot_pane_id)
      select_pane(autopilot_pane_id)
    return int(pane_id.replace("%", ""))

  @staticmethod
  def clear() -> None:
    execute_cmd("tmux clear-history")

  @property
  def pane_id(self) -> int:
    return int(self.window_id)

  def clear_history(self) -> None:
    execute_cmd(f"tmux clear-history -t %{self.pane_id}")

  def send_text(
    self, text: str, paste: bool = True, enter: bool = False
  ) -> None:
    if text == "":
      return
    if paste:
      paste_to_pane(str(self.pane_id), text)
    else:
      execute_cmd(["tmux", "send-keys", "-t", f"%{self.pane_id}", "-l", text])
    if enter:
      execute_cmd(["tmux", "send-keys", "-t", f"%{self.pane_id}", "enter"])
    elif not self.is_canonical:  # send C-L to force a refresh
      execute_cmd(["tmux", "send-keys", "-t", f"%{self.pane_id}", "C-L"])

  def send_key(self, key: str) -> None:
    key = key.lower()
    key = key.replace("ctrl+", "C-")
    key = key.replace("control+", "C-")
    key = key.replace("shift+", "S-")
    key = key.replace("alt+", "M-")
    key = key.replace("meta+", "M-")
    execute_cmd(
      [
        "tmux",
        "send-keys",
        "-t",
        f"%{self.pane_id}",
        key,
      ],
    )
    # make sure the key is sent
    time.sleep(0.2)

  @property
  def alternate_on(self):
    a = execute_cmd(
      [
        "tmux",
        "display-message",
        "-t",
        f"%{self.pane_id}",
        "-p",
        "#{alternate_on}",
      ]
    )
    return bool(int(a))

  def _get_text(self, extent: str = "all") -> str:
    Sdict = {"all": "-", "screen": "0"}
    text = execute_cmd(
      [
        "tmux",
        "capture-pane",
        "-J",
        "-t",
        f"%{self.pane_id}",
        "-p",
        "-S",
        Sdict[extent],
      ]
    )
    text = text.rstrip(" \t\r\n")
    return str(text)

  def _enable_input(self) -> None:
    execute_cmd(f"tmux select-pane -t %{self.pane_id} -e")

  def _disable_input(self) -> None:
    execute_cmd(f"tmux select-pane -t %{self.pane_id} -d")

  def shutdown(self) -> None:
    global _session
    if _session is not None:
      kill_session(_session)
    _session = None
