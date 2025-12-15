import signal
import time

import psutil

from autopilot.utils import console


def on_terminate(proc):
  console.print(
    f"[green]process {proc.pid} terminated with exit code {proc.returncode}[/green]"
  )


def send_sigint_to_autopilot_processes():
  """Send SIGINT signal to all running autopilot child processes.

  This will trigger the SIGINT handler in BaseWorkflow which sets the event,
  allowing graceful shutdown of the workflow.
  """
  current_process = psutil.Process()
  autopilot_children = [
    c
    for c in current_process.children(recursive=True)
    if c.name() == "autopilot"
  ]

  sigint_session_names = []
  for child in autopilot_children:
    session_name = "unknown"
    try:
      cmdline = child.cmdline()
      for i, token in enumerate(cmdline):
        if token == "--name" and i + 1 < len(cmdline):
          session_name = cmdline[i + 1]
          break
      child.send_signal(signal.SIGINT)
      console.print(
        f"[green]Sending SIGINT to autopilot process {child.pid} (session: {session_name})[/green]"
      )
    except psutil.NoSuchProcess:
      console.print(
        f"[red]Autopilot process {child.pid} (session: {session_name}) already terminated[/red]"
      )
    except Exception as e:
      console.print(
        f"[red]Failed to send SIGINT to process {child.pid}: {e}[/red]"
      )
    finally:
      sigint_session_names.append(session_name)

  return sigint_session_names


def cleanup_zombie_processes(timeout=10):
  console.print(
    f"Cleaning up zombie autopilot processes\n"
    f"Wait {timeout} seconds for autopilot child processes to get called"
  )
  # Sleep for timeout seconds for child processes to be called
  time.sleep(timeout)

  current_process = psutil.Process()
  autopilot_children = [
    c
    for c in current_process.children(recursive=True)
    if c.name() == "autopilot"
  ]

  # Terminate child evaluation processes
  for child in autopilot_children:
    session_name = "unknown"
    try:
      # cmdline may raise NoSuchProcess if process already terminated
      cmdline = child.cmdline()
      for i, token in enumerate(cmdline):
        if token == "--name" and i + 1 < len(cmdline):
          session_name = cmdline[i + 1]
          break
      child.terminate()
      console.print(
        f"[green]Early stopping triggered: Terminating child evaluation process {child.pid} {child.name()} (session: {session_name})[/green]"
      )
    except psutil.NoSuchProcess:
      console.print(
        f"[red]Child evaluation process {child.pid} {child.name()} (session: {session_name}) already terminated[/red]"
      )

  _, alive = psutil.wait_procs(
    autopilot_children, timeout=timeout, callback=on_terminate
  )
  for p in alive:
    session_name = "unknown"
    try:
      # cmdline may raise NoSuchProcess if process already terminated
      cmdline = p.cmdline()
      for i, token in enumerate(cmdline):
        if token == "--name" and i + 1 < len(cmdline):
          session_name = cmdline[i + 1]
          break
      console.print(
        f"[green]process {p.pid} ({p.cmdline()}) did not terminate in time. Killing...[/green]"
      )
      p.kill()
    except psutil.NoSuchProcess:
      console.print(
        f"[red]Child evaluation process {p.pid} {p.name()} (session: {session_name}) already terminated[/red]"
      )

  return
