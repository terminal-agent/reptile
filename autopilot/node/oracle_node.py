from typing import Optional, Tuple

from autopilot.data import (
  ContextData,
  ExtraInfo,
  WorkflowConfig,
)

from .base import BaseNode, NodeOutputType, Role


class OracleNode(BaseNode):
  """
  OracleNode is the node to examine the gold solution.

  Args:
    workflow_config (WorkflowConfig): the workflow config
  """

  def __init__(
    self,
    workflow_config: WorkflowConfig,
  ):
    super().__init__(
      name="oracle",
      role=Role.LLM,
      terminal=None,
      workflow_config=workflow_config,
    )

  def set_output_nodes(self, node: BaseNode) -> None:
    self.output_node = node

  def run(
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> NodeOutputType:
    gold_solution = """```bash
bash /tmp/tasks/shared_scripts/solution.sh
```"""
    self.append_and_print(self.role, self.name, gold_solution, data)
    return self.output_node, None
