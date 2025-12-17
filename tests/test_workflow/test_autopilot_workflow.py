import argparse
import os
import time

import pytest

from autopilot.data import InteractionMode, WorkflowConfig
from autopilot.hooks import CheckpointingHook, GitHubTelemetryHook
from autopilot.workflow import AutopilotWorkflow


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--checkpoint", action="store_true")
  parser.add_argument("--interaction-mode", type=str, default="interactive")
  parser.add_argument("--telemetry", action="store_true")
  return parser.parse_args()


@pytest.mark.skip(reason="This is an interactive test")
def test_autopilot_workflow(
  interaction_mode: str, checkpoint: bool = False, telemetry: bool = False
):
  workflow = AutopilotWorkflow(
    workflow_config=WorkflowConfig(
      interaction_mode=InteractionMode(interaction_mode)
    )
  )

  if checkpoint:
    workflow.register_hook(CheckpointingHook())

  if telemetry:
    workflow.register_hook(
      GitHubTelemetryHook(
        name=f"autopilot-refactoring-{time.time()}",
        remote_url="git@github.com:Sailor-Agents/yaml_data.git",
        ssh_key_path=os.path.expanduser("~/.ssh/id_rsa"),
      )
    )
  workflow.run()


if __name__ == "__main__":
  args = parse_args()
  test_autopilot_workflow(
    args.interaction_mode, args.checkpoint, args.telemetry
  )
