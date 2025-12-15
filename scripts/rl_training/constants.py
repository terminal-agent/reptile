"""Constants for RL training environment configuration.

This module contains default configuration values that can be overridden
via environment variables.
"""

import os
from getpass import getuser
from pathlib import Path

# ============================================================================
# Configuration Constants
# ============================================================================
# Default environment configuration dictionary.
# Can be overridden via environment variables.
import dotenv

path = Path(__file__).parent / ".env"
dotenv.load_dotenv(path)

ENV = {
  # VERL_HOST is the IP of the entrynode.
  # https://docs.sail.insea.io/user-guides/entry-node/
  "VERL_HOST": os.environ.get("VERL_HOST", None),
  "VERL_USER": os.environ.get("VERL_USER", getuser()),
  # Benchmark and evaluation criteria for rollouts and shipping
  "DEFAULT_MODEL_NAME": os.environ.get("DEFAULT_MODEL_NAME", "auto-vllm"),
  "CONFIG_PATH": os.path.expanduser("~/.config/autopilot/config.yaml"),
}

# Default model name identifier.
DEFAULT_MODEL_NAME: str = ENV["DEFAULT_MODEL_NAME"]

# Default path to configuration file.
DEFAULT_CONFIG: str = ENV["CONFIG_PATH"]
