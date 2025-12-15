import socket
from dataclasses import dataclass
from typing import Any

from zmq import PAIR, Context

from autopilot.data import MessageType


@dataclass
class ZMQMessage:
  """
  This is the message structure to send messages between the server and the client.

  Args:
    message_type (MessageType): the type of the message
    payload (Any): the payload of the message, can be any type
  """

  message_type: MessageType
  payload: Any


class ZMQServer:
  """
  This is the server class to send and receive messages between the server and the client.

  Args:
    host (str): the host of the server, default to localhost
    port (int): the port of the server, default to 5000
  """

  def __init__(self, host: str = "localhost", port: int = 5000) -> None:
    self.host = host
    self.port = port

    # create the zmq server
    self.context = Context()
    self.socket = self.context.socket(PAIR)
    self.connect()

  def connect(self) -> None:
    # bind the socket to the host and port
    self.socket.bind(f"tcp://{self.host}:{self.port}")

  def send(self, message: ZMQMessage) -> None:
    """
    Send a message to the client.

    Args:
      message (ZMQMessage): the message to send to the client
    """
    print(f"SERVER: sending message {message}")
    self.socket.send_pyobj(message)

  def receive(self) -> ZMQMessage:
    """
    Receive a message from the client.

    Returns:
      message (ZMQMessage): the message received from the client
    """
    data = self.socket.recv_pyobj()
    print(f"SERVER: received message {data}")
    if not isinstance(data, ZMQMessage):
      raise TypeError(f"Expected ZMQMessage, got {type(data)}")
    return data

  def shutdown(self) -> None:
    """
    Shutdown the server, this is used for graceful shutdown of the web applications.
    """
    self.socket.close(linger=0)
    self.context.term()


class ZMQClient:
  """
  This is the client class to send and receive messages between the server and the client.

  Args:
    host (str): the host of the server, default to localhost
    port (int): the port of the server, default to 5000
  """

  def __init__(self, host: str = "localhost", port: int = 5000) -> None:
    self.context = Context()

    #  Socket to talk to server
    self.socket = self.context.socket(PAIR)
    self.socket.connect(f"tcp://{host}:{port}")

  def send(self, message: ZMQMessage) -> None:
    """
    Send a message to the server.

    Args:
      message (ZMQMessage): the message to send to the server
    """
    print(f"CLIENT: sending message {message}")
    self.socket.send_pyobj(message)

  def receive(self) -> ZMQMessage:
    """
    Receive a message from the server.

    Returns:
      message (ZMQMessage): the message received from the server
    """
    data = self.socket.recv_pyobj()
    print(f"CLIENT: received message {data}")
    if not isinstance(data, ZMQMessage):
      raise TypeError(f"Expected ZMQMessage, got {type(data)}")
    return data
