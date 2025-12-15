import os

import yaml
from typer import Typer

from autopilot.config import (
  Config,
  ToolConfig,
  save_config,
  save_template_config,
)
from autopilot.constants import _CONFIG_FILE_PATH
from autopilot.tools.tool import TOOLS

app = Typer()


@app.command(name="view", help="View the existing autopilot coonfig.")
def view() -> None:
  """
  View the existing autopilot config.
  """
  with open(_CONFIG_FILE_PATH, "r") as f:
    print(f.read())


@app.command(name="edit", help="Edit the autopilot config.")
def edit() -> None:
  """
  List the existing autopilot configs.
  """
  default_editor = os.getenv("EDITOR", "vim")
  os.system(f"{default_editor} {_CONFIG_FILE_PATH}")


@app.command(name="init", help="Initialize the autopilot config.")
def init_config() -> None:
  """
  Initialize the autopilot config.
  """
  if _CONFIG_FILE_PATH.exists():
    print(f"Config file already exists at {_CONFIG_FILE_PATH}")
    return
  _CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
  save_template_config(str(_CONFIG_FILE_PATH))
  print(f"Config file created at {_CONFIG_FILE_PATH}")


@app.command(
  name="update",
  help="Update the autopilot config based on the current version's tool list",
)
def update() -> None:
  # check if the config file exists
  if not _CONFIG_FILE_PATH.exists():
    print(
      f"Config file does not exist at {_CONFIG_FILE_PATH}, please use `autopilot config init` to create it first."
    )
    return

  # check if the config is valid
  try:
    with open(_CONFIG_FILE_PATH, "r") as f:
      config = yaml.safe_load(f)
  except yaml.YAMLError as e:
    print(f"Config file is not valid: {e}")
    return

  for name, data in TOOLS.data.items():
    tool_config = ToolConfig(
      name=name, description=data["description"], type="built-in"
    )
    if name in config["tools"]:
      config["tools"][name] = tool_config
    else:
      config["tools"].append(tool_config)

  save_config(Config(**config), str(_CONFIG_FILE_PATH))
