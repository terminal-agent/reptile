from pathlib import Path

_HOME = Path.home()

# config-related
_CONFIG_ROOT = _HOME.joinpath(".config/autopilot")
_CONFIG_FILE_PATH = _CONFIG_ROOT.joinpath("config.yaml")

# sandbox-related
_IMAGE_NAME = "autopilot"

# session-related
_CACHE_ROOT = _HOME.joinpath(".cache/autopilot")
_SCRATCHPAD_ROOT = _HOME.joinpath(".cache/autopilot-scratchpad")
_DEFAULT_MAX_TOKENS = 163840
