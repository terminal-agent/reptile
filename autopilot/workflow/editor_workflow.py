from typing import List, Optional

from autopilot.console.rich_console import RichConsole
from autopilot.data import WorkflowConfig
from autopilot.node import (
  BaseNode,
  EditorNode,
  InitPromptNode,
  LLMNode,
  TerminalNode,
)

from .base_workflow import BaseWorkflow


class EditorWorkflow(BaseWorkflow):
  """
  EditorWorkflow is the workflow for using an LLM editor to supervise the LLM worker
  by providing feedback and editing the LLM worker's output.
  """

  def __init__(self, workflow_config: "WorkflowConfig", editor: str):
    super().__init__(name="editor", workflow_config=workflow_config)
    self.terminal_node = TerminalNode(self.term, self.workflow_config)
    self.editor_node = EditorNode(
      self.event, self.term, self.workflow_config, editor
    )
    self.llm_node = LLMNode(self.event, self.workflow_config)
    self.init_prompt_node = InitPromptNode(self.term, self.workflow_config)

    # initialize dataflow
    self.define_graph()

  def get_nodes(self) -> List[BaseNode]:
    """
    Get the nodes of the workflow.
    """
    return [
      self.init_prompt_node,
      self.llm_node,
      self.editor_node,
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
        |    llm_node      | <----+-------------------+
        +------------------+      |                   |
                |                 |                   |
                v                 | edit/feedback     |
        +------------------+      |                   |
        |   editor_node    | -----+                   |
        +------------------+                          |
                | proceed                             |
                v                                     |
        +------------------+                          |
        | terminal_node    | -------------------------+
        +------------------+
    """
    self.init_prompt_node.set_output_nodes(self.llm_node)
    self.llm_node.set_output_nodes(self.editor_node)
    self.editor_node.set_output_nodes(self.llm_node, self.terminal_node)
    self.terminal_node.set_output_nodes(self.llm_node)
    self.start_node = self.init_prompt_node

  def get_fallback_node(self) -> Optional[BaseNode]:
    """
    Get the fallback node for handling termination reasons and exceptions.
    EditorWorkflow currently doesn't support fallback handling.
    """
    # TODO (Longxu): use editor node as fallback node
    return None
