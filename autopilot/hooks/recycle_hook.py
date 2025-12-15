from typing import TYPE_CHECKING

from autopilot.data import ContextData

from .base_hook import BaseHook

if TYPE_CHECKING:
  from autopilot.workflow.base_workflow import BaseWorkflow


class RecycleHook(BaseHook):
  def __init__(self):
    super().__init__(
      priority=-99999
    )  # lower priority to make sure other hooks have finished first

  def post_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    workflow.term.shutdown()
