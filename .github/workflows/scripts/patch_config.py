import os

from autopilot.config import load_config, save_config
from autopilot.constants import _CONFIG_FILE_PATH


def main():
  config = load_config()

  config.models[0].credentials.api_key = os.getenv("LLM_API_KEY")
  config.models[0].credentials.base_url = os.getenv("LLM_BASE_URL")
  config.models[0].parameters.model = os.getenv("LLM_MODEL_NAME")
  config.models[0].priority = 10
  config.telemetry.github.repo_url = ""
  save_config(config, _CONFIG_FILE_PATH)


if __name__ == "__main__":
  main()
