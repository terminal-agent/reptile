"""Unit tests for MongoViewer Gradio app functionality."""

import os
import sys
from typing import Callable

import pytest
from pytest_mock import MockerFixture

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from autopilot.app.gradio.mongo_viewer import MongoViewer


@pytest.fixture(scope="module")
def mongo_viewer_factory(
  module_mocker: MockerFixture,
) -> Callable[..., MongoViewer]:
  module_mocker.patch("autopilot.app.gradio.mongo_viewer.MongoClient")

  mock_config = module_mocker.patch(
    "autopilot.app.gradio.mongo_viewer.GLOBAL_CONFIG"
  )
  mock_config.telemetry.mongodb.username = "test_user"
  mock_config.telemetry.mongodb.password = "test_pass"
  mock_config.telemetry.mongodb.host = "localhost"
  mock_config.telemetry.mongodb.port = 27017
  mock_config.telemetry.mongodb.database = "test_db"
  mock_config.telemetry.mongodb.collection = "test_collection"

  def _factory() -> MongoViewer:
    return MongoViewer()

  return _factory


@pytest.fixture(scope="function")
def mongo_viewer(mongo_viewer_factory) -> MongoViewer:
  return mongo_viewer_factory()


def test_mongo_viewer_initialization(mongo_viewer: MongoViewer):
  """Tests MongoViewer initialization with proper MongoDB connection."""
  assert mongo_viewer.history == []
  assert mongo_viewer.page_size == 20


def test_get_total_number_of_data(
  mongo_viewer: MongoViewer, mocker: MockerFixture
):
  """Tests getting total number of documents in collection."""
  mock_count = mocker.MagicMock(return_value=100)
  mongo_viewer.collection.count_documents = mock_count

  result = mongo_viewer.get_total_number_of_data()

  mock_count.assert_called_once_with({})
  assert result == 100


def test_get_num_pages(mongo_viewer: MongoViewer, mocker: MockerFixture):
  """Tests calculating number of pages based on total data."""
  mocker.patch.object(
    mongo_viewer, "get_total_number_of_data", return_value=100
  )
  result = mongo_viewer.get_num_pages()
  assert result == 6  # 100 // 20 + 1 = 6


def test_get_data_by_page(mongo_viewer: MongoViewer, mocker: MockerFixture):
  """Tests getting session names for a specific page."""
  mock_data = [
    {"session_name": "session1"},
    {"session_name": "session2"},
    {"session_name": "session3"},
  ]

  mocker.patch.object(mongo_viewer, "get_data_by_range", return_value=mock_data)
  result = mongo_viewer.get_data_by_page(0)

  expected_session_names = ["session1", "session2", "session3"]
  assert result == expected_session_names


def test_load_data(mongo_viewer: MongoViewer, mocker: MockerFixture):
  """Tests loading session data from MongoDB."""
  mock_data = {
    "session_name": "test_session",
    "chat_history": [
      {
        "name": "user",
        "role": "user",
        "content": "Hello",
        "traj": 0,
        "step": 0,
      },
      {
        "name": "terminal",
        "role": "assistant",
        "content": "Hi",
        "traj": 0,
        "step": 1,
      },
    ],
    "model_name": "gpt-4",
    "username": "test_user",
  }

  mongo_viewer.collection.find_one.return_value = mock_data

  mocker.patch.object(mongo_viewer, "history_to_trajectory", return_value=[])
  mock_gr = mocker.patch("autopilot.app.gradio.mongo_viewer.gr")

  result = mongo_viewer.load_data("test_session")

  mongo_viewer.collection.find_one.assert_called_once_with(
    {"session_name": "test_session"}
  )

  # Verify returned values
  user_name, model_name, trajectory_dropdown, trajectory = result
  assert user_name == "test_user"
  assert model_name == "gpt-4"
  mock_gr.Dropdown.assert_called_once()


def test_history_to_trajectory(mongo_viewer: MongoViewer):
  """Tests converting history to trajectory format."""
  mongo_viewer.history = [
    {
      "name": "user",
      "role": "user",
      "content": "Hello",
      "traj": 0,
      "step": 0,
    },
    {
      "name": "terminal",
      "role": "assistant",
      "content": "Hi",
      "traj": 0,
      "step": 1,
    },
    {
      "name": "user",
      "role": "user",
      "content": "How are you?",
      "traj": 1,
      "step": 0,
    },
  ]

  result = mongo_viewer.history_to_trajectory(0)
  assert len(result) == 2
  assert result[0]["content"] == "Hello"
  assert result[1]["content"] == "Hi"


def test_history_to_trajectory_with_higher_trajectory(
  mongo_viewer: MongoViewer,
):
  """Tests trajectory conversion with higher trajectory number."""
  mongo_viewer.history = [
    {
      "name": "user",
      "role": "user",
      "content": "Hello",
      "traj": 0,
      "step": 0,
    },
    {
      "name": "terminal",
      "role": "assistant",
      "content": "Hi",
      "traj": 0,
      "step": 1,
    },
    {
      "name": "user",
      "role": "user",
      "content": "How are you?",
      "traj": 1,
      "step": 0,
    },
  ]

  result = mongo_viewer.history_to_trajectory(1)
  assert len(result) == 1
  assert result[0]["content"] == "How are you?"


def test_build_app(mongo_viewer: MongoViewer, mocker: MockerFixture):
  """Tests building the Gradio app interface."""
  mock_gr = mocker.patch("autopilot.app.gradio.mongo_viewer.gr")
  mock_demo = mocker.MagicMock()
  mock_gr.Blocks.return_value.__enter__.return_value = mock_demo

  mocker.patch.object(mongo_viewer, "get_num_pages", return_value=5)
  mocker.patch.object(
    mongo_viewer, "get_data_by_page", return_value=["session1", "session2"]
  )

  result = mongo_viewer.build_app()

  # Verify that Gradio components are created
  mock_gr.Blocks.assert_called_once()
  mock_gr.Markdown.assert_called()
  mock_gr.Dropdown.assert_called()
  mock_gr.Button.assert_called()


def test_launch(mongo_viewer: MongoViewer, mocker: MockerFixture):
  """Tests launching the Gradio app."""
  mock_gr = mocker.patch("autopilot.app.gradio.mongo_viewer.gr")
  mock_demo = mocker.MagicMock()
  mock_gr.Blocks.return_value.__enter__.return_value = mock_demo

  mocker.patch.object(mongo_viewer, "build_app", return_value=mock_demo)
  mongo_viewer.launch(port=9000, share=True)

  mock_demo.launch.assert_called_once_with(server_port=9000, share=True)


if __name__ == "__main__":
  pytest.main([__file__])
