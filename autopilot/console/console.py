from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Generator, Optional, Union

from autopilot.data import Message


class Console(ABC):
  """
  Console is an abstract class which takes charge of sending the output to the target console.
  """

  @abstractmethod
  def stream(
    self,
    message_stream: Generator,
    prefix: Optional[str] = None,
    use_markdown: bool = False,
  ) -> str:
    """
    Stream the message chunk by chunk to the target console.

    The text_extractor is a function which extracts the text content from the stream object
    if the stream object is not directly a text.

    ```python
    def sample_extractor(stream_obj):
      return stream_obj.text
    ```

    Args:
      message_stream (Generator): A generator which outputs the message by chunk.
      prefix (str): The prefix of the message.
      use_markdown (bool): Whether to use markdown to render the message.

    Returns:
      text (str): The concatenated text.
    """
    pass

  @abstractmethod
  def print(
    self,
    message: Union[str, Message],
    use_markdown: bool = False,
    *args,
    **kwargs,
  ) -> None:
    """
    Print the message to the target console.

    Args:
      message (str): The message to be printed.
      use_markdown (bool): Whether to use markdown to render the message.
    """
    pass

  @abstractmethod
  def prompt(self, message: str = "", **kwargs) -> str:
    """
    Prompt the user for input.

    Args:
      message (str): The prompt message to display.
      **kwargs: Additional arguments for specific console implementations.

    Returns:
      str: The user input.
    """
    pass
