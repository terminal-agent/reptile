from typing import Callable, Generator, Optional, Union

import zmq
from rich import text

from autopilot.communication import (
  ZMQMessage,
  get_global_zmq_client,
  init_global_zmq_client,
)
from autopilot.data import Message, MessageType, ReloadExtraInfo
from autopilot.utils import SingletonABCMeta

from .console import Console


class ZMQConsole(Console, metaclass=SingletonABCMeta):
  """
  ZMQConsole is a console implementation which uses zmq to send and receive messages between the server and the client.
  This is used for web applications like Gradio.

  Args:
    port (int): the port of the zmq server
    host (str): the host of the zmq server, default to localhost
  """

  def __init__(self, port: int, host: str = "localhost"):
    # create client socket
    init_global_zmq_client(host, port)
    self.client = get_global_zmq_client()
    print(f"ZMQConsole connected to {host}:{port}")

  def print(
    self,
    message: Union[str, Message],
    use_markdown: bool = False,
    step_num: Optional[int] = None,
    message_type: Optional[MessageType] = None,
    *args,
    **kwargs,
  ) -> None:
    if message_type in [
      MessageType.LLM_RESPONSE,
      MessageType.TERMINAL_RESPONSE,
      MessageType.NO_COMMAND_FOUND,
      MessageType.USER_PROMPT,  # hard rule feedback
    ]:
      message_payload = {
        "new_content": message,
        "tokens_used": 0,
        "max_context_length": 0,
      }
      if message_type == MessageType.LLM_RESPONSE:
        data = ZMQMessage(message_type=message_type, payload=message_payload)
      else:
        data = ZMQMessage(message_type=message_type, payload=message)
      self.client.send(data)

    extra_info = kwargs.get("extra_info")
    if (
      extra_info is not None
      and isinstance(extra_info, ReloadExtraInfo)
      and extra_info.reloaded_finished
    ):
      # When reloading is finished, send `WORKFLOW_TURN_END` message to `AnnotationGradioApp` to stop reloading
      if message_type == MessageType.LLM_RESPONSE:
        self.client.send(
          ZMQMessage(message_type=MessageType.WORKFLOW_TURN_END, payload=None)
        )

  def stream(
    self,
    message_stream: Generator,
    prefix: Optional[str] = None,
    *args,
    **kwargs,
  ) -> str:
    """
    Stream the message chunk by chunk back to the server for streaming outputs. The `args` and `kwargs` will not take effect.

    Args:
      message_stream (Generator): the message stream from the workflow
      prefix (Optional[str]): the prefix of the message

    Returns:
      text (str): the l text
    """
    text_buffer = ""
    if prefix is not None:
      text_buffer += prefix
    try:
      for data in message_stream:
        text_buffer += data["new_content"]
        self.client.send(
          ZMQMessage(message_type=MessageType.LLM_RESPONSE, payload=data)
        )
    except Exception as e:
      print(f"error in file autopilot/console/zmq_console.py::stream(): {e}")
    self.client.send(
      ZMQMessage(message_type=MessageType.WORKFLOW_TURN_END, payload=None)
    )
    return text_buffer

  def prompt(self, *args, **kwargs) -> str:
    """
    This receives the user entry from the client and parse it to the workflow.
    """
    data: ZMQMessage = self.client.receive()
    if (
      data.message_type == MessageType.USER_PROMPT
      or data.message_type == MessageType.ACTION
    ):
      payload: str = data.payload
      return payload
    else:
      raise ValueError(f"Invalid message type: {data.message_type}")
