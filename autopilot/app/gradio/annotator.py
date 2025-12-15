import logging
import os
import signal
import sys
import time
from multiprocessing import Process
from pathlib import Path
from typing import Dict, List, Optional

import gradio as gr
from gradio_autopilot_chatbot import AgentChatbot
from gradio_autopilot_chatbot.agentchatbot import Message

from autopilot.app.gradio.budget_chart import BudgetProgressChart
from autopilot.app.gradio.token_budget import TokenBudgetManager
from autopilot.app.gradio.utils import launch_workflow
from autopilot.cli.evaluate import valid_criteria
from autopilot.communication import (
  ZMQMessage,
  ZMQServer,
  get_global_zmq_server,
  init_global_zmq_server,
)
from autopilot.config import GLOBAL_CONFIG
from autopilot.constants import _CACHE_ROOT
from autopilot.data import InteractionMode, MessageType, WorkflowConfig
from autopilot.evaluation.single_eval import run_single_eval
from autopilot.evaluation.tasks import TASKS, Task
from autopilot.hooks import GitHubTelemetryHook, GradioHook, InterruptHook
from autopilot.workflow.autopilot_workflow import AutopilotWorkflow

logger = logging.getLogger(__name__)


class AnnotationGradioApp:
  def __init__(
    self,
    port: int,
    zmq_port: int,
    tasks_dir: Optional[str] = None,
    log_to_mongodb: bool = True,
    log_to_github: bool = True,
  ):
    self.port = port
    self.zmq_port = zmq_port
    self.log_to_mongodb = log_to_mongodb
    self.log_to_github = log_to_github

    # app states
    self.history: List[Message] = []
    self.workflow = None
    self.server: Optional[ZMQServer] = None
    self.current_workflow_process = None
    self.current_task: Optional[Task] = None
    self._shutdown_initiated: bool = False

    # Backend: Token budget management
    self.budget_manager = TokenBudgetManager()

    # Frontend: Budget chart visualization
    self.budget_chart = BudgetProgressChart(
      budget_manager=self.budget_manager,
      chart_size=150,
    )

    if tasks_dir is None:
      self.tasks_dir = Path(__file__).parent.parent.parent.parent.joinpath(
        "external"
      )
    else:
      self.tasks_dir = Path(tasks_dir)
    self.benchmark_tasks = self.get_benchmark_tasks()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, self._sigint_handler)

  def _sigint_handler(self, signum, frame):
    if self._shutdown_initiated:
      return

    self.cleanup()
    sys.exit(0)

  # ==============================
  # Helper Functions
  # ==============================
  def _update_token_budget(self, response: ZMQMessage) -> None:
    """Update token budget from LLM response payload."""
    tokens_used = response.payload["tokens_used"]
    max_content_length = response.payload["max_context_length"]
    # Backend handles all the token budget logic
    self.budget_manager.update_from_llm_response(
      tokens_used, max_content_length
    )

  def get_benchmark_tasks(self) -> Dict[str, List[str]]:
    benchmark_list = TASKS.list_tasks()
    benchmark_list.sort()
    benchmark_tasks = {}
    for benchmark in benchmark_list:
      # all tasks
      task_list = TASKS.get(benchmark).task_names()
      benchmark_tasks[benchmark] = task_list
    return benchmark_tasks

  def get_session_list(self) -> List[str]:
    session_folder = Path(_CACHE_ROOT).joinpath("sessions")
    session_names = [f.name for f in Path(session_folder).glob("*")]
    session_names = ["none"] + session_names
    return session_names

  def get_model_list(self) -> List[str]:
    model_list = [
      (model.name, model.priority) for model in GLOBAL_CONFIG.models
    ]
    model_list.sort(key=lambda x: x[1], reverse=True)
    return [model[0] for model in model_list]

  def _cleanup_current_task(self, task: Optional[Task] = None) -> None:
    # The specified task takes precedence over the current task
    if task is None:
      task = self.current_task

    # Nothing to cleanup if both the specified and the current tasks are None
    if task is None:
      return

    logger.info(f"Cleaning up resources for task {task.name}")
    try:
      task.cleanup_resources()
    except Exception:
      logger.exception(f"Failed to cleanup resources {type(task)}")
    finally:
      self.current_task = None

  def _start_workflow_process(
    self,
    zmq_port: int,
    model: str,
    sandbox: str,
    task: Optional[str] = None,
    reload_session: str = "none",
    reload_trajectory: int = -1,
    reload_step: int = -1,
  ):
    push = True
    name = None
    max_steps = None
    max_current_steps = None
    max_time = None

    # workflow process
    process = Process(
      target=launch_workflow,
      kwargs=dict(
        zmq_port=zmq_port,
        model=model,
        sandbox=sandbox,
        max_steps=max_steps,
        max_current_steps=max_current_steps,
        max_time=max_time,
        name=name,
        task=task,
        log_to_mongodb=self.log_to_mongodb,
        log_to_github=self.log_to_github,
        reload_session=reload_session,
        reload_trajectory=reload_trajectory,
        reload_step=reload_step,
      ),
      daemon=True,
    )
    process.start()

    # wait for workflow to be ready
    time.sleep(2)
    if self.server is None:
      raise RuntimeError("ZMQ server not initialized")
    data = self.server.receive()
    assert data.message_type == MessageType.WORKFLOW_READY
    gr.Info("Workflow is ready")
    return process

  def get_solution(self, benchmark: str, task: str):
    # check if solution.sh exists
    benchmark_tasks_dir = TASKS.get(benchmark).from_name(task, benchmark).dir
    maybe_solution_sh = Path(benchmark_tasks_dir, "solution.sh")
    if maybe_solution_sh.exists():
      with open(maybe_solution_sh, "r") as f:
        solution = f.read()
    else:
      solution = "No solution.sh found"
    return solution

  # ==============================
  # Event Handlers
  # ==============================
  # workflow events
  def load_task_list(self, benchmark: str):
    return gr.Dropdown(
      choices=self.benchmark_tasks[benchmark],
      label="Select a task",
      interactive=True,
    )

  def execute_workflow(
    self,
    benchmark: str,
    task: str,
    reload_session: str,
    reload_trajectory: int,
    reload_step: int,
    model: str,
  ):
    if self.current_workflow_process is not None:
      gr.Info("Terminating previous workflow...")
      self.current_workflow_process.terminate()
      self.current_workflow_process.join(timeout=5)
      self.current_workflow_process = None
      self.history = []
      self.budget_manager.reset()
      self._cleanup_current_task()

    if self.server is not None:
      self.kill_zmq_server()
    self.start_zmq_server()

    # get the task
    gr.Info(f"Launching workflow for {benchmark}/{task}...")
    task_obj = TASKS.get(benchmark).from_name(task, benchmark)

    # launch with try except to cleanup task resources
    try:
      task_obj.launch_container()
    except Exception as e:
      logger.exception(
        f"Failed to launch container for {benchmark}/{task}: {e}"
      )
      self._cleanup_current_task(task_obj)
      return

    self.current_task = task_obj

    process = self._start_workflow_process(
      zmq_port=self.zmq_port,
      model=model,
      sandbox=self.current_task.container_name,
      reload_session=reload_session,
      reload_trajectory=reload_trajectory,
      reload_step=reload_step,
    )

    self.current_workflow_process = process

  def load_solution(self, benchmark: str, task: str):
    # get the solution
    solution = self.get_solution(benchmark, task)
    return solution

  def add_task_instruction(self, benchmark: str, task: str):
    # add the task instruction as user instruction
    task_obj = TASKS.get(benchmark).from_name(task, benchmark)

    self.history = []
    if self.server is None:
      raise RuntimeError("ZMQ server not initialized")
    self.server.send(
      ZMQMessage(
        message_type=MessageType.USER_PROMPT, payload=task_obj.description
      )
    )
    self.history.append(
      Message(name="user", role="user", content=task_obj.description)
    )
    yield self.history, self.budget_chart.get_budget_chart()
    for history, chart in self._receive_messages():
      yield history, chart

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
      elif response.message_type == MessageType.USER_PROMPT:
        if self.history[-1].name == "llm":
          # Display user (hard-rule) feedback after LLM response
          self.history.append(
            Message(name="user", role="user", content=response.payload)
          )
          yield self.history, self.budget_chart.get_budget_chart()
      elif response.message_type == MessageType.WORKFLOW_TURN_END:
        break
      elif response.message_type == MessageType.NO_COMMAND_FOUND:
        gr.Warning("No command found in the LLM response, cannot proceed.")
        break
      else:
        continue

  # chat evetns
  def send_message(self, msg):
    print("sending message: ", msg)
    if self.server is None:
      raise RuntimeError("ZMQ server not initialized")

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

  def edit_message(self, edit_data: gr.EditData):
    if self.server is None:
      raise RuntimeError("ZMQ server not initialized")
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

  def clear_history(self):
    self.history = []
    self.budget_manager.reset()
    return self.history, self.budget_chart.get_budget_chart()

  def run_evaluation(self, eval_criteria: str):
    """Run evaluation on the current task with the specified criteria."""
    if self.current_task is None:
      gr.Warning("No task is currently loaded. Please start a workflow first.")
      return "Error: No task loaded"

    try:
      # Create output directory for evaluation results
      output_dir = Path(_CACHE_ROOT).joinpath("eval_results")
      os.makedirs(output_dir, exist_ok=True)

      gr.Info(
        f"Running {eval_criteria} evaluation for task: {self.current_task.name}"
      )

      # Run the evaluation using run_single_eval with eval_only=True
      success, eval_output_file = run_single_eval(
        task=self.current_task,
        output_dir=str(output_dir),
        eval_criteria=eval_criteria,
        eval_only=True,
      )

      # Read and return the evaluation output
      if os.path.exists(eval_output_file):
        with open(
          eval_output_file, "r", encoding="utf-8", errors="replace"
        ) as f:
          eval_output = f.read()

        if success:
          gr.Info("Evaluation result: Passed!")
        else:
          gr.Warning("Evaluation result: Failed!")

        return eval_output
      else:
        return "Error: Evaluation output file not found"

    except Exception as e:
      logger.exception(f"Error running evaluation: {e}")
      gr.Error(f"Evaluation error: {str(e)}")
      return f"Error: {str(e)}"

  # ==============================
  # UI Components
  # ==============================
  def build_app(self):
    with gr.Blocks(
      fill_height=True,
      fill_width=True,
      css="""
          #budget_plot .modebar { display: none !important; }
          .plotly .modebar { display: none !important; }
      """,
    ) as demo:
      gr.Markdown("# 🤖 Autopilot Annotator")

      # ==============================
      # Configuration Section
      # ==============================
      with gr.Row(equal_height=True):
        with gr.Sidebar():
          gr.Markdown("**Benchmark Selection**")

          with gr.Row(equal_height=True):
            benchmark_dropdown = gr.Dropdown(
              value="",
              choices=list(self.benchmark_tasks.keys()),
              label="Select a benchmark",
              elem_id="benchmark_dropdown",
            )
            task_dropdown = gr.Dropdown(
              value="",
              label="Select a task",
              elem_id="task_dropdown",
            )

          gr.Markdown("**Reload options**")
          with gr.Row(equal_height=True):
            session_dropdown = gr.Dropdown(
              choices=self.get_session_list(),
              label="Select a session",
              interactive=True,
              elem_id="session_dropdown",
            )
            reload_trajectory = gr.Number(
              value=-1,
              label="Trajectory",
              interactive=True,
              elem_id="reload_trajectory",
            )
            reload_step = gr.Number(
              value=-1,
              label="Step",
              interactive=True,
              elem_id="reload_step",
            )

          gr.Markdown("**Others**")
          model_dropdown = gr.Dropdown(
            choices=self.get_model_list(),
            label="Select a model",
            interactive=True,
            elem_id="model_dropdown",
          )
          start_workflow_button = gr.Button(
            "Start Workflow", elem_id="start_workflow_button"
          )

          # ==============================
          # Evaluation section
          # ==============================
          gr.Markdown("## 🔍 Evaluation")
          eval_criteria_dropdown = gr.Dropdown(
            choices=valid_criteria,
            value="rule-based",
            label="Evaluation Criteria",
            interactive=True,
            elem_id="eval_criteria_dropdown",
          )
          evaluation_output = gr.TextArea(
            label="Unit Test Output",
            elem_id="evaluation_output",
          )
          test_button = gr.Button("Run Unit Test", elem_id="test_button")

          # ==============================
          # Solution section
          # ==============================
          gr.Markdown("## 📝 Solution")
          with gr.Accordion(
            label="Solution",
            elem_id="solution_accordion",
            open=False,
          ):
            solution = gr.TextArea(
              interactive=False,
              elem_id="solution",
              show_label=False,
              container=False,
            )
        with gr.Column():
          # ==============================
          # Chatbot section
          # ==============================
          gr.Markdown("## 💬 Chatbot")
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
            height="65vh",
          )
          with gr.Row(
            equal_height=True, min_height=self.budget_chart.chart_size
          ):
            msg = gr.Textbox(
              show_label=False,
              scale=10,
              placeholder="Enter your message here...",
              interactive=True,
              elem_id="msg",
            )
            button = gr.Button("Send", elem_id="send_button")
            progress_plot = gr.Plot(
              value=self.budget_chart.get_budget_chart(),
              show_label=False,
              elem_id="budget_plot",
              container=False,
            )

      # ==============================
      # Workflow Events handlers
      # ==============================
      benchmark_dropdown.change(
        fn=self.load_task_list,
        inputs=[benchmark_dropdown],
        outputs=[task_dropdown],
        concurrency_limit=1,
        concurrency_id="global_queue",
      )

      start_workflow_button.click(
        fn=self.execute_workflow,
        inputs=[
          benchmark_dropdown,
          task_dropdown,
          session_dropdown,
          reload_trajectory,
          reload_step,
          model_dropdown,
        ],
        outputs=None,
        concurrency_id="global_queue",
      ).then(
        fn=self.load_solution,
        inputs=[benchmark_dropdown, task_dropdown],
        outputs=[solution],
        concurrency_id="global_queue",
      ).then(
        self.add_task_instruction,
        inputs=[benchmark_dropdown, task_dropdown],
        outputs=[chatbot, progress_plot],
        concurrency_id="global_queue",
      )

      test_button.click(
        fn=self.run_evaluation,
        inputs=[eval_criteria_dropdown],
        outputs=[evaluation_output],
        concurrency_id="global_queue",
      )

      chatbot.edit(
        fn=self.edit_message,
        outputs=[chatbot, progress_plot],
        concurrency_id="global_queue",
      )
      msg.submit(
        fn=self.send_message,
        inputs=[msg],
        outputs=[msg, chatbot, progress_plot],
        concurrency_id="global_queue",
      )
      button.click(
        fn=self.send_message,
        inputs=[msg],
        outputs=[msg, chatbot, progress_plot],
        concurrency_id="global_queue",
      )

      demo.load(
        self.clear_history, inputs=None, outputs=[chatbot, progress_plot]
      )
    return demo

  def start_zmq_server(self):
    print(f"Launching ZMQ server at {self.zmq_port}...")
    init_global_zmq_server(port=self.zmq_port)
    print("ZMQ server launched.")
    self.server = get_global_zmq_server()

  def kill_zmq_server(self):
    if self.server is not None:
      self.server.shutdown()
      self.server = None

  def cleanup(self):
    if self._shutdown_initiated:
      # prevent duplicate cleanup
      return

    self._shutdown_initiated = True
    cls_name = self.__class__.__name__
    logger.info(f"{cls_name}: Initiating a graceful shutdown...")

    # terminate workflow process
    if (
      self.current_workflow_process is not None
      and self.current_workflow_process.is_alive()
    ):
      logger.info(f"{cls_name}: Terminating workflow process...")
      self.current_workflow_process.terminate()
      self.current_workflow_process.join(timeout=5)
      if self.current_workflow_process.is_alive():
        logger.warning(
          f"{cls_name}: Workflow process didn't terminate gracefully, "
          "force killing..."
        )
        self.current_workflow_process.kill()
        self.current_workflow_process.join()
      self.current_workflow_process = None

    # cleanup task container resources
    self._cleanup_current_task()

    # shutdown zmq server
    self.kill_zmq_server()

  def launch(self):
    demo = self.build_app()
    demo.launch(server_port=self.port)


if "GRADIO_WATCH_DIRS" in os.environ:
  # for debug purposes
  app = AnnotationGradioApp(port=12000, zmq_port=8459)
  demo = app.build_app()
  demo.launch(server_port=12000)
