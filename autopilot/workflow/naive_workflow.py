from typing import List, Optional

from autopilot.data import WorkflowConfig
from autopilot.node import (
  BaseNode,
  InitPromptNode,
  LLMNode,
)

from .base_workflow import BaseWorkflow


class NaiveWorkflow(BaseWorkflow):
  """
  NaiveWorkflow is the workflow for a naive interaction, i.e. only one llm step.
  """

  def __init__(self, workflow_config: "WorkflowConfig"):
    super().__init__(name="naive", workflow_config=workflow_config)
    self.init_prompt_node = InitPromptNode(
      self.term, self.workflow_config, no_follow_up_terminal=True
    )
    self.llm_node = LLMNode(self.event, self.workflow_config)

    # initialize dataflow
    self.define_graph()

  def get_nodes(self) -> List[BaseNode]:
    """
    Get the nodes of the workflow.
    """
    return [
      self.init_prompt_node,
      self.llm_node,
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
        |   llm_node       |
        +------------------+
    """
    self.init_prompt_node.set_output_nodes(self.llm_node)
    self.llm_node.set_output_nodes(None)  # type: ignore
    self.start_node = self.init_prompt_node

  def get_fallback_node(self) -> Optional[BaseNode]:
    """
    Get the fallback node for handling termination reasons and exceptions.
    NaiveWorkflow doesn't support fallback handling.
    """
    return None
