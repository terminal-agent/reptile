from threading import Event
from typing import Any, Dict, Optional, Tuple

from autopilot.data import (
  ContextData,
  DirectActionExtraInfo,
  ExtraInfo,
  MessageType,
  WorkflowConfig,
)
from autopilot.llm.llm import LLM
from autopilot.prompts import SUPERVISOR_PROMPT, SUPERVISOR_SYSTEM_PROMPT
from autopilot.terminal.term import Term

from .base import BaseNode, NodeOutputType, Role
from .user_action_node import UserActionNode


class EditorNode(UserActionNode):
  """
  EditorNode is the node that uses an LLM editor to take an action including proceed, feedback and edit.

  Args:
    event (Event): the event to interrupt the user action
    terminal (Term): the terminal to use for the workflow
    workflow_config (WorkflowConfig): the workflow config
    editor_llm (str): the model to use for the editor
  """

  def __init__(
    self,
    event: Event,
    terminal: Term,
    workflow_config: WorkflowConfig,
    editor_llm: str,
  ):
    super().__init__(event, terminal, workflow_config)
    self.name = "editor"
    self.editor_llm = LLM(model=editor_llm)

  def supervisor_step(self, data: ContextData) -> NodeOutputType:
    history_parts = []
    for message in data.substack[:-1]:
      role = message.role.value
      content = message.content
      history_parts.extend([f"# {role}", content])
    history = "\n".join(history_parts)
    if data.last_message is None:
      raise ValueError("No last message found")

    context = [
      (
        "user",
        SUPERVISOR_PROMPT.format(
          history=history, last_round=data.last_message.content
        ),
      )
    ]
    generation_stream = self.editor_llm.generate(
      SUPERVISOR_SYSTEM_PROMPT, context, self.event
    )
    self.console.print("\n[bold green]Feedback from Supervisor")
    feedback = self.console.stream(
      generation_stream,
      use_markdown=True,
    )
    self.console.print("\n", message_type=MessageType.FORMATTING)
    if "LGTM" in feedback:
      return self._proceed(data)
    else:
      self.append_and_print(
        Role.USER,
        "supervisor",
        feedback,
        data,
        title="# Step {step} (supervisor)",
      )
      return self.llm_node, None

  def run(  # type: ignore[override]
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> NodeOutputType:
    return self.supervisor_step(data)
