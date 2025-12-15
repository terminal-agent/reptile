from .proto import ZMQClient, ZMQMessage, ZMQServer

GLOBAL_ZMQ_SERVER = None
GLOBAL_ZMQ_CLIENT = None


def init_global_zmq_server(host: str = "localhost", port: int = 5000):
  """
  Initialize the global zmq server.

  Args:
    host (str): the host of the server, default to localhost
    port (int): the port of the server, default to 5000
  """
  global GLOBAL_ZMQ_SERVER
  GLOBAL_ZMQ_SERVER = ZMQServer(host, port)


def init_global_zmq_client(host: str = "localhost", port: int = 5000):
  """
  Initialize the global zmq client.

  Args:
    host (str): the host of the client, default to localhost
    port (int): the port of the client, default to 5000
  """
  global GLOBAL_ZMQ_CLIENT
  GLOBAL_ZMQ_CLIENT = ZMQClient(host, port)


def get_global_zmq_server() -> ZMQServer:
  """
  Get the global zmq server.

  Usage:

  ```python
  from autopilot.communication import get_global_zmq_server

  server = get_global_zmq_server()
  server.send(ZMQMessage(message_type=MessageType.WORKFLOW_READY, payload=None))
  ```

  """
  global GLOBAL_ZMQ_SERVER
  assert GLOBAL_ZMQ_SERVER is not None, "ZMQ server not initialized"
  return GLOBAL_ZMQ_SERVER


def get_global_zmq_client() -> ZMQClient:
  """
  Get the global zmq client.

  Usage:

  ```python
  from autopilot.communication import get_global_zmq_client

  client = get_global_zmq_client()
  client.send(ZMQMessage(message_type=MessageType.WORKFLOW_READY, payload=None))
  ```

  """
  global GLOBAL_ZMQ_CLIENT
  assert GLOBAL_ZMQ_CLIENT is not None, "ZMQ client not initialized"
  return GLOBAL_ZMQ_CLIENT


__all__ = [
  "ZMQServer",
  "ZMQClient",
  "init_global_zmq_server",
  "init_global_zmq_client",
  "get_global_zmq_server",
  "get_global_zmq_client",
  "ZMQMessage",
]
