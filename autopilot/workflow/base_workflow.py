import signal
from abc import ABC, abstractmethod
from threading import Event
from typing import List, Optional, Union

from autopilot.console import Console, RichConsole, ZMQConsole
from autopilot.data import (
  ContextData,
  InstructionExtraInfo,
  InteractionMode,
  WorkflowConfig,
)
from autopilot.hooks import BaseHook
from autopilot.node.base import BaseNode
from autopilot.terminal import Tmux


class BaseWorkflow(ABC):
  """
  BaseWorkflow is the base class for all workflows.

  Args:
    name (str): The name of the workflow.
  """

  def __init__(self, name: str, workflow_config: WorkflowConfig):
    # create an interrupt event
    self.event = Event()

    def sigint_handler(signum, frame):
      self.event.set()

    signal.signal(signal.SIGINT, sigint_handler)

    self.term = Tmux(event=self.event, sandbox=workflow_config.sandbox)
    self.name = name
    self.start_node: Optional[BaseNode] = None
    self.hook_extra_info = None
    self.hooks: List[BaseHook] = []
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
  def get_nodes(self) -> List[BaseNode]:
    """
    Get the nodes of the workflow.
    """
    pass

  def register_hook(self, hook: BaseHook) -> None:
    """
    Register a hook to the workflow. Hooks are automatically sorted by priority.

    Args:
      hook (BaseHook): The hook to register.
    """
    self.hooks.append(hook)
    self.hooks.sort(
      key=lambda h: h.priority, reverse=True
    )  # higher number = higher priority

  @abstractmethod
  def define_graph(self) -> None:
    """
    This is the most important method of a workflow as it defines the dataflow among nodes. The programmer needs
    to implement this method and use `BaseNode.set_output_nodes` to connects the nodes. Also, you need to set the value
    for `self.start_node` to specify the start node of the workflow.
    """
    pass

  @abstractmethod
  def get_fallback_node(self) -> Optional[BaseNode]:
    """
    Get the fallback node for handling termination reasons and exceptions.
    Returns None if the workflow doesn't support fallback handling.
    """
    pass

  def call_pre_run_hooks(self, data: ContextData) -> None:
    """
    Call hooks before the workflow starts.
    """
    for hook in self.hooks:
      if hook.enabled:
        hook.pre_run_execute(data, self)

  def call_post_run_hooks(self, data: ContextData):
    """
    Call hooks after the workflow finishes.
    """
    for hook in self.hooks:
      if hook.enabled:
        hook.post_run_execute(data, self)

  def call_pre_node_hooks(self, data: ContextData, node: BaseNode):
    """
    Call hooks before a node starts.
    """
    for hook in self.hooks:
      if hook.enabled:
        hook.pre_node_execute(data, node)

  def call_post_node_hooks(self, data: ContextData, node: BaseNode):
    """
    Call hooks after a node finishes.
    """
    for hook in self.hooks:
      if hook.enabled:
        hook.post_node_execute(data, node)

  def run(self, instruction: Optional[str] = None) -> None:
    """
    Run the workflow.
    """
    data = ContextData()

    # reload hook might reset the start node and the start extra info
    self.call_pre_run_hooks(data)

    # reload
    if (
      hasattr(self, "init_prompt_node")
      and self.start_node != self.init_prompt_node
    ):
      extra_info = self.hook_extra_info
    # with instruction
    elif instruction is not None:
      extra_info = InstructionExtraInfo(instruction=instruction)
    else:
      extra_info = None

    next_node = self.start_node

    while True:
      # execute the node and update next node
      if next_node is None:
        break
      self.call_pre_node_hooks(data, next_node)
      current_node = next_node
      try:
        next_node, extra_info = next_node(data, extra_info)  # type: ignore
      except Exception as e:
        print(f"Exception occurred: {e}")
        # Store the exception in data for hooks to access
        data.last_exception = e
        next_node, extra_info = None, None
      finally:
        # Always call post_node_hooks, even if the node execution failed
        self.call_post_node_hooks(data, current_node)

      if data.termination_reason is not None:
        if (
          self.workflow_config.interaction_mode
          == InteractionMode.EXECUTIVE_ONLY
        ):
          break
        else:
          fallback_node = self.get_fallback_node()
          if fallback_node is not None:
            next_node, extra_info = fallback_node(data, extra_info)  # type: ignore
          else:
            # No fallback node available, break the loop
            break
      if next_node is None:
        break
    self.call_post_run_hooks(data)
