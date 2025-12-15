from abc import ABC, abstractmethod
from optparse import Option
from typing import Any, Dict, Optional, Tuple, Union

from autopilot.communication.proto import MessageType
from autopilot.console.console import Console
from autopilot.console.rich_console import RichConsole
from autopilot.console.zmq_console import ZMQConsole
from autopilot.data import (
  ContextData,
  ExtraInfo,
  InteractionMode,
  RedirectedOutputExtraInfo,
  Role,
  WorkflowConfig,
)
from autopilot.terminal.term import Term

NodeOutputType = Tuple[
  Optional["BaseNode"],
  Optional[
    Union[
      ExtraInfo,
      Dict[str, Any],
      RedirectedOutputExtraInfo,
    ]
  ],
]


class BaseNode(ABC):
  """
  BaseNode is the interface for all nodes in the workflow.

  Args:
    name (str): the name of the node
    role (Role): the role of the node
    workflow_config (WorkflowConfig): the workflow configuration
    terminal (Term): the terminal to use for the workflow
  """

  def __init__(
    self,
    name: str,
    role: Role,
    workflow_config: WorkflowConfig,
    terminal: Optional[Term] = None,
  ):
    self.name = name
    self.role = role
    self.terminal = terminal
    self.workflow_config = workflow_config

    # Initialize console based on interaction mode
    self.console: Console
    if workflow_config.interaction_mode == InteractionMode.INTERACTIVE_BY_ZMQ:
      if workflow_config.zmq_host is None or workflow_config.zmq_port is None:
        raise ValueError(
          "zmq_host and zmq_port must be provided when using INTERACTIVE_BY_ZMQ mode"
        )
      self.console = ZMQConsole(
        host=workflow_config.zmq_host,
        port=workflow_config.zmq_port,
      )
    else:
      self.console = RichConsole()

  @abstractmethod
  def set_output_nodes(self, *args, **kwargs) -> None:
    """
    Set the output nodes for the node.
    """
    pass

  def __call__(
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> NodeOutputType:
    """
    Execute the nodes.

    Args:
        data (ContextData): the data of the workflow
        extra_info (ExtraInfo): the extra information of the node

    Returns:
        next_node (BaseNode): the next node
        extra_info (ExtraInfo): the extra information of the node that the next node needs to know
    """
    next_node, run_extra_info = self.run(data, extra_info)
    return next_node, run_extra_info

  @abstractmethod
  def run(
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> NodeOutputType:
    """
    This is an abstract method that should be implemented by all child class nodes.

    Args:
        data (ContextData): the data of the workflow
        extra_info (ExtraInfo): the extra information of the node

    Returns:
        next_node (BaseNode): the next node
        extra_info (ExtraInfo): the extra information of the node that the next node needs to know
    """
    pass

  def append_and_print(
    self,
    role: Role,
    name: str,
    content: str,
    data: ContextData,
    title: str = "# Step {step}",
    extra_info: Optional[ExtraInfo] = None,
  ) -> None:
    """
    Add the message to the context data and send its output to the console.

    Args:
        role (Role): the role of the message
        name (str): the name of the message
        content (str): the content of the message
        data (ContextData): the data of the workflow
        title (str): the title of the message, default to f"# Step {step}"
        extra_info (ExtraInfo): the extra information of the message
    """
    # step starts from 0
    step = len(data.current_branch)
    if data.in_substack:
      relative_step = data.absolute_step_to_relative_step(step)
      step_str = (
        f"{step} ({relative_step})" if relative_step != step else str(step)
      )
    else:
      step_str = str(step)
    title = title.format(step=step_str)
    is_llm_response = role == Role.LLM
    is_user_response = role == Role.USER
    data.append(role.value, name, content, extra_info)

    if name == "terminal" and role == Role.USER:
      message_type = MessageType.TERMINAL_RESPONSE
    elif name == "user" and role == Role.USER:
      message_type = MessageType.USER_PROMPT
    elif role == Role.LLM:
      message_type = MessageType.LLM_RESPONSE
    else:
      message_type = MessageType.FORMATTING

    self.console.print(
      title,
      use_markdown=True,
      message_type=MessageType.FORMATTING,
      extra_info=extra_info,
    )
    self.console.print(
      content,
      use_markdown=is_llm_response,
      no_markup=is_user_response,
      message_type=message_type,
      extra_info=extra_info,
    )

  def get_terminal_text(self, screen: bool = False) -> str:
    """
    Get the text from the terminal.

    Args:
        screen (bool): whether to get the screen text, default to False

    Returns:
        text (str): the text from the terminal
    """
    assert self.terminal is not None, "Terminal is not set"
    if self.terminal.alternate_on or screen:
      text = self.terminal.get_screen()
    else:
      text = self.terminal.get_new_text()
    text = f"## terminal:\n{text}\n"
    return text
