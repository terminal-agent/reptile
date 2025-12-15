#!/usr/bin/env python3
"""
Test script to verify LLMMaxContextLengthExceeded exception handling in interrupt_hook.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from threading import Event

from autopilot.data import ContextData, InteractionMode, WorkflowConfig
from autopilot.hooks.interrupt_hook import InterruptHook
from autopilot.llm.llm import LLMMaxContextLengthExceeded
from autopilot.node.base import BaseNode, Role
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS


class MockWorkflow:
  """Mock workflow for testing"""

  def __init__(self):
    self.event = Event()
    self.workflow_config = WorkflowConfig(
      interaction_mode=InteractionMode.EXECUTIVE_ONLY,
      system_prompt=SYSTEM_PROMPT.format(
        tools_description=TOOLS.get_tools_description()
      ),
      time_out=60,
      max_steps=10,
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
    # Simulate LLMMaxContextLengthExceeded exception
    raise LLMMaxContextLengthExceeded("Token limit exceeded")


def test_exception_handling():
  """Test that LLMMaxContextLengthExceeded is properly caught by interrupt_hook"""
  print("Testing LLMMaxContextLengthExceeded exception handling...")

  # Create test data
  data = ContextData()
  hook = InterruptHook()
  mock_node = MockNode()
  mock_workflow = MockWorkflow()

  # Call pre_run_execute to set the event
  hook.pre_run_execute(data, mock_workflow)

  # Simulate exception and store it in data
  try:
    mock_node(data, None)
  except LLMMaxContextLengthExceeded as e:
    data.last_exception = e

  # Call post_node_execute - this should catch the exception
  hook.post_node_execute(data, mock_node)

  # Verify the hook handled the exception
  assert mock_workflow.event.is_set(), (
    "Event should be set when LLMMaxContextLengthExceeded is caught"
  )
  assert data.termination_reason == "Max context length exceeded", (
    f"Expected 'Max context length exceeded', got '{data.termination_reason}'"
  )

  print(
    "✅ Test passed! LLMMaxContextLengthExceeded exception was properly caught by interrupt_hook"
  )


if __name__ == "__main__":
  test_exception_handling()
