import os
import subprocess
import sys
from typing import Callable

import pytest
from pytest_mock import MockerFixture

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from autopilot.app.gradio.annotator import AnnotationGradioApp


@pytest.fixture(scope="function")
def mock_config(mocker: MockerFixture):
  mock = mocker.patch("autopilot.app.gradio.annotator.GLOBAL_CONFIG")
  mock.models = [
    mocker.MagicMock(name="gpt-4", priority=1),
    mocker.MagicMock(name="claude-3", priority=2),
  ]
  return mock


@pytest.fixture(scope="function")
def mock_tasks(mocker: MockerFixture):
  mock = mocker.patch("autopilot.app.gradio.annotator.TASKS")
  mock.list_tasks.return_value = ["benchmark1", "benchmark2"]
  mock.get.return_value.task_names.return_value = ["task1", "task2"]
  return mock


@pytest.fixture(scope="module")
def annotator_app_factory(
  module_mocker: MockerFixture,
) -> Callable[..., AnnotationGradioApp]:
  """Pytest fixture to mock dependencies and instantiate AnnotationGradioApp."""
  # mock config
  mock_config = module_mocker.patch(
    "autopilot.app.gradio.annotator.GLOBAL_CONFIG"
  )
  mock_config.models = [
    module_mocker.MagicMock(name="gpt-4", priority=1),
    module_mocker.MagicMock(name="claude-3", priority=2),
  ]

  # mock tasks
  mock_tasks = module_mocker.patch("autopilot.app.gradio.annotator.TASKS")
  mock_tasks.list_tasks.return_value = ["benchmark1", "benchmark2"]
  mock_tasks.get.return_value.task_names.return_value = ["task1", "task2"]

  # mock path
  mock_path = module_mocker.patch("autopilot.app.gradio.annotator.Path")
  # Path() -> .joinpath() -> .glob() -> return_value=[]
  mock_path.return_value.joinpath.return_value.glob.return_value = []

  def _factory(
    *, port: int = 12000, zmq_port: int = 8459
  ) -> AnnotationGradioApp:
    return AnnotationGradioApp(port=port, zmq_port=zmq_port)

  return _factory


@pytest.fixture(scope="function")
def annotator_app(annotator_app_factory) -> AnnotationGradioApp:
  return annotator_app_factory(port=12000, zmq_port=8459)


def test_annotation_app_initialization(annotator_app: AnnotationGradioApp):
  """Tests AnnotationGradioApp initialization."""
  assert annotator_app.port == 12000
  assert annotator_app.zmq_port == 8459
  assert annotator_app.history == []
  assert annotator_app.workflow is None
  assert annotator_app.server is None
  assert annotator_app.current_workflow_process is None


def test_get_benchmark_tasks(annotator_app: AnnotationGradioApp):
  """Tests getting benchmark tasks from TASKS."""
  result = annotator_app.get_benchmark_tasks()

  expected = {
    "benchmark1": ["task1", "task2"],
    "benchmark2": ["task1", "task2"],
  }
  assert result == expected


def test_load_task_list(
  annotator_app: AnnotationGradioApp, mocker: MockerFixture
):
  """Tests loading task list for a benchmark."""
  annotator_app.benchmark_tasks = {
    "benchmark1": ["task1", "task2", "task3"],
    "benchmark2": ["task4", "task5"],
  }

  mock_gr = mocker.patch("autopilot.app.gradio.annotator.gr")
  mock_dropdown = mocker.MagicMock()
  mock_gr.Dropdown.return_value = mock_dropdown

  result = annotator_app.load_task_list("benchmark1")

  mock_gr.Dropdown.assert_called_once_with(
    choices=["task1", "task2", "task3"],
    label="Select a task",
    interactive=True,
  )
  assert result is mock_dropdown


def test_get_solution_from_sh_file(
  annotator_app: AnnotationGradioApp, mocker: MockerFixture
):
  """Tests getting solution from solution.sh file."""
  mocker.patch.object(
    annotator_app,
    "get_solution",
    return_value="#!/bin/bash\necho 'Hello World'",
  )
  result = annotator_app.get_solution("benchmark1", "task1")
  assert result == "#!/bin/bash\necho 'Hello World'"


def test_get_solution_no_file_found(
  annotator_app: AnnotationGradioApp, mocker: MockerFixture
):
  """Tests getting solution when no solution file exists."""
  mocker.patch.object(
    annotator_app,
    "get_solution",
    return_value="No solution.sh or solution.md found",
  )
  result = annotator_app.get_solution("benchmark1", "task1")
  assert result == "No solution.sh or solution.md found"


def test_execute_workflow(
  annotator_app: AnnotationGradioApp,
  mocker: MockerFixture,
  mock_tasks: MockerFixture,
):
  """Tests executing workflow with task parameters."""
  mocker.patch("autopilot.app.gradio.annotator.gr")
  mock_start = mocker.patch.object(annotator_app, "_start_workflow_process")

  mock_task_obj = mocker.MagicMock()
  mock_task_obj.container_name = "test_container"
  mock_tasks.get.return_value.from_name.return_value = mock_task_obj

  mock_process = mocker.MagicMock()
  mock_start.return_value = mock_process

  annotator_app.execute_workflow(
    benchmark="benchmark1",
    task="task1",
    reload_session="none",
    reload_trajectory=-1,
    reload_step=-1,
    model="gpt-4",
  )

  mock_task_obj.launch_container.assert_called_once()
  mock_start.assert_called_once_with(
    zmq_port=annotator_app.zmq_port,
    model="gpt-4",
    sandbox="test_container",
    reload_session="none",
    reload_trajectory=-1,
    reload_step=-1,
  )
  assert annotator_app.current_workflow_process is mock_process


def test_start_zmq_server(
  annotator_app: AnnotationGradioApp, mocker: MockerFixture
):
  """Tests starting ZMQ server."""
  mock_get_server = mocker.patch(
    "autopilot.app.gradio.annotator.get_global_zmq_server"
  )
  mock_init_server = mocker.patch(
    "autopilot.app.gradio.annotator.init_global_zmq_server"
  )
  mock_server = mocker.MagicMock()
  mock_get_server.return_value = mock_server

  annotator_app.start_zmq_server()

  mock_init_server.assert_called_once_with(port=annotator_app.zmq_port)
  mock_get_server.assert_called_once()

  assert annotator_app.server is mock_server


def test_launch(annotator_app: AnnotationGradioApp, mocker: MockerFixture):
  """Tests launching the Gradio app."""
  mock_gr = mocker.patch("autopilot.app.gradio.annotator.gr")
  mock_demo = mocker.MagicMock()
  mock_gr.Blocks.return_value.__enter__.return_value = mock_demo

  mocker.patch.object(annotator_app, "start_zmq_server")
  mocker.patch.object(annotator_app, "build_app", return_value=mock_demo)

  annotator_app.launch()

  mock_demo.launch.assert_called_once_with(server_port=annotator_app.port)


def test_cleanup(annotator_app: AnnotationGradioApp, mocker: MockerFixture):
  """Tests cleanup process."""
  mocker.patch.object(annotator_app, "_shutdown_initiated", False)
  mock_task = mocker.patch.object(annotator_app, "current_task")
  mock_zmq_server = mocker.patch.object(annotator_app, "server")
  mock_process = mocker.patch.object(annotator_app, "current_workflow_process")
  mock_process.is_alive.side_effect = [True, False]

  annotator_app.cleanup()

  mock_task.cleanup_resources.assert_called_once()
  mock_process.terminate.assert_called_once()
  mock_process.join.assert_called_once()
  mock_process.kill.assert_not_called()
  mock_zmq_server.shutdown.assert_called_once()
  assert annotator_app.current_workflow_process is None

  # Test ungraceful shutdown for workflow process
  mocker.patch.object(annotator_app, "_shutdown_initiated", False)
  mock_task = mocker.patch.object(annotator_app, "current_task")
  mock_zmq_server = mocker.patch.object(annotator_app, "server")
  mock_process = mocker.patch.object(annotator_app, "current_workflow_process")
  mock_process.is_alive.side_effect = [True, True]

  annotator_app.cleanup()

  mock_task.cleanup_resources.assert_called_once()
  mock_process.kill.assert_called_once()
  mock_zmq_server.shutdown.assert_called_once()
  assert annotator_app.current_workflow_process is None


def test_cleanup_sigint_interrupts(
  annotator_app: AnnotationGradioApp, mocker: MockerFixture
):
  """Tests cleanup get correctly called on SIGINT."""

  def _cleanup_side_effect():
    annotator_app._shutdown_initiated = True

  def _raise_sigint(test_msg):
    import signal

    signal.raise_signal(signal.SIGINT)

  # Test a single SIGINT interrupt
  mock_cleanup = mocker.patch.object(
    annotator_app, "cleanup", side_effect=_cleanup_side_effect
  )
  mocker.patch.object(annotator_app, "send_message", side_effect=_raise_sigint)
  mock_exit = mocker.patch("autopilot.app.gradio.annotator.sys.exit")

  annotator_app.send_message("Test message")

  mock_cleanup.assert_called_once()
  mock_exit.assert_called_once_with(0)

  # Test multiple SIGINT interrupts
  mock_cleanup.reset_mock()
  mock_exit.reset_mock()
  annotator_app._shutdown_initiated = False

  for _ in range(3):
    annotator_app.send_message("Test message")

  mock_cleanup.assert_called_once()
  mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
  pytest.main([__file__])
