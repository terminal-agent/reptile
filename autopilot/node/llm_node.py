from threading import Event
from typing import Any, Dict, Optional, Tuple

from autopilot.data import (
  ContextData,
  DirectActionExtraInfo,
  EditExtraInfo,
  ExtraInfo,
  InteractionMode,
  MessageType,
  RedirectedOutputExtraInfo,
  WorkflowConfig,
)
from autopilot.llm.llm import LLM
from autopilot.prompts import SYSTEM_PROMPT
from autopilot.terminal.term import Term
from autopilot.tools import TOOLS

from .base import BaseNode, NodeOutputType, Role


class LLMNode(BaseNode):
  """
  This is the node that uses the LLM to generate the output.

  Args:
    interrupt_event (Event): the event to interrupt the LLM generation
  """

  def __init__(
    self,
    interrupt_event: Event,
    workflow_config: WorkflowConfig,
  ):
    super().__init__(
      name="llm",
      role=Role.LLM,
      workflow_config=workflow_config,  # type: ignore
      terminal=None,
    )
    self.llm = LLM(model=workflow_config.model)
    self.interrupt_event = interrupt_event
    self.output_node: Optional[BaseNode] = None
    self.system_prompt = workflow_config.system_prompt

  def set_output_nodes(self, node: BaseNode) -> None:
    self.output_node = node

  def run(  # type: ignore[override]
    self,
    data: ContextData,
    extra_info: Optional[EditExtraInfo | RedirectedOutputExtraInfo] = None,
  ) -> NodeOutputType:
    context = data.substack
    context = [(message.role.value, message.content) for message in context]  # type: ignore

    if isinstance(extra_info, EditExtraInfo):
      edited_prefix = extra_info.edit_prefix
      original_content = extra_info.content_before_edit
      context.append(("llm", edited_prefix))  # type: ignore
    elif isinstance(extra_info, RedirectedOutputExtraInfo):
      edited_prefix = extra_info.output
      original_content = None
      context.append(("llm", edited_prefix))  # type: ignore
    else:
      edited_prefix = None
      original_content = None

    generation_stream = self.llm.generate(
      self.system_prompt,
      context,  # type: ignore
      self.interrupt_event,
    )

    step = len(data.current_branch)
    relative_step = data.absolute_step_to_relative_step(step)
    if data.in_substack:
      step_str = (
        f"{step} ({relative_step})" if relative_step != step else str(step)
      )
    else:
      step_str = str(step)
    # print the title
    if edited_prefix is None:
      title = f"# Step {step_str}"
    else:
      title = f"# Step {step_str} (amend)"
    self.console.print(
      title, use_markdown=True, message_type=MessageType.FORMATTING
    )

    # Collect token_ids from the stream
    # Note: llm.py returns accumulated token_ids in each chunk, so we only keep the latest one
    accumulated_token_ids = None
    prompt_token_ids = None

    def stream_with_token_collection(stream):
      nonlocal accumulated_token_ids, prompt_token_ids
      for chunk in stream:
        # Each chunk contains the full accumulated token_ids list up to this point
        if "token_ids" in chunk and chunk["token_ids"] is not None:
          accumulated_token_ids = chunk["token_ids"]
        if (
          "prompt_token_ids" in chunk and chunk["prompt_token_ids"] is not None
        ):
          prompt_token_ids = chunk["prompt_token_ids"]
        yield chunk

    text = self.console.stream(
      stream_with_token_collection(generation_stream),
      use_markdown=True,
      prefix=edited_prefix,
    )

    # Append the message with collected token_ids
    data.append(
      self.role.value,
      self.name,
      text,
      extra_info=extra_info,
      token_ids=accumulated_token_ids,
      prompt_token_ids=prompt_token_ids,
    )

    if self.workflow_config.interaction_mode == InteractionMode.EXECUTIVE_ONLY:
      return self.output_node, DirectActionExtraInfo(
        action="p", target_step=data.num_steps - 1
      )
    else:
      return self.output_node, None
