from typing import Any, Dict, Optional, Tuple

from autopilot.console.rich_console import RichConsole
from autopilot.console.zmq_console import ZMQConsole
from autopilot.data import (
  ContextData,
  ExtraInfo,
  InstructionExtraInfo,
  InteractionMode,
  WorkflowConfig,
)
from autopilot.terminal.term import Term

from .base import BaseNode, NodeOutputType, Role


class InitPromptNode(BaseNode):
  """
  This is the start node of the workflow which prompts the user for a task.

  Args:
    terminal (Term): the terminal to use for the workflow.
    no_follow_up_terminal (bool): whether to print the terminal follow up. This is to mimic the LLM-only agent's behavior, termed `naive` mode.
  """

  def __init__(
    self,
    terminal: Term,
    workflow_config: WorkflowConfig,
    no_follow_up_terminal: bool = False,
  ):
    super().__init__("init-prompt", Role.USER, workflow_config, terminal)
    self.output_node: Optional[BaseNode] = None
    self.no_follow_up_terminal = no_follow_up_terminal

  def set_output_nodes(self, node: BaseNode) -> None:
    self.output_node = node

  def run(  # type: ignore[override]
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> NodeOutputType:
    if isinstance(extra_info, InstructionExtraInfo):
      instruction = extra_info.instruction
    else:
      if (
        self.workflow_config.interaction_mode
        == InteractionMode.INTERACTIVE_BY_ZMQ
      ):
        assert isinstance(self.console, ZMQConsole)
        instruction = self.console.prompt()
      else:
        assert isinstance(self.console, RichConsole)
        self.console.print(
          "[bold green]Describe the task that you want autopilot to do."
        )
        # TODO (lsg): handle history=user_instruction_history
        instruction = self.console.prompt("> ", multiline=True)

    # Ensure instruction is not None
    if instruction is None:
      raise ValueError("No instruction provided")

    self.append_and_print(Role.USER, "user", instruction, data)
    if not self.no_follow_up_terminal:
      term_text = self.get_terminal_text()
      self.append_and_print(Role.USER, "terminal", term_text, data)
    return self.output_node, None
