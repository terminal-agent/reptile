from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from autopilot.node.base import BaseNode
  from autopilot.workflow.base import BaseWorkflow


from autopilot.data import ContextData

__all__ = ["BaseHook"]


class BaseHook:
  """
  BaseHook is the base class for all hooks. It covers the lifecycle of the workflow and is useful to
  insert control flow or sidecar logic into the workflow.

  Args:
    priority (int): the priority of the hook. Higher number = higher priority. default is 0.
  """

  def __init__(self, priority: int = 0):
    self.enabled = True
    self.priority = priority  # higher number = higher priority

  def disable(self) -> None:
    """
    Disable the hook so that it will not be executed.
    """
    self.enabled = False

  def enable(self) -> None:
    """
    Enable the hook so that it will be executed.
    """
    self.enabled = True

  def pre_run_execute(self, data: ContextData, workflow: BaseWorkflow) -> None:
    """
    This method is called before the workflow starts.

    Args:
      data (ContextData): the data of the workflow
      workflow (BaseWorkflow): the workflow that is about to be executed
    """
    pass

  def pre_node_execute(self, data: ContextData, node: BaseNode) -> None:
    """
    This method is called before the node starts.

    Args:
      data (ContextData): the context data of the workflow
      node (BaseNode): the node that is about to be executed
    """
    pass

  def post_node_execute(self, data: ContextData, node: BaseNode) -> None:
    """
    This method is called after the node finishes.

    Args:
      data (ContextData): the context data of the workflow
      node (BaseNode): the node that has been executed
    """
    pass

  def post_run_execute(self, data: ContextData, workflow: BaseWorkflow) -> None:
    """
    This method is called after the workflow finishes.

    Args:
      data (ContextData): the context data of the workflow
      workflow (BaseWorkflow): the workflow that has finished
    """
    pass
