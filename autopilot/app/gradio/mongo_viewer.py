import os
from copy import deepcopy
from pathlib import Path

import gradio as gr
from gradio_autopilot_chatbot import AgentChatbot
from pymongo import MongoClient

from autopilot.config import GLOBAL_CONFIG


class MongoViewer:
  def __init__(self):
    if (
      GLOBAL_CONFIG.telemetry is None or GLOBAL_CONFIG.telemetry.mongodb is None
    ):
      raise ValueError(
        "Telemetry or MongoDB is not configured in the config file"
      )
    self.mongo_url = f"mongodb://{GLOBAL_CONFIG.telemetry.mongodb.username}:{GLOBAL_CONFIG.telemetry.mongodb.password}@{GLOBAL_CONFIG.telemetry.mongodb.host}:{GLOBAL_CONFIG.telemetry.mongodb.port}"
    self.client = MongoClient(self.mongo_url)
    self.db = self.client[GLOBAL_CONFIG.telemetry.mongodb.database]
    self.collection = self.db[GLOBAL_CONFIG.telemetry.mongodb.collection]
    self.history = []
    self.page_size = 20

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
        """,
    ) as demo:
      gr.Markdown("# 🤖 MongoDB Data Viewer")

      gr.Markdown("## Session Selector")
      with gr.Row(equal_height=True):
        page_number = gr.Dropdown(
          label="Page Number",
          choices=range(self.get_num_pages()),
          value=0,
          interactive=True,
        )
        session_name = gr.Dropdown(
          label="Session Name",
          choices=self.get_data_by_page(0),
          interactive=True,
        )
        load_button = gr.Button("Load Session")

      gr.Markdown("## Chat Trajectory")

      with gr.Row(equal_height=True):
        user_name = gr.Label(
          label="User Name",
        )
        model_name = gr.Label(label="Model Name")

        traject_choice = gr.Dropdown(
          label="Traject Choice",
          value=0,
          interactive=True,
        )
      chatbot = AgentChatbot(
        type="messages",
        show_label=False,
        avatar_images=(
          Path(__file__).parent.joinpath("assets/avatars/user.png"),
          Path(__file__).parent.joinpath("assets/avatars/terminal.png"),
          Path(__file__).parent.joinpath("assets/avatars/robot.png"),
        ),
        editable=None,
        render_markdown=True,
        group_consecutive_messages=False,
        elem_id="chatbot",
      )

      load_button.click(
        fn=self.load_data,
        inputs=session_name,
        outputs=[user_name, model_name, traject_choice, chatbot],
      )

      traject_choice.change(
        fn=self.history_to_trajectory,
        inputs=traject_choice,
        outputs=chatbot,
      )

      page_number.change(
        fn=self.get_data_by_page,
        inputs=page_number,
        outputs=session_name,
      )

    return demo

  def launch(self, port: int = 8000, share: bool = False):
    demo = self.build_app()
    demo.launch(server_port=port, share=share)

  def load_data(self, session_name):
    data = self.collection.find_one({"session_name": session_name})

    history = data["chat_history"]
    model_name = data["model_name"]
    user_name = data["username"]
    num_trajectories = history[-1]["traj"] + 1 if history else 0
    self.history = history
    trajectory = self.history_to_trajectory(0)

    # trajectory dropdown
    trajectory_dropdown = gr.Dropdown(
      label="Trajectory",
      choices=range(num_trajectories),
      value=0,
      interactive=True,
    )

    return (
      user_name,
      model_name,
      trajectory_dropdown,
      trajectory,
    )

  def history_to_trajectory(self, trajectory: int):
    selected_history: list[dict] = []
    current_trajectory = -1

    for message in self.history:
      if message["traj"] > trajectory:
        break
      if message["traj"] > current_trajectory:
        step = message["step"]
        selected_history = selected_history[:step]

      current_trajectory = message["traj"]
      message = deepcopy(message)
      if message["name"] == "terminal":
        message["role"] = "assistant"
      selected_history.append(message)
    return selected_history

  def get_total_number_of_data(self):
    return self.collection.count_documents({})

  def get_num_pages(self):
    return self.get_total_number_of_data() // self.page_size + 1

  def get_data_by_range(self, start, end):
    return self.collection.find().sort("_id", 1).skip(start).limit(end - start)

  def get_data_by_page(self, page_number):
    start = page_number * self.page_size
    end = start + self.page_size
    return [data["session_name"] for data in self.get_data_by_range(start, end)]


if "GRADIO_WATCH_DIRS" in os.environ:
  # for debug purposes
  viewer = MongoViewer()
  demo = viewer.build_app()
  demo.launch()
