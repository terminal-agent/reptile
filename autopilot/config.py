import re
from typing import Optional

import yaml
from pydantic import BaseModel, ValidationError

from autopilot.constants import _CONFIG_FILE_PATH
from autopilot.utils import console

__all__ = [
  "GLOBAL_CONFIG",
  "save_config",
  "save_template_config",
  "Config",
  "ToolConfig",
  "SessionConfig",
  "LLMCredentials",
  "LLMParameters",
  "LLMConfig",
  "load_config",
]


class LLMCredentials(BaseModel):
  """
  LLMCredentials contains the credentials for the LLM.

  Args:
    api_key (str): the API key for the LLM
    base_url (str): the base URL for the LLM
  """

  api_key: str
  base_url: str


class LLMParameters(BaseModel):
  """
  LLMParameters contains the parameters for the LLM.

  Args:
    model (str): assign a unique name to this model.
  """

  model: str


class LLMConfig(BaseModel):
  """
  LLMConfig contains the configuration for the LLM.

  Args:
    name (str): assign a unique name to this model.
    credentials (LLMCredentials): the credentials for the LLM
    parameters (LLMParameters): the parameters for the LLM
    priority (int): the priority of the model
  """

  name: str
  credentials: LLMCredentials
  parameters: LLMParameters
  priority: int


class ToolConfig(BaseModel):
  """
  ToolConfig contains the configuration for the tool.

  Args:
    name (str): assign a unique name to this tool.
    description (str): the description of the tool
    type (str): the type of the tool, type can either be "built-in" or "external"
    path (Optional[str]): the path to the tool, only used when type is "external"
  """

  name: str
  description: str
  type: str
  path: Optional[str] = None


class SessionConfig(BaseModel):
  """
  SessionConfig contains the configuration for the session.

  Args:
    use_default_bashrc (bool): whether to use the default bashrc file
  """

  use_default_bashrc: bool = False


class MongoDBConfig(BaseModel):
  """
  MongoDBConfig contains the configuration for the MongoDB.

  Args:
    host (str): the host of the MongoDB
    port (int): the port of the MongoDB
    username (str): the username of the MongoDB
    password (str): the password of the MongoDB
    database (str): the name of the MongoDB database
    collection (str): the name of the MongoDB collection
  """

  host: str
  port: int
  username: str
  password: str
  database: str
  collection: str


class GitHubConfig(BaseModel):
  """
  GitHubConfig contains the configuration for the GitHub.

  Args:
    repo_url (str): the URL of the GitHub repository
  """

  repo_url: str


class TelemetryConfig(BaseModel):
  """
  TelemetryConfig contains the configuration for the telemetry.

  Args:
    github (Optional[GitHubConfig]): the configuration for the GitHub
    mongodb (Optional[MongoDBConfig]): the configuration for the MongoDB
  """

  github: Optional[GitHubConfig] = None
  mongodb: Optional[MongoDBConfig] = None


class Config(BaseModel):
  """
  This is the overall configuration for the autopilot.

  Args:
    models (list[LLMConfig]): the configuration for the LLMs
    session (SessionConfig): the configuration for the session
    telemetry (Optional[TelemetryConfig]): the configuration for the telemetry
  """

  models: list[LLMConfig]
  session: SessionConfig
  telemetry: Optional[TelemetryConfig] = None

  def __post_init__(self):
    assert len(self.models) > 0, "At least one model is required"


# ================================
# Template Config
# ================================

_TEMPLATE_CONFIG = Config(
  models=[
    LLMConfig(
      name="deepseek",
      credentials=LLMCredentials(
        api_key="to-be-filled", base_url="https://api.deepseek.com"
      ),
      parameters=LLMParameters(model="deepseek-chat"),
      priority=0,
    ),
    LLMConfig(
      name="gemini-2.0",
      credentials=LLMCredentials(
        api_key="to-be-filled",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
      ),
      parameters=LLMParameters(model="gemini-2.0-flash"),
      priority=0,
    ),
  ],
  session=SessionConfig(
    use_default_bashrc=False,
  ),
  telemetry=TelemetryConfig(
    github=GitHubConfig(
      repo_url="git@github.com:terminal-agents/yaml_data.git"
    ),
    mongodb=MongoDBConfig(
      host="",
      port=27017,
      username="",
      password="",
      database="autopilot",
      collection="autopilot",
    ),
  ),
)


class LineSeprationDumper(yaml.Dumper):
  """
  This is a custom dumper for the YAML file to add line separation between different sections.
  """

  def increase_indent(self, flow=False, indentless=False):
    return super(LineSeprationDumper, self).increase_indent(flow, False)


def save_config(config: Config, path: str) -> None:
  """
  Save the configuration to a YAML file.

  Args:
    config (Config): the configuration to save
    path (str): the path to the YAML file
  """
  with open(path, "w") as f:
    yaml_str = yaml.dump(
      config.model_dump(mode="json"),
      Dumper=LineSeprationDumper,
      sort_keys=False,
      default_flow_style=False,
      indent=2,
    )
    yaml_str_with_spacing = re.sub(r"(?m)^(?!\s|$)", r"\n\g<0>", yaml_str)
    f.write(yaml_str_with_spacing)


def save_template_config(path: str) -> None:
  """
  Save the template configuration to a YAML file.

  Args:
    path (str): the path to the YAML file
  """
  save_config(_TEMPLATE_CONFIG, path)


# ================================
# Load Config
# ================================
def load_config() -> Config:
  """
  Load the configuration from the YAML file in the project configuration directory.

  Returns:
    config (Config): the configuration loaded from the YAML file
  """
  if not _CONFIG_FILE_PATH.exists():
    _CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_template_config(str(_CONFIG_FILE_PATH))
    console.log(
      "Config file not found, created a default config file at",
      _CONFIG_FILE_PATH,
    )
  with open(_CONFIG_FILE_PATH, "r") as f:
    data = yaml.safe_load(f)

  try:
    config = Config(**data)
  except ValidationError:
    raise ValueError(
      f"Your config format is invalid, please check the config file at {_CONFIG_FILE_PATH} and try again."
    )
  return config


GLOBAL_CONFIG = load_config()
