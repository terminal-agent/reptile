"""Unit tests for Gradio CLI functionality."""

import os
import sys
from typing import Callable, Optional

import pytest
from pytest_mock import MockerFixture

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from autopilot.app.gradio.app import AutopilotGradioApp
from autopilot.cli.app import run_gradio_app


@pytest.fixture(scope="function")
def mock_gradio_cls_and_app(
  mocker: MockerFixture,
):
  """Fixture that patches AutopilotGradioApp and returns the mock class and instance."""
  mock_app_class = mocker.patch("autopilot.cli.app.AutopilotGradioApp")
  mock_app_instance = mocker.MagicMock()
  mock_app_class.return_value = mock_app_instance

  return mock_app_class, mock_app_instance


@pytest.fixture(scope="module")
def autopilot_app_factory(
  module_mocker: MockerFixture,
) -> Callable[..., AutopilotGradioApp]:
  # patch attributes or methods at here

  def _factory(
    *,
    log_to_mongodb: bool = False,
    log_to_github: bool = False,
    sandbox: Optional[str] = None,
  ) -> AutopilotGradioApp:
    return AutopilotGradioApp(
      log_to_mongodb=log_to_mongodb,
      log_to_github=log_to_github,
      sandbox=sandbox,
    )

  return _factory


@pytest.fixture(scope="function")
def autopilot_app(autopilot_app_factory) -> AutopilotGradioApp:
  return autopilot_app_factory(
    log_to_mongodb=False, log_to_github=False, sandbox=None
  )


def test_run_gradio_app_with_defaults(
  mock_gradio_cls_and_app: MockerFixture,
):
  """Tests CLI launches app with default parameters."""
  mock_app_class, mock_app_instance = mock_gradio_cls_and_app

  run_gradio_app()

  mock_app_class.assert_called_once_with(
    model=None,
    sandbox=None,
    name="gradio-session",
    max_steps=200,
    max_time=600,
    log_to_mongodb=True,
    log_to_github=True,
  )
  mock_app_instance.launch.assert_called_once_with(port=8000, zmq_port=8001)


def test_run_gradio_app_with_all_params(
  mock_gradio_cls_and_app: MockerFixture,
):
  """Tests CLI with all parameters specified."""
  mock_app_class, mock_app_instance = mock_gradio_cls_and_app

  run_gradio_app(
    port=9000,
    zmq_port=8999,
    model="gpt-4",
    sandbox="docker",
    name="test-session",
    max_steps=100,
    max_time=300,
    log_to_mongodb=False,
    log_to_github=False,
  )

  mock_app_class.assert_called_once_with(
    model="gpt-4",
    sandbox="docker",
    name="test-session",
    max_steps=100,
    max_time=300,
    log_to_mongodb=False,
    log_to_github=False,
  )
  mock_app_instance.launch.assert_called_once_with(port=9000, zmq_port=8999)


def test_run_gradio_app_logging_flags(
  mock_gradio_cls_and_app: MockerFixture,
):
  """Tests CLI logging flag behavior."""
  mock_app_class, _ = mock_gradio_cls_and_app

  # Test --no-log-to-mongodb
  run_gradio_app(log_to_mongodb=False)

  call_kwargs = mock_app_class.call_args.kwargs
  assert call_kwargs["log_to_mongodb"] is False

  # Test --no-log-to-github
  mock_app_class.reset_mock()
  run_gradio_app(log_to_github=False)

  call_kwargs = mock_app_class.call_args.kwargs
  assert call_kwargs["log_to_github"] is False

  # Test both flags disabled
  mock_app_class.reset_mock()
  run_gradio_app(log_to_mongodb=False, log_to_github=False)

  call_kwargs = mock_app_class.call_args.kwargs
  assert call_kwargs["log_to_mongodb"] is False
  assert call_kwargs["log_to_github"] is False


def test_cleanup(autopilot_app: AutopilotGradioApp, mocker: MockerFixture):
  """Tests cleanup process."""
  mock_server = mocker.patch.object(autopilot_app, "server")
  mock_process = mocker.patch.object(autopilot_app, "workflow_process")
  mock_process.is_alive.side_effect = [True, False]

  autopilot_app.cleanup()

  mock_process.join.assert_called_once()
  mock_server.shutdown.assert_called_once()
  assert autopilot_app.workflow_process is None


def test_cleanup_sigint_interrupts(
  autopilot_app: AutopilotGradioApp, mocker: MockerFixture
):
  """Tests cleanup get correctly called on SIGINT."""

  def _cleanup_side_effect():
    autopilot_app._shutdown_initiated = True

  def _raise_sigint(test_msg):
    import signal

    signal.raise_signal(signal.SIGINT)

  # Test a single SIGINT interrupt
  mock_cleanup = mocker.patch.object(
    autopilot_app, "cleanup", side_effect=_cleanup_side_effect
  )
  mocker.patch.object(autopilot_app, "add_message", side_effect=_raise_sigint)
  mock_exit = mocker.patch("autopilot.app.gradio.annotator.sys.exit")

  autopilot_app.add_message("Test message")

  mock_cleanup.assert_called_once()
  mock_exit.assert_called_once_with(0)

  # Test multiple SIGINT interrupts
  mock_cleanup.reset_mock()
  mock_exit.reset_mock()
  autopilot_app._shutdown_initiated = False

  for _ in range(3):
    autopilot_app.add_message("Test message")

  mock_cleanup.assert_called_once()
  mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
  pytest.main([__file__])
