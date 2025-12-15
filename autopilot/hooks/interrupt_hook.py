import time
from threading import Event, Thread
from typing import TYPE_CHECKING

from autopilot.data import ContextData, InteractionMode
from autopilot.llm.llm import (
  LLMAPIError,
  LLMInterrupted,
  LLMMaxContextLengthExceeded,
)
from autopilot.node.base import BaseNode

from .base_hook import BaseHook

if TYPE_CHECKING:
  from autopilot.workflow.base_workflow import BaseWorkflow


class InterruptHook(BaseHook):
  """
  InterruptHook is a hook that is used to interrupt the workflow.
  """

  def pre_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    self.event = workflow.event

    # Read values from workflow_config if not provided in constructor
    self.timeout = workflow.workflow_config.time_out
    self.max_steps = workflow.workflow_config.max_steps
    self.max_current_steps = workflow.workflow_config.max_current_steps

    def monitor_executor():
      if self.event is None:
        return
      start_time = time.time()
      while not self.event.is_set():
        elapsed_time = time.time() - start_time
        if self.timeout is not None and elapsed_time > self.timeout:
          workflow.console.print(f"\n[Timeout {self.timeout}s reached]")
          self.event.set()
          data.termination_reason = f"Timeout {self.timeout}s reached"
          break
        self.event.wait(1)

    if self.timeout is not None:
      Thread(target=monitor_executor, daemon=True).start()

  def post_node_execute(self, data: ContextData, node: BaseNode) -> None:
    assert self.event is not None, "Event is not set"

    # ================================================
    # Outside Node Interruption
    # ================================================
    if self.max_steps is not None and len(data.history) > self.max_steps:
      node.console.print(
        f"[bold red]Max steps {self.max_steps} reached[/bold red]"
      )
      self.event.set()
      data.termination_reason = f"Max step {self.max_steps} reached"
    if (
      self.max_current_steps is not None
      and len(data.substack) > self.max_current_steps
    ):
      node.console.print(
        f"[bold red]Max current steps {self.max_current_steps} reached[/bold red]"
      )
      self.event.set()
      data.termination_reason = (
        f"Max current step {self.max_current_steps} reached"
      )

    # ================================================
    # Inside Node Interruption
    # ================================================
    if data.last_exception:
      self.event.set()

      # If termination_reason is already set (e.g., by timeout monitor),
      # preserve it instead of overwriting
      if data.termination_reason is not None:
        return

      # Incorrect API Key
      if isinstance(data.last_exception, LLMAPIError):
        data.termination_reason = "LLM API error"
      # Max Context Length Exceeded
      elif isinstance(data.last_exception, LLMMaxContextLengthExceeded):
        data.termination_reason = "Max context length exceeded"
      # LLM Interrupted by user
      # Only set "LLM interrupted" if termination_reason is not already set
      # (e.g., by timeout monitor). If timeout occurred during LLM node execution,
      # it will trigger LLMInterrupted exception, but we preserve the "Timeout" reason.
      elif (
        isinstance(data.last_exception, LLMInterrupted)
        and node.workflow_config.interaction_mode
        != InteractionMode.EXECUTIVE_ONLY
      ):
        data.termination_reason = "LLM interrupted"

  def post_run_execute(
    self, data: ContextData, workflow: "BaseWorkflow"
  ) -> None:
    if data.termination_reason:
      workflow.console.print(
        f"[bold red]Run terminated due to {data.termination_reason}[/bold red]"
      )
