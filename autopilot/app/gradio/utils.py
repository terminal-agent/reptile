import os
import signal
import sys
from pathlib import Path

from autopilot.cli.run import reload_prefix
from autopilot.config import GLOBAL_CONFIG
from autopilot.data import InteractionMode, WorkflowConfig
from autopilot.hooks import (
  GitHubTelemetryHook,
  GradioHook,
  InterruptHook,
  MongoDBTelemetryHook,
  ReloadHook,
)
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS
from autopilot.workflow.autopilot_workflow import AutopilotWorkflow


def launch_workflow(
  zmq_port: int,
  model: str,
  sandbox: str,
  max_steps: int,
  max_current_steps: int,
  max_time: int,
  name: str,
  task: str,
  log_to_mongodb: bool,
  log_to_github: bool,
  reload_session: str = "none",
  reload_trajectory: int = -1,
  reload_step: int = -1,
):
  workflow = AutopilotWorkflow(
    workflow_config=WorkflowConfig(
      interaction_mode=InteractionMode.INTERACTIVE_BY_ZMQ,
      model=model,
      sandbox=sandbox,
      zmq_host="localhost",
      zmq_port=zmq_port,
      max_steps=max_steps,
      max_current_steps=max_current_steps,
      time_out=max_time,
      system_prompt=SYSTEM_PROMPT.format(
        tools_description=TOOLS.get_tools_description()
      ),
    )
  )
  workflow.register_hook(GradioHook())

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

  workflow.register_hook(InterruptHook())

  if reload_session != "none" and reload_trajectory >= 0 and reload_step >= 0:
    workflow.register_hook(
      ReloadHook(
        prefix=reload_prefix(
          f"{reload_session}:{reload_trajectory}:{reload_step}"
        )
      )
    )

  # Handle graceful shutdown on SIGINT
  def _sigint_handler(signum, frame):
    print("shutting down workflow...")
    try:
      workflow.term.shutdown()
    except Exception as e:
      print(f"Error during graceful shutdown: {e}")
      sys.exit(1)

    sys.exit(0)

  # Reuse the handler for both SIGINT and SIGTERM
  # to catch the signal from both user input (Ctrl + C)
  # and SIGTERM via workflow_process.terminate()
  signal.signal(signal.SIGINT, _sigint_handler)
  signal.signal(signal.SIGTERM, _sigint_handler)

  workflow.run(instruction=task)
