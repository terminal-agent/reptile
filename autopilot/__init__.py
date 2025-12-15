import os

from .utils import check_system_commands_exist
from .version import __version__

# disable telemetry for browser use
os.environ["ANONYMIZED_TELEMETRY"] = "false"


check_system_commands_exist()
