import os
import sys
from threading import Event, Thread
from typing import Any, Generator, List, Tuple

from openai import OpenAI

from autopilot.config import GLOBAL_CONFIG, LLMConfig
from autopilot.constants import _DEFAULT_MAX_TOKENS
from autopilot.utils import console, ensure_list, safe_get


class LLMAPIError(Exception):
  """Exception raised when the LLM API returns an error."""

  pass


class LLMInterrupted(Exception):
  """Exception raised when the LLM is interrupted by the user."""

  pass


class LLMMaxContextLengthExceeded(Exception):
  """Exception raised when the LLM context length is exceeded."""

  pass


ContextType = List[Tuple[str, str]]


class LLM:
  """
  LLM is the class wrapper for the LLM API.

  Args:
    model (str): the model to use
  """

  def __init__(self, model=None):
    # check the model to use via environment variable
    # by default, we use the first model in the config file
    # we match the llm config by name
    llm_configs = GLOBAL_CONFIG.models

    if model is None:
      # get the index of the model with the highest priority
      target_config = max(llm_configs, key=lambda x: x.priority)
    else:
      # get the model from command line argument
      target_config = next(
        (config for config in llm_configs if config.name == model), None
      )  # type: ignore
      if target_config is None:
        raise ValueError(f"Model {model} not found in config")

    console.log(
      f"running LLM with {target_config.name} - "
      f"{target_config.parameters.model}"
    )

    # initialize the client
    self.config = target_config
    self.client = OpenAI(**target_config.credentials.dict())
    self.max_context_length = self.get_max_context_length()
    env_stream = os.getenv("AUTOPILOT_STREAMING", "1").strip()
    self.streaming = env_stream != "0"
    print(f"Streaming: {self.streaming}", file=sys.stderr)

  def merge_context(self, context: ContextType) -> ContextType:
    """
    This is only for the Google-Gemma-like model. Somehow the gemma model prevents us from using the same role in a row,
    so we need to merge the context.

    Args:
      context (ContextType): the context to merge

    Returns:
      ContextType: the merged context
    """
    prev_role = None
    merged = []
    for role, ctx in context:
      if role == "terminal":
        role = "user"
      if role != prev_role:
        merged.append((role, ctx))
        prev_role = role
      else:
        merged[-1] = (role, merged[-1][1] + "\n" + ctx)
    return merged

  def prepend_idx(self, context: ContextType) -> ContextType:
    """
    Add the index of the message to the content.

    Args:
      context (ContextType): the context to prepend the index to

    Returns:
      ContextType: the context with the index prepended
    """
    context = [
      (role, f"<label:{i}>\n{content}")
      for i, (role, content) in enumerate(context)
    ]
    # if prev step is assistant
    if context[-1][0] != "llm":
      context.append(("llm", f"<label:{len(context)}>\n"))
    return context

  def _generate_stream(
    self, prompt: str, stop_event: Event, context: list
  ) -> Generator[dict[str, Any], None, None]:
    """
    Generate the stream of the LLM response.

    Args:
      prompt (str): the prompt to generate the response
      stop_event (Event): the event to stop the generation
      context (ContextType): the context to generate the response

    Returns:
      Generator[str, None, None]: the stream of the LLM response
    """
    if stop_event.is_set():
      raise LLMInterrupted("LLM interrupted, pass control to user")

    should_stream = self.streaming

    if self.config.name == "gemma":
      context = self.merge_context(context)
    messages = []
    if prompt:
      messages.append({"role": "system", "content": prompt})
    messages += [
      {"role": ("assistant" if role == "llm" else "user"), "content": ctx}
      for role, ctx in context
      if ctx != ""  # ignore empty context (which is used for resampling)
    ]

    _default_parameters = dict(temperature=0.7, stream=should_stream)
    _default_parameters.update(self.config.parameters)

    last_role = messages[-1]["role"] if messages else None
    base_url = self.config.credentials.base_url

    # vllm server on k8s.
    # if self-hosted, use "http:" in base_url
    # if sre-hosted, use "vllm" in base_url
    is_vllm = "http:" in base_url or "vllm" in base_url

    if is_vllm:
      # Always request token_ids for vLLM
      _default_parameters["extra_body"] = {  # type: ignore[assignment]
        "return_token_ids": True,
      }
      if last_role == "assistant":  # for llm completion under editing-mode
        _default_parameters["extra_body"].update(  # type: ignore[attr-defined]
          {
            "add_generation_prompt": True,
            "continue_final_message": False,
          }
        )

    _default_parameters["stream_options"] = {"include_usage": True}  # type: ignore[assignment]

    if base_url == "https://api.deepseek.com/beta" and last_role == "assistant":
      messages[-1]["prefix"] = True  # type: ignore[assignment]

    if (
      base_url == "https://api.moonshot.cn/v1"
      or base_url == "https://api.moonshot.ai/v1"
    ) and last_role == "assistant":
      messages[-1]["partial"] = True  # type: ignore[assignment]

    try:
      streamed_response = self.client.chat.completions.create(
        messages=messages, **_default_parameters
      )
    except Exception as e:
      if (
        "maximum context length" in str(e)  # gemma
        or "max_tokens must be at least" in str(e)  # devstral
      ):
        raise LLMMaxContextLengthExceeded("Token limit exceeded")
      else:
        raise LLMAPIError("LLM API error")

    if not should_stream:
      yield from self._single_step_generator(streamed_response, stop_event)
      return

    # Accumulate token_ids across chunks
    accumulated_token_ids: list[int] = []
    prompt_token_ids: list[int] | None = None
    for chunk in streamed_response:
      # If stop event is set, stop streaming
      if stop_event.is_set():
        raise LLMInterrupted("LLM interrupted, pass control to user")

      # Check for prompt_token_ids (usually in first chunk, before content)
      if is_vllm and not prompt_token_ids:
        pt_ids = safe_get(chunk, "prompt_token_ids")
        if pt_ids is not None:
          prompt_token_ids = ensure_list(pt_ids)

      # Check for usage information in the chunk.
      usage = safe_get(chunk, "usage")
      if usage is not None:
        yield {
          "new_content": "",
          "tokens_used": safe_get(usage, "total_tokens", 0),
          "max_context_length": self.max_context_length,
          "token_ids": accumulated_token_ids.copy()
          if accumulated_token_ids
          else None,
          "prompt_token_ids": prompt_token_ids.copy()
          if prompt_token_ids
          else None,
        }
        continue

      # Extract content from the chunk
      try:
        new_content = safe_get(chunk, "choices.0.delta.content")
        if new_content is not None:
          chunk_token_ids = None
          if is_vllm:
            choice = safe_get(chunk, "choices.0")
            # In streaming mode, token_ids is in choice.token_ids (not in delta)
            t_ids = safe_get(choice, "token_ids")
            if t_ids is not None:
              chunk_token_ids = ensure_list(t_ids)

            # Accumulate token_ids
            if chunk_token_ids is not None:
              accumulated_token_ids.extend(chunk_token_ids)

          yield {
            "new_content": new_content,
            "tokens_used": 0,  # `chunk.usage` is None except for the last chunk
            "max_context_length": self.max_context_length,
            "token_ids": accumulated_token_ids.copy()
            if accumulated_token_ids
            else None,
            "prompt_token_ids": prompt_token_ids.copy()
            if prompt_token_ids
            else None,
          }
      except IndexError:  # openai sometimes returns None
        pass

  def _single_step_generator(
    self, response: Any, stop_event: Event
  ) -> Generator[dict[str, Any], None, None]:
    if stop_event.is_set():
      raise LLMInterrupted("LLM interrupted, pass control to user")

    choice = safe_get(response, "choices.0")

    new_content = (
      safe_get(choice, "message.content")
      or safe_get(choice, "delta.content")
      or safe_get(choice, "text")
      or ""
    )

    chunk_token_ids = ensure_list(safe_get(choice, "token_ids"))
    prompt_token_ids = ensure_list(safe_get(response, "prompt_token_ids"))
    usage_tokens = safe_get(response, "usage.total_tokens", 0)

    yield {
      "new_content": new_content,
      "tokens_used": usage_tokens,
      "max_context_length": self.max_context_length,
      "token_ids": chunk_token_ids,
      "prompt_token_ids": prompt_token_ids,
    }

  def generate(
    self, system_prompt: str, context: ContextType, event: Event
  ) -> Generator[dict[str, Any], None, None]:
    """
    Generate the response from the LLM.

    Args:
      system_prompt (str): the system prompt to generate the response
      context (ContextType): the context to generate the response
      event (Event): the event to stop the generation

    returns:
      Generator[str, None, None]: the stream of the LLM response
    """
    # context = self.prepend_idx(context)
    streamed_response = self._generate_stream(system_prompt, event, context)
    return streamed_response

  def get_max_context_length(self) -> int:
    """
    Get the maximum context length of the model.
    Returns:
      int: the maximum context length
    """
    try:
      models = self.client.models.list()
      model_info = models.data[0]
      if hasattr(model_info, "max_model_len"):
        return int(model_info.max_model_len)
      elif hasattr(model_info, "context_length"):
        return int(model_info.context_length)
      else:
        return int(_DEFAULT_MAX_TOKENS)
    except Exception:
      return int(_DEFAULT_MAX_TOKENS)
