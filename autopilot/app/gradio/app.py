import logging
import signal
import sys
import time
from multiprocessing import Process
from pathlib import Path
from typing import List, Optional

import gradio as gr
from gradio_autopilot_chatbot import AgentChatbot
from gradio_autopilot_chatbot.agentchatbot import Message

from autopilot.app.gradio.budget_chart import BudgetProgressChart
from autopilot.app.gradio.token_budget import TokenBudgetManager
from autopilot.communication import (
  ZMQMessage,
  ZMQServer,
  get_global_zmq_server,
  init_global_zmq_server,
)
from autopilot.data import MessageType
from autopilot.workflow.autopilot_workflow import AutopilotWorkflow

from .utils import launch_workflow

logger = logging.getLogger(__name__)


class AutopilotGradioApp:
  def __init__(
    self,
    model: Optional[str] = None,
    name: Optional[str] = None,
    max_steps: Optional[int] = None,
    max_current_steps: Optional[int] = None,
    max_time: Optional[int] = None,
    log_to_mongodb: Optional[bool] = None,
    log_to_github: Optional[bool] = None,
    sandbox: Optional[str] = None,
  ):
    # app configs
    self.model = model
    self.sandbox = sandbox
    self.name = name
    self.max_steps = max_steps
    self.max_current_steps = max_current_steps
    self.max_time = max_time
    self.log_to_mongodb = log_to_mongodb
    self.log_to_github = log_to_github

    # app states
    self.history: List[Message] = []
    self.workflow: Optional[AutopilotWorkflow] = None
    self.workflow_process: Optional[Process] = None
    self.server: Optional[ZMQServer] = None
    self._shutdown_initiated = False

    # Backend: Token budget management
    self.budget_manager = TokenBudgetManager()

    # Frontend: Budget chart visualization
    self.budget_chart = BudgetProgressChart(
      budget_manager=self.budget_manager,
      chart_size=150,
    )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, self._sigint_handler)

  def _sigint_handler(self, signum, frame):
    if self._shutdown_initiated:
      return

    self.cleanup()
    sys.exit(0)

  def _update_token_budget(self, response: ZMQMessage) -> None:
    """Update token budget from LLM response payload."""
    tokens_used = response.payload["tokens_used"]
    max_content_length = response.payload["max_context_length"]
    # Backend handles all the token budget logic
    self.budget_manager.update_from_llm_response(
      tokens_used, max_content_length
    )

  def launch_zmq_server(self, zmq_port: int):
    print("launching zmq server")
    init_global_zmq_server(port=zmq_port)
    print("zmq server launched")
    self.server = get_global_zmq_server()

  def kill_zmq_server(self):
    if self.server is not None:
      self.server.shutdown()
      self.server = None

  def _receive_messages(self):
    if self.server is None:
      raise RuntimeError("ZMQ server not initialized")
    while True:
      # receive message from the workflow
      # stop when the message is from an LLM
      response: ZMQMessage = self.server.receive()

      if response.message_type == MessageType.TERMINAL_RESPONSE:
        self.history.append(
          Message(name="terminal", role="assistant", content=response.payload)
        )
        yield self.history, self.budget_chart.get_budget_chart()
      elif response.message_type == MessageType.LLM_RESPONSE:
        content = response.payload["new_content"]
        self._update_token_budget(response)

        if self.history[-1].name == "llm":
          self.history[-1].content += content
        else:
          self.history.append(
            Message(
              name="llm",
              role="assistant",
              content=content,
            )
          )
        yield self.history, self.budget_chart.get_budget_chart()
      elif response.message_type == MessageType.WORKFLOW_TURN_END:
        break
      elif response.message_type == MessageType.NO_COMMAND_FOUND:
        gr.Warning("No command found in the LLM response, cannot proceed.")
        break
      else:
        continue

  def add_message(self, msg):
    if self.server is None:
      gr.Error("Server not initialized")
      return "", self.history, self.budget_chart.get_budget_chart()

    if len(self.history) == 0 and msg == "":
      # empty prompt
      return "", self.history, self.budget_chart.get_budget_chart()
    elif len(self.history) == 0 and msg != "":
      # initial user prompt
      self.server.send(
        ZMQMessage(message_type=MessageType.USER_PROMPT, payload=msg)
      )
      self.history.append(Message(name="user", role="user", content=msg))
    elif len(self.history) > 0 and msg == "":
      # proceed
      self.server.send(ZMQMessage(message_type=MessageType.ACTION, payload="p"))
    elif msg != "":
      # feedback
      self.server.send(ZMQMessage(message_type=MessageType.ACTION, payload="f"))
      self.server.send(
        ZMQMessage(message_type=MessageType.USER_PROMPT, payload=msg)
      )
      self.history.append(Message(name="user", role="user", content=msg))
      yield "", self.history, self.budget_chart.get_budget_chart()
    else:
      gr.Warning("Invalid message")
      return "", self.history, self.budget_chart.get_budget_chart()

    for history, chart in self._receive_messages():
      yield "", history, chart
    yield "", self.history, self.budget_chart.get_budget_chart()

  def load_history(self):
    return self.history

  def reset(self):
    self.history = []
    self.budget_manager.reset()

    # restart the workflow
    gr.Info("Terminating workflow...")

    if self.workflow_process is None:
      gr.Error(
        "Workflow process is not initialized, please try to restart the app"
      )
      return self.history, self.budget_chart.get_budget_chart()

    if self.server is None:
      gr.Error("ZMQ server is not initialized, please try to restart the app")
      return self.history, self.budget_chart.get_budget_chart()

    self.workflow_process.terminate()
    self.server.shutdown()
    gr.Success("Workflow terminated")

    gr.Info(
      "Restarting workflow..., please wait for the success notification before sending a new message"
    )
    self.launch_zmq_server(zmq_port=self.zmq_port)
    self.workflow_process = self.start_workflow(zmq_port=self.zmq_port)
    gr.Success("Workflow restarted")

    return self.history, self.budget_chart.get_budget_chart()

  def edit_message(self, edit_data: gr.EditData):
    if self.server is None:
      gr.Error("Server not initialized")
      return self.history, self.budget_chart.get_budget_chart()

    self.history = self.history[: edit_data.index + 1]
    self.history[-1].content = edit_data.value
    self.server.send(
      ZMQMessage(
        message_type=MessageType.ACTION, payload=f"e {edit_data.index}"
      )
    )
    self.server.send(
      ZMQMessage(
        message_type=MessageType.USER_PROMPT,
        payload=self.history[-1].content,
      )
    )

    while True:
      # receive message from the workflow
      # stop when the message is from an LLM
      response: ZMQMessage = self.server.receive()
      if response.message_type == MessageType.LLM_RESPONSE:
        content = response.payload["new_content"]
        self._update_token_budget(response)

        self.history[-1].content += content
        yield self.history, self.budget_chart.get_budget_chart()
      elif response.message_type == MessageType.WORKFLOW_TURN_END:
        break
      else:
        continue
    return self.history, self.budget_chart.get_budget_chart()

  def build_app(self):
    with gr.Blocks(
      fill_height=True,
      fill_width=True,
      css="""
  .icon-button-wrapper.top-panel {
      display: none !important;
  }
  .contain { display: flex; flex-direction: column; }
  .gradio-container { height: 100vh !important; }
  #component-0 { height: 100%; }
  #chatbot { flex-grow: 1; overflow: auto;}
  #budget_plot .modebar { display: none !important; }
  .plotly .modebar { display: none !important; }
      """,
    ) as demo:
      with gr.Row(equal_height=True):
        with gr.Column(scale=9):
          gr.Markdown("# 🤖 Autopilot")
        with gr.Column(scale=1):
          reset_btn = gr.Button("Reset", elem_id="reset_button")

      chatbot = AgentChatbot(
        type="messages",
        show_label=False,
        avatar_images=(
          Path(__file__).parent.joinpath("assets/avatars/user.png"),
          Path(__file__).parent.joinpath("assets/avatars/terminal.png"),
          Path(__file__).parent.joinpath("assets/avatars/robot.png"),
        ),
        editable="llm",
        render_markdown=True,
        group_consecutive_messages=False,
        elem_id="chatbot",
      )

      with gr.Row(equal_height=True):
        msg = gr.Textbox(
          show_label=False,
          scale=10,
          placeholder="Enter your message here...",
          elem_id="msg",
        )
        button = gr.Button("Send", elem_id="send_button")
        progress_plot = gr.Plot(
          label="Budget Progress",
          value=self.budget_chart.get_budget_chart(),
          show_label=False,
          elem_id="budget_plot",
        )

      chatbot.edit(
        fn=self.edit_message,
        outputs=[chatbot, progress_plot],
      )

      msg.submit(
        fn=self.add_message,
        inputs=[msg],
        outputs=[msg, chatbot, progress_plot],
      )
      button.click(
        fn=self.add_message,
        inputs=[msg],
        outputs=[msg, chatbot, progress_plot],
      )

      reset_btn.click(
        fn=self.reset,
        inputs=None,
        outputs=[chatbot, progress_plot],
      )
      demo.load(self.load_history, inputs=None, outputs=chatbot)
    return demo

  def start_workflow(self, zmq_port: int):
    # workflow process
    process = Process(
      target=launch_workflow,
      kwargs=dict(
        zmq_port=zmq_port,
        model=self.model,
        sandbox=self.sandbox,
        max_steps=self.max_steps,
        max_current_steps=self.max_current_steps,
        max_time=self.max_time,
        name=self.name,
        task=None,
        log_to_mongodb=self.log_to_mongodb,
        log_to_github=self.log_to_github,
      ),
    )
    process.start()

    # wait for workflow to be ready
    time.sleep(2)
    if self.server is None:
      raise RuntimeError("Server not initialized")
    data = self.server.receive()
    assert data.message_type == MessageType.WORKFLOW_READY
    return process

  def cleanup(self):
    if self._shutdown_initiated:
      # prevent duplicate cleanup
      return

    self._shutdown_initiated = True
    cls_name = self.__class__.__name__
    logger.info(f"{cls_name}: Initiating a graceful shutdown...")

    if self.workflow_process is not None and self.workflow_process.is_alive():
      logger.info(f"{cls_name}: Terminating workflow process...")
      try:
        # Wait with a timeout here, without sending SIGINT explicitly.
        # The workflow process created by `multiprocessing.Process` is in
        # the same process group as the main process, so the SIGINT signal
        # will be delivered to the child process as well.
        # Note that workflow_process is not launched with daemon=True.
        self.workflow_process.join(timeout=5)

        # Force kill if the workflow process still alive
        if self.workflow_process.is_alive():
          logger.warning(
            f"{cls_name}: Workflow process didn't terminate gracefully, "
            "force killing..."
          )
          self.workflow_process.kill()
          self.workflow_process.join()

        self.workflow_process = None
      except Exception as e:
        logger.error(f"{cls_name}: Error terminating workflow process: {e}")

    # shutdown zmq server
    self.kill_zmq_server()

  def launch(self, port: int = 8000, zmq_port: int = 8001, share: bool = False):
    self.zmq_port = zmq_port
    self.launch_zmq_server(zmq_port=self.zmq_port)
    self.workflow_process = self.start_workflow(zmq_port=self.zmq_port)
    demo = self.build_app()
    demo.launch(server_port=port, share=share)


if __name__ == "__main__":
  app = AutopilotGradioApp(
    model="gpt-4o",
    name="gradio-session",
    max_steps=200,
    max_time=600,
    log_to_mongodb=True,
    log_to_github=True,
    sandbox=None,
  )
  app.launch(port=8000, zmq_port=8001, share=False)
