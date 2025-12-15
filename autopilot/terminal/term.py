import os
import re
import select
import sys
import termios
import time
from threading import Event
from typing import List, Optional
from uuid import uuid4

from autopilot.utils import console, execute_cmd

from ._utils import build_tools_wheel, cp_to_container, install_binaries

if sys.platform not in ["linux", "darwin"]:
  raise RuntimeError("Autopilot is only supported on Linux and macOS.")


class TermInterrupted(Exception):
  """
  TermInterrupted is an exception raised when the terminal is interrupted by the user.
  """

  pass


def trim_trailing_space(text: str) -> str:
  """
  Remove the trailing spaces from the text.

  Args:
    text (str): the text to trim

  Returns:
    text (str): the text with trailing spaces removed
  """
  # trim all trailing spaces
  lines = text.splitlines()
  return "\n".join([line.rstrip() for line in lines])


class Term(object):
  """
  Term is a base class for terminal abstraction.

  Args:
    event (Event): the event to signal the terminal to interrupt
    sandbox (Optional[str]): the sandbox to use for the terminal
  """

  def __init__(self, event: Event, sandbox: Optional[str] = None):
    self.window_id = self._new_window()
    self.event = event
    self.sandbox = sandbox
    # 0. before we can use self.wait, we need to ensure cmds like ps exists.
    if sandbox:
      install_binaries(sandbox)  # install binaries in the sandbox
      self.python_bin = self._ensure_python()
    # 1. get the tty path
    self._get_tty()
    # 2. ensure tools are in the PATH
    self._ensure_tools()
    # clear everything
    self.send_key("C-l")
    self.clear_history()
    self._old_text = ""
    self.tui_timeout = False
    self.terminal_timeout = False

  def _run_cmd(self, cmd: List[str]) -> str:
    """
    Run a command in the terminal.

    Args:
      cmd (List[str]): the command to run

    Returns:
      output (str): the output of the command
    """
    if self.sandbox:
      retry = 0
      cmd_output = ""
      while retry < 3:
        try:
          retry += 1
          cmd_output = execute_cmd(["docker", "exec", self.sandbox, *cmd])
          break
        except:
          console.log("docker exec failed, retrying in 1 second")
          time.sleep(1)
          continue
      return cmd_output
    else:
      return execute_cmd(cmd)  # type: ignore[no-any-return]

  def _get_tty(self) -> None:
    """
    Get the tty path of the terminal.
    """
    tty_id = str(uuid4())
    self._run_cmd(["mkfifo", f"/tmp/{tty_id}.tty"])
    if self.sandbox:
      self.send_text(
        f"docker exec -it --detach-keys='ctrl-]' {self.sandbox} "
        f"bash -c 'tty > /tmp/{tty_id}.tty; exec $SHELL'",
        paste=False,
        enter=True,
      )
    else:
      self.send_text(f"tty > /tmp/{tty_id}.tty", paste=False, enter=True)
    tty = self._run_cmd(["cat", f"/tmp/{tty_id}.tty"])
    self.tty = tty.strip(" \r\n\t")
    if not self.sandbox:
      self.tty_fd = os.open(self.tty, os.O_RDONLY | os.O_NOCTTY)
    self.wait()

  def _ensure_python(self) -> str:
    """
    Ensure the Python environment is set up.
    """
    self._run_cmd(["uv", "venv", "-p", "python311", "/tmp/tools"])
    return "/tmp/tools/bin/python3"

  def _ensure_tools(self) -> None:
    """
    Ensure the tools are in the PATH.
    """
    if not self.sandbox:
      path = os.path.dirname(sys.executable)
      self.send_text(f"export PATH={path}:$PATH", paste=False, enter=True)
      self.wait()
    else:
      src = build_tools_wheel()
      dst = f"/tmp/{os.path.basename(src)}"
      cp_to_container(self.sandbox, src, dst)
      self.send_text(
        "source /tmp/tools/bin/activate\n"
        f"uv pip install {dst}\n"
        "deactivate\n"
        "export PATH=$PATH:/tmp/tools/bin",
        paste=False,
        enter=True,
      )
      self.wait()

  @property
  def is_canonical(self) -> bool:
    """
    Check if the terminal is in canonical mode.
    """
    if self.sandbox:
      command_out = self._run_cmd(
        [
          self.python_bin,
          "-c",
          (
            "import termios, os; "
            f"fd = os.open('{self.tty}', os.O_RDONLY | os.O_NOCTTY); "
            "print(termios.tcgetattr(fd)[3] & termios.ICANON)"
          ),
        ]
      )
      canon = int(command_out)
    else:
      canon = termios.tcgetattr(self.tty_fd)[3] & termios.ICANON
    if canon:
      return True
    else:
      return False

  @property
  def is_wait_woken(self) -> bool:
    """
    Check if the terminal is waiting for a woken event.
    """
    cmd = ["ps", "H", "-t", self.tty, "-o", "stat=,wchan="]
    out = self._run_cmd(cmd)
    for line in out.splitlines():
      stat, wchan = re.split(r"\s+", line)
      if "+" in stat:
        if wchan == "wait_woken":
          return True
    return False

  @property
  def match_heuristic_words(self) -> bool:
    """
    Check if the terminal matches the heuristic words.
    """
    heuristics = {
      r"[Yy](?:es)?(?:\/| or )[Nn](?:o)?",
      r"[Pp]assword",
    }
    text = self.get_text()
    last_line = text.rsplit("\n", 1)[-1]
    for h in heuristics:
      if re.search(h, last_line):
        console.log(f"last line: {last_line}")
        return True
    return False

  def clear_history(self) -> None:
    """
    Clear the history of the terminal.
    """
    raise NotImplementedError

  def sleep(self, dur: float = 1) -> None:
    """
    Sleep for the given duration.

    Args:
      dur (float): the duration to sleep
    """
    if self.event.wait(dur):
      self.send_key("control+c")
      raise TermInterrupted("Term interrupted, pass control to user")

  @property
  def tty_is_empty(self) -> bool:
    """
    Check if the tty is empty.
    """
    if self.sandbox:
      len_stdin = self._run_cmd(
        [
          self.python_bin,
          "-c",
          (
            "import select, os;"
            f"fd = os.open('{self.tty}', os.O_RDONLY | os.O_NOCTTY);"
            "stdin, _, _ = select.select([fd], [], [], 0); print(len(stdin))"
          ),
        ]
      )
      return int(len_stdin) == 0
    stdin, _, _ = select.select([self.tty_fd], [], [], 0)
    return len(stdin) == 0

  def _wait_for_stdin(self, tick: float, timeout: int) -> bool:
    """
    Wait for the stdin to be empty.

    Args:
      tick (float): the duration to sleep
      timeout (int): the timeout to wait

    Returns:
      bool: True if the timeout is reached, False otherwise
    """
    self._wait_for_no_new_output()
    waited = 0.0
    if self.tty_is_empty:
      self.send_key("enter")
    # then we start waiting for the stdin to be empty again
    with console.status("[bold green]Waiting for terminal ...") as status:
      while True:
        self.sleep(tick)
        waited += tick
        if self.tty_is_empty:
          break
        elif waited > timeout:
          break
        else:
          status.update("[bold green]Terminal busy ...")
    if waited > timeout:
      console.log(
        "Terminal timeout: waiting for terminal after {waited} seconds"
      )
      return True
    else:
      console.log("Terminal is ready for interaction")
      return False

  def _wait_for_stdin_linux(self, tick: float, timeout: int) -> bool:
    """
    Wait for the stdin to be empty on Linux.

    Args:
      tick (float): the duration to sleep
      timeout (int): the timeout to wait

    Returns:
      bool: True if the timeout is reached, False otherwise
    """
    noncanon = 0
    wait_woken = 0
    no_new_output = 0
    prev_screen = self.get_screen()
    waited = 0.0
    with console.status("[bold green]Waiting for terminal ..."):
      while True:
        noncanon = (noncanon + 1) if not self.is_canonical else 0
        wait_woken = (wait_woken + 1) if self.is_wait_woken else 0
        screen = self.get_screen()
        if screen == prev_screen:
          no_new_output += 1
        else:
          no_new_output = 0
        prev_screen = screen
        if no_new_output >= 3:
          if noncanon >= 3:
            console.log("non-canonical mode")
            break
          elif wait_woken >= 3 and no_new_output >= 3:
            console.log("wait_woken detected")
            break
          elif self.match_heuristic_words:
            console.log("keyword match found")
            break
          elif waited > timeout:
            console.log(
              f"Terminal timeout: waiting for terminal after {waited} seconds"
            )
            break
        self.sleep(tick)
        waited += tick
    if waited > timeout:
      return True
    else:
      return False

  def _wait_for_no_new_output(self, tick: float = 1) -> None:
    """
    Wait for the terminal to have no new output.

    Args:
      tick (float): the duration to sleep

    Returns:
      None
    """
    prev_screen = self.get_screen()
    waited = 0.0
    with console.status("[bold green]Waiting for terminal ...") as status:
      while True:
        self.sleep(tick)
        waited += tick
        screen = self.get_screen()
        if screen == prev_screen:
          break
        else:
          status.update("[bold green]Terminal busy ...")
        prev_screen = screen
    console.log("Terminal has no new updates")

  def _wait_for_alternate_off(self, tick: int = 1, timeout: int = 5) -> None:
    """
    Wait for the alternate to be off.

    Args:
      tick (float): the duration to sleep
      timeout (int): the timeout to wait before sending quit command

    Returns:
      None
    """
    waited = 0
    with console.status("[bold green]Waiting for user to quit TUI"):
      while True:
        self.sleep(tick)
        waited += tick
        if not self.alternate_on:
          break
        elif waited > timeout:
          console.log(f"Timeout waiting for TUI to exit, sending quit command")
          self.tui_timeout = True
          # Try common quit commands for different TUI programs
          self.send_key("q")  # quit vim, less, etc.
          time.sleep(0.5)  # wait a bit for the command to take effect
          if self.alternate_on:
            # If still in alternate mode, try escape
            self.send_key("escape")
            time.sleep(0.5)
            if self.alternate_on:
              # Last resort: force quit with Ctrl+C
              self.send_key("control+c")
              break

  def _interrupt_stuck_command(self) -> None:
    """
    Try to interrupt a stuck command by sending quit/interrupt keys.

    Returns:
      None
    """
    console.log(
      "Terminal timeout: waiting for command, sending interrupt commands"
    )
    # Try common interrupt commands
    self.send_key("q")  # quit vim, less, etc.
    time.sleep(0.5)  # wait a bit for the command to take effect

    # If still stuck, try escape
    self.send_key("escape")
    time.sleep(0.5)

    # Last resort: force quit with Ctrl+C
    self.send_key("control+c")

  def wait(self, tick: float = 0.5, timeout: int = 30) -> bool:
    """
    Wait for the terminal to be ready for interaction.

    Args:
      tick (float): the duration to sleep
      timeout (int): the timeout to wait

    Returns:
      bool: True if the timeout is reached, False otherwise
    """
    # Reset timeout flags at the beginning of each wait
    self.tui_timeout = False
    self.terminal_timeout = False
    if self.alternate_on:
      self._wait_for_alternate_off()
      return False  # not timeout
    # we suppose it is linux running in the sandbox
    if self.sandbox or sys.platform == "linux":
      result = self._wait_for_stdin_linux(tick=tick, timeout=timeout)
      if result:
        self.terminal_timeout = True
        # Try to interrupt the stuck command
        self._interrupt_stuck_command()
      return result
    else:
      result = self._wait_for_stdin(tick=tick, timeout=timeout)
      if result:
        self.terminal_timeout = True
        # Try to interrupt the stuck command
        self._interrupt_stuck_command()
      return result

  def get_screen(self) -> str:
    """
    Get the screen text of the terminal.

    Returns:
      text (str): the screen text of the terminal
    """
    return trim_trailing_space(self._get_text(extent="screen"))  # type: ignore[no-any-return]

  def get_text(self) -> str:
    """
    Get the text of the terminal.
    """
    return trim_trailing_space(self._get_text(extent="all"))  # type: ignore[no-any-return]

  @property
  def foreground_pid(self) -> int:
    """
    Get the ID of the foreground process.

    Returns:
      pid (int): the ID of the foreground process
    """
    output = self._run_cmd(["ps", "-o", "stat=,pid=", "-t", self.tty])
    for line in output.splitlines():
      stat, pid = re.split(r"\s+", line)
      if "+" in stat:
        break
    return int(pid)

  @property
  def alternate_on(self):
    """
    Check if the alternate is on.

    Returns:
      bool: True if the alternate is on, False otherwise
    """
    raise NotImplementedError

  def send_text(self, text: str, paste: bool, enter: bool = False) -> None:
    """
    Send text to the terminal.

    Args:
      text (str): the text to send
      paste (bool): whether to paste the text
      enter (bool): whether to enter the text
    """
    raise NotImplementedError

  def send_key(self, key: str) -> None:
    """
    Send a key to the terminal.

    Args:
      key (str): the key to send
    """
    raise NotImplementedError

  def _get_text(self, extent="all") -> str:
    """
    Get the text of the terminal.

    Args:
      extent (str): the extent of the text to get

    Returns:
      text (str): the text of the terminal
    """
    raise NotImplementedError

  def save_old_text(self) -> None:
    """
    Save the old text of the terminal.
    """
    self.clear_history()
    self._old_text = self.get_text()

  def get_new_text(self) -> str:
    """
    Get the new text of the terminal.

    Returns:
      new_text (str): the new text of the terminal
    """
    new_text = self.get_text()[len(self._old_text) :]
    self.save_old_text()
    return new_text

  @classmethod
  def _new_window(cls) -> int:
    """
    Create a new window.

    Returns:
      window_id (int): the ID of the new window
    """
    raise NotImplementedError

  def _enable_input(self) -> None:
    """
    Enable the input of the terminal.
    """
    raise NotImplementedError

  def _disable_input(self) -> None:
    """
    Disable the input of the terminal.
    """
    raise NotImplementedError

  def enable_input(self) -> None:
    """
    Enable the input of the terminal.
    """
    self._enable_input()

  def disable_input(self) -> None:
    """
    Disable the input of the terminal.
    """
    self._disable_input()
    self.clear_history()
    self._old_text = self.get_text()

  def shutdown(self) -> None:
    """
    Shutdown the terminal.
    """
    raise NotImplementedError
