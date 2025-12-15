from typing import TYPE_CHECKING

from autopilot.communication import (
  ZMQMessage,
  get_global_zmq_client,
)
from autopilot.data import ContextData, MessageType

from .base_hook import BaseHook

if TYPE_CHECKING:
  from autopilot.workflow.base_workflow import BaseWorkflow


class GradioHook(BaseHook):
  """
  GradioHook is a hook that is used to send signals to the Gradio application via ZMQ.
  """

  def __init__(self):
    super().__init__()
    self.client = get_global_zmq_client()

  def pre_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    # send the WORKFLOW_READY signal to the Gradio application
    self.client.send(
      ZMQMessage(message_type=MessageType.WORKFLOW_READY, payload=None)
    )
