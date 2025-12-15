from typing import Generator, Optional, Union

from prompt_toolkit import prompt
from rich.console import Console as _Console
from rich.live import Live
from rich.markdown import Markdown

from autopilot.data import Message
from autopilot.utils import SingletonABCMeta

from .console import Console


class RichConsole(Console, metaclass=SingletonABCMeta):
  """
  RichConsole is a console implementation which uses rich to render the output.
  """

  def __init__(self):
    self.console = _Console()
    self.live = Live(self.console, refresh_per_second=10)

  def print(
    self,
    message: Union[str, Message],
    use_markdown: bool = False,
    no_markup: bool = False,
    step_num: Optional[int] = None,
    *args,
    **kwargs,
  ) -> None:
    """
    Print the message to the rich console. The `args` and `kwargs` will not take effect.

    Args:
      message (Union[str, Message]): the message to print
      use_markdown (bool): whether to use markdown to render the message
      no_markup (bool): whether to use no markup to render the message
      step_num (Optional[int]): the step number
    """

    if step_num is not None:
      title = f"# Step {step_num}"
      self.console.print(title, use_markdown=True)
    if isinstance(message, Message):
      message = message.content
    if use_markdown:
      self.console.print(Markdown(message))
    elif no_markup:
      self.console.print(message, markup=False)
    else:
      self.console.print(message)

  def stream(
    self,
    message_stream: Generator,
    prefix: Optional[str] = None,
    use_markdown: bool = False,
  ) -> str:
    """
    Stream the message chunk by chunk to the rich console with the `rich.Live` API.

    Args:
      message_stream (Generator): the message stream from the workflow
      prefix (Optional[str]): the prefix of the message
      use_markdown (bool): whether to use markdown to render the message

    Returns:
      text (str): the full text
    """
    text_buffer = ""
    if prefix is not None:
      text_buffer += prefix
    with Live(refresh_per_second=10, vertical_overflow="visible") as live:
      try:
        for text in message_stream:
          text_buffer += text["new_content"]

          if use_markdown:
            # Escape thinking tags for markdown display
            text_buffer = text_buffer.replace("<think>", "&lt;think&gt;")
            text_buffer = text_buffer.replace("</think>", "&lt;/think&gt;")
            live.update(Markdown(text_buffer))
          else:
            live.update(text_buffer)
      except Exception as e:
        self.console.print(f"[bold red]Streaming error: {e}[/bold red]")
        raise e
      finally:
        # Reverse the escape of thinking tags for history logging
        text_buffer = text_buffer.replace("&lt;think&gt;", "<think>")
        text_buffer = text_buffer.replace("&lt;/think&gt;", "</think>")

    return text_buffer

  def prompt(self, message: str = "", *args, **kwargs) -> str:
    """
    A wrapper around `prompt_toolkit.prompt` to handle KeyboardInterrupt. `args` and `kwargs` will not take effect.

    Args:
      message (str): the message to prompt

    Returns:
      result (str): the user input
    """
    multiline = kwargs.get("multiline", False)
    while True:
      try:
        result: str = prompt(message, multiline=multiline)
        return result
      except (KeyboardInterrupt, EOFError):
        confirmation = (
          prompt("Are you sure you want to exit? ([y]/n) ").strip().lower()
        )
        if confirmation == "y" or confirmation == "":
          exit(0)
