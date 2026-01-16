import os
import re
import shlex
import sys
from pathlib import Path
from typing import Optional

import typer
from prettytable import PrettyTable
from typing_extensions import Annotated

from autopilot.config import GLOBAL_CONFIG
from autopilot.data import InteractionMode, WorkflowConfig
from autopilot.hooks import (
  GitHubTelemetryHook,
  InterruptHook,
  MongoDBTelemetryHook,
  RecycleHook,
  ReloadHook,
)
from autopilot.prompts import NAIVE_SYSTEM_PROMPT, SYSTEM_PROMPT
from autopilot.terminal import tmux
from autopilot.tools import TOOLS
from autopilot.utils import console, execute_cmd
from autopilot.workflow import (
  AutopilotWorkflow,
  EditorWorkflow,
  NaiveWorkflow,
  OracleWorkflow,
)

from .data import Session, initialize_repo, repo_path, sessions_path

# ================================
# Main Function
# ================================
PATTERN = r"autopilot_\d+"


def reload_prefix(reload: str) -> list[tuple[str, str]]:
  try:
    if reload.count(":") == 1:
      # format: <branch>:<step>
      branch, step_str = reload.split(":")
      traj_idx, step = -1, int(step_str)
    else:
      branch, traj_str, step_str = reload.split(":")
      traj_idx, step = int(traj_str), int(step_str)
  except Exception:
    console.print(
      f"Reloading {reload} failed, correct format is <branch>:<traj>:<step> or <branch>:<step>, "
      "where both <traj> and <step> are integers."
    )
    sys.exit(1)
  # if there is a folder named branch under sessions_path,
  # we find the history.yml file under it
  history_file = os.path.join(sessions_path, branch, "history.yml")
  if os.path.exists(history_file):
    console.log(f"Session {branch} found in {sessions_path}.")
  else:
    history_file = os.path.join(repo_path, branch, "history.yml")
    if os.path.exists(history_file):
      console.log(f"Session {branch} found in {repo_path}.")
    else:
      console.log("Syncing yaml_data repository ...")
      try:
        repo = initialize_repo(
          os.path.join(repo_path, branch), branch=branch
        )  # only clone the branch
      except Exception:
        console.print(f"Branch {branch} not found in the repository.")
        sys.exit(1)
  session = Session(history_file)
  if traj_idx >= 0:
    selected_traj = session.trajs[traj_idx][: step + 1]
  else:
    selected_traj = None
    for session_traj in session.trajs:
      if len(session_traj) >= step + 1:
        selected_traj = session_traj
        break

  if selected_traj is None:
    return []

  ### to be compatible with the data format, before and after refactoring
  ### old format: when only role is provided, we use the step["role"]
  ### new format: both role and name are provided, we use the step["name"]
  prefix = [
    (
      step_data["role"] if "name" not in step_data else step_data["name"],
      step_data["content"],
    )
    for step_data in selected_traj
  ]
  return prefix


def run_autopilot(
  terminal: Annotated[
    bool,
    typer.Option("-t", "--terminal/--no-terminal", help="Show the terminal"),
  ] = True,
  model: Annotated[
    Optional[str], typer.Option("-m", "--model", help="The model to use")
  ] = None,
  task: Annotated[
    Optional[str], typer.Option("--task", help="The task description")
  ] = None,
  sandbox: Annotated[
    Optional[str], typer.Option("-s", "--sandbox", help="The sandbox to use")
  ] = None,
  reload: Annotated[
    Optional[str],
    typer.Option(
      "-r",
      "--reload",
      help=(
        "Reload a history, format: <branch>:<traj>:<step> or <branch>:<step>."
        f"We first check under {sessions_path}, "
        "otherwise check the yaml_data repo."
      ),
    ),
  ] = None,
  name: Annotated[
    Optional[str],
    typer.Option("-n", "--name", help="The task session name to use"),
  ] = None,
  interaction: Annotated[
    str,
    typer.Option(
      "-i",
      "--interaction",
      help="The interaction mode to use, one of ('executive_only', 'interactive', 'naive', 'oracle')",
    ),
  ] = "interactive",
  editor: Annotated[
    Optional[str],
    typer.Option(
      "-e", "--editor", help="The LLM editor to supervise the LLM worker"
    ),
  ] = None,
  max_steps: Annotated[
    int,
    typer.Option(
      "--max-steps",
      help="The maximum number of steps in the current thread",
    ),
  ] = 500,
  max_current_steps: Annotated[
    int,
    typer.Option(
      "--max-current-steps",
      help="The maximum number of steps to run the autopilot",
    ),
  ] = 250,
  max_time: Annotated[
    int,
    typer.Option("--max-time", help="The maximum time to run the autopilot"),
  ] = 600,
  log_to_mongodb: Annotated[
    bool,
    typer.Option(
      "--log-to-mongodb/--no-log-to-mongodb",
      help="Control whether to push the data to telemetry",
    ),
  ] = False,
  log_to_github: Annotated[
    bool,
    typer.Option(
      "--log-to-github/--no-log-to-github",
      help="Control whether to push the data to github",
    ),
  ] = False,
  strong_scaffold: Annotated[
    bool,
    typer.Option(
      "--strong-scaffold/--no-strong-scaffold",
      help="Enable strong scaffold mode to control terminal node behavior",
    ),
  ] = False,
) -> None:
  """
  Start a new autopilot run.

  Args:
      terminal (Optional[bool]): Show the terminal tab in the tmux session to demonstrate the agent actions, optional.
      sandbox (Optional[str]): Run in sandbox mode, optional. If True, the run will be executed in a sandboxed environment.
      image (Optional[str]): The image to use, optional. If not provided, the default image will be used.
      model (Optional[str]): The model to use, optional. If not provided, the model with the highest priority will be used.
  """

  if terminal:
    # rerun in tmux
    cmd = [arg for arg in sys.argv if arg not in ("-t", "--terminal")] + [
      "--no-terminal"
    ]
    epilogue = (
      "tmux kill-session" if interaction == "executive_only" else "$SHELL"
    )
    cmd_str = shlex.join(cmd)

    # Collect context (AUTOPILOT_ env vars)
    env_context = {
      k: v for k, v in os.environ.items() if k.startswith("AUTOPILOT_")
    }

    tmux.new_pane(f"{cmd_str}; {epilogue}", env=env_context)
    tmux.attach()
    exit(0)

  workflow_config = WorkflowConfig(
    interaction_mode=InteractionMode(interaction),
    sandbox=sandbox,
    name=name,
    model=model,
    max_steps=max_steps,
    max_current_steps=max_current_steps,
    time_out=max_time,
    strong_scaffold=strong_scaffold,
    system_prompt=NAIVE_SYSTEM_PROMPT
    if interaction == "naive"
    else SYSTEM_PROMPT.format(tools_description=TOOLS.get_tools_description()),
  )

  workflow: AutopilotWorkflow | EditorWorkflow | OracleWorkflow | NaiveWorkflow
  if editor:
    workflow = EditorWorkflow(editor=editor, workflow_config=workflow_config)
  elif interaction == "oracle":
    workflow = OracleWorkflow(workflow_config=workflow_config)
  elif interaction == "naive":
    workflow = NaiveWorkflow(workflow_config=workflow_config)
  else:
    workflow = AutopilotWorkflow(workflow_config=workflow_config)

  workflow.register_hook(InterruptHook())
  workflow.register_hook(RecycleHook())

  if reload:
    workflow.register_hook(ReloadHook(prefix=reload_prefix(reload)))

  if GLOBAL_CONFIG.telemetry is None or GLOBAL_CONFIG.telemetry.github is None:
    raise ValueError("Telemetry or GitHub is not configured in the config file")

  workflow.register_hook(
    GitHubTelemetryHook(
      remote_url=GLOBAL_CONFIG.telemetry.github.repo_url,
      ssh_key_path=os.path.expanduser("~/.ssh/id_rsa"),
      name=name,
      push=log_to_github,
    )
  )

  if log_to_mongodb:
    if (
      GLOBAL_CONFIG.telemetry is None or GLOBAL_CONFIG.telemetry.mongodb is None
    ):
      raise ValueError(
        "Telemetry or MongoDB is not configured in the config file"
      )
    workflow.register_hook(
      MongoDBTelemetryHook(
        username=GLOBAL_CONFIG.telemetry.mongodb.username,
        password=GLOBAL_CONFIG.telemetry.mongodb.password,
        host=GLOBAL_CONFIG.telemetry.mongodb.host,
        port=GLOBAL_CONFIG.telemetry.mongodb.port,
        database=GLOBAL_CONFIG.telemetry.mongodb.database,
        collection=GLOBAL_CONFIG.telemetry.mongodb.collection,
        name=name,
      )
    )

  workflow.run(instruction=task)


def list_runs(
  head: Annotated[
    Optional[int], typer.Option("-n", "--head", help="Show the head n runs")
  ] = None,
) -> None:
  """
  List the existing autopilot runs.

  Args:
      head (Optional[int]): Show the head n runs, optional.
  """
  existing_sessions = execute_cmd("tmux ls")
  table = PrettyTable()
  table.field_names = ["ID", "Name", "Creation time"]
  for line in existing_sessions.split("\n"):
    if re.match(PATTERN, line):
      session_name = line.split(":")[0].strip()
      session_id = session_name.split("_")[-1]
      creation_time = line.split("(")[1].split(")")[0].lstrip("created")
      table.add_row([session_id, session_name, creation_time])
  print(table)


def kill_runs(
  run_id: Annotated[
    Optional[str], typer.Option("-i", "--id", help="The id of the run to kill")
  ] = None,
  all: Annotated[
    bool, typer.Option("-a", "--all", help="Kill all runs")
  ] = False,
) -> None:
  """
  Kill the existing autopilot runs.

  Args:
      all (Optional[bool]): Kill all runs if True, optional.
  """
  assert not (run_id and all), "Cannot specify both run_id and all"
  if run_id:
    execute_cmd(f"tmux kill-session -t autopilot_{run_id}")
  elif all:
    existing_sessions = execute_cmd("tmux ls")
    for line in existing_sessions.split("\n"):
      if re.match(PATTERN, line):
        session_name = line.split(":")[0]
        execute_cmd(f"tmux kill-session -t {session_name}")
