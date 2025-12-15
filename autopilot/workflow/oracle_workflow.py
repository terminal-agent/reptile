from typing import List, Optional

from autopilot.data import WorkflowConfig
from autopilot.node import (
  BaseNode,
  InitPromptNode,
  OracleNode,
  TerminalNode,
)

from .base_workflow import BaseWorkflow


class OracleWorkflow(BaseWorkflow):
  """
  OracleWorkflow is the workflow for examine the gold solution.
  """

  def __init__(self, workflow_config: "WorkflowConfig"):
    super().__init__(name="oracle", workflow_config=workflow_config)
    self.terminal_node = TerminalNode(self.term, self.workflow_config)
    self.oracle_node = OracleNode(self.workflow_config)
    self.init_prompt_node = InitPromptNode(self.term, self.workflow_config)

    # initialize dataflow
    self.define_graph()

  def get_nodes(self) -> List[BaseNode]:
    """
    Get the nodes of the workflow.
    """
    return [
      self.init_prompt_node,
      self.oracle_node,
      self.terminal_node,
    ]

  def define_graph(self) -> None:
    """
    We define the graph as follows

    Flow:
        +------------------+
        | init_prompt_node |
        +------------------+
                |
                v
        +------------------+
        |   oracle_node    |
        +------------------+
                |
                v
        +------------------+
        |  terminal_node   |
        +------------------+
    """
    self.init_prompt_node.set_output_nodes(self.oracle_node)
    self.oracle_node.set_output_nodes(self.terminal_node)
    self.terminal_node.set_output_nodes(None)  # type: ignore
    self.start_node = self.init_prompt_node

  def get_fallback_node(self) -> Optional[BaseNode]:
    """
    Get the fallback node for handling termination reasons and exceptions.
    OracleWorkflow doesn't support fallback handling.
    """
    return None
