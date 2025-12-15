from typing import TYPE_CHECKING, List, Tuple

import yaml

from autopilot.data import (
  ContextData,
  DirectActionExtraInfo,
  InteractionMode,
  ReloadExtraInfo,
  Role,
)
from autopilot.utils import extract_commands

from .base_hook import BaseHook

if TYPE_CHECKING:
  from autopilot.workflow.base import BaseWorkflow


class ReloadHook(BaseHook):
  """
  ReloadHook is a hook that is used to reload the workflow from a remote GitHub repository.

  Args:
    prefix (List[Tuple[str, str]]): The prefix to reload the workflow from.
  """

  def __init__(self, prefix: List[Tuple[str, str]]):
    super().__init__()
    self.prefix = prefix

  # ========================
  # Hooks
  # ========================
  def pre_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    if self.prefix:
      extra_info = ReloadExtraInfo(reloaded_finished=False)
      # append everything as it is
      # but reexecute the command if it is a terminal step
      terminal_node = workflow.terminal_node
      for i in range(len(self.prefix)):
        role, content = self.prefix[i]
        # extract the command from the previous step
        if role == "terminal":
          prev_role, prev_content = self.prefix[i - 1]
          if prev_role == "llm":
            commands = extract_commands(prev_content)
            cmd_type, cmd = commands[0]
            # we assume output should be the same as the content,
            # but we don't check this.
            content = terminal_node._exec_and_return_output(cmd_type, cmd)
          elif (
            prev_role == "user" and i == 1
          ):  # step1-terminal-step after step0-user-step
            content = terminal_node.get_terminal_text()

        role_enum = (
          Role.USER
          if role == "terminal"
          else Role.LLM
          if role == "llm"
          else Role.USER
        )
        if i == len(self.prefix) - 1:
          # ZMQConsole needs this flag to know when reloading is finished
          extra_info.reloaded_finished = True
        terminal_node.append_and_print(
          role_enum, role, content, data, extra_info=extra_info
        )

      if (
        workflow.workflow_config.interaction_mode
        == InteractionMode.EXECUTIVE_ONLY
      ):
        workflow.hook_extra_info = DirectActionExtraInfo(
          action="p", target_step=data.num_steps - 1
        )

      # if the last step is a terminal or a user step, next an llm step
      if self.prefix[-1][0] == "terminal" or self.prefix[-1][0] == "user":
        workflow.start_node = workflow.llm_node
      # give the control to the user
      else:
        workflow.start_node = workflow.user_action_node
