#!/usr/bin/env python3
"""
Test script to verify max_steps functionality in interrupt_hook.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from threading import Event

from autopilot.data import ContextData, InteractionMode, WorkflowConfig
from autopilot.hooks.interrupt_hook import InterruptHook
from autopilot.node.base import BaseNode, Role
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS


class MockWorkflow:
  """Mock workflow for testing"""

  def __init__(self):
    self.event = Event()
    self.workflow_config = WorkflowConfig(
      interaction_mode=InteractionMode.INTERACTIVE,
      system_prompt=SYSTEM_PROMPT.format(
        tools_description=TOOLS.get_tools_description()
      ),
      time_out=60,
      max_steps=5,
    )


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
    # Add a message to history to simulate workflow execution
    data.append("llm", "mock_node", f"Step {len(data.history)}")
    # Return self as the next node to simulate a loop
    return data, self


def test_max_steps_exceeded():
  """Test that max_steps limit is properly enforced by interrupt_hook"""
  print("Testing max_steps functionality...")

  # Create test data
  data = ContextData()
  max_steps_limit = 5
  hook = InterruptHook()
  mock_node = MockNode()
  mock_workflow = MockWorkflow()

  # Call pre_run_execute to set the event
  hook.pre_run_execute(data, mock_workflow)

  # Simulate workflow behavior by executing nodes multiple times
  # This will naturally add entries to data.history through the workflow execution
  current_node = mock_node
  for i in range(max_steps_limit + 2):  # Exceed by 2 steps
    # Execute the node
    data, next_node = current_node(data, None)
    # Call post_node_execute to check max_steps limit
    hook.post_node_execute(data, current_node)

    # If event is set, the max_steps limit was reached
    if mock_workflow.event.is_set():
      break

    # Move to next node (which is self in this case)
    current_node = next_node

  # Verify the hook handled the max_steps limit
  assert mock_workflow.event.is_set(), (
    "Event should be set when max_steps is exceeded"
  )
  assert data.termination_reason == f"Max step {max_steps_limit} reached", (
    f"Expected 'Max step {max_steps_limit} reached', got '{data.termination_reason}'"
  )

  print(
    "✅ Test passed! max_steps limit was properly enforced by interrupt_hook"
  )


if __name__ == "__main__":
  test_max_steps_exceeded()
