#!/usr/bin/env python3
"""
Test script to verify timeout functionality in interrupt_hook.
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from threading import Event

from autopilot.data import ContextData, InteractionMode, WorkflowConfig
from autopilot.hooks.interrupt_hook import InterruptHook
from autopilot.node.base import BaseNode, Role
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS


class MockWorkflow:
  """Mock workflow for testing"""

  def __init__(self, timeout_limit=3):
    self.event = Event()
    self.console = MockConsole()
    self.workflow_config = WorkflowConfig(
      interaction_mode=InteractionMode.INTERACTIVE,
      system_prompt=SYSTEM_PROMPT.format(
        tools_description=TOOLS.get_tools_description()
      ),
      time_out=timeout_limit,
      max_steps=10,
    )


class MockConsole:
  """Mock console for testing"""

  def print(self, message):
    print(f"Console: {message}")


class MockNode(BaseNode):
  """Mock node for testing"""

  def __init__(self):
    super().__init__(
      name="mock_node",
      role=Role.LLM,
      terminal=None,
      workflow_config=WorkflowConfig(
        interaction_mode=InteractionMode.INTERACTIVE,
        system_prompt=SYSTEM_PROMPT.format(
          tools_description=TOOLS.get_tools_description()
        ),
      ),
    )

  def set_output_nodes(self, *args, **kwargs):
    pass

  def run(self, data, extra_info=None):
    return None, None


def test_timeout_exceeded():
  """Test that timeout limit is properly enforced by interrupt_hook"""
  print("Testing timeout functionality...")

  # Create test data with short timeout
  data = ContextData()
  timeout_limit = 3  # 3 second timeout for stable testing
  hook = InterruptHook()
  mock_workflow = MockWorkflow(timeout_limit=timeout_limit)

  # Call pre_run_execute to start the timeout monitor
  hook.pre_run_execute(data, mock_workflow)

  # Wait for timeout to be triggered
  time.sleep(timeout_limit + 0.5)  # Wait a bit longer than timeout

  # Verify the hook handled the timeout
  assert mock_workflow.event.is_set(), (
    "Event should be set when timeout is exceeded"
  )
  assert data.termination_reason == f"Timeout {timeout_limit}s reached", (
    f"Expected 'Timeout {timeout_limit}s reached', got '{data.termination_reason}'"
  )

  print("✅ Test passed! Timeout limit was properly enforced by interrupt_hook")


if __name__ == "__main__":
  test_timeout_exceeded()
