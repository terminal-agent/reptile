import os
import sys

from autopilot.utils import execute_cmd


def build_tools_wheel():
  import getpass

  username = getpass.getuser()
  wheel_path = (
    f"/tmp/autopilot_tools_{username}/autopilot_tools-0.0.0-py3-none-any.whl"
  )
  project_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
  execute_cmd(["make", "-C", project_dir, "wheel"])
  return wheel_path


def cp_to_container(container, src, dst):
  execute_cmd(["docker", "cp", src, f"{container}:{dst}"])


def install_binaries(container):
  arch = execute_cmd(["docker", "exec", container, "uname", "-m"])
  arch = arch.strip(" \r\n\t")
  script_dir = os.path.dirname(os.path.abspath(__file__))
  binary_dir = os.path.join(script_dir, "../binaries", arch)

  def cp(src, dst):
    cp_to_container(container, src, dst)

  try:
    execute_cmd(["docker", "exec", container, "which", "ps"])
  except Exception:
    cp(os.path.join(binary_dir, "bin", "ps"), "/usr/bin/")
    cp(os.path.join(binary_dir, "lib", "libprocps.so.6"), "/usr/lib/")
    cp(os.path.join(binary_dir, "lib", "libprocps.so.6.0.0"), "/usr/lib/")

  cp(os.path.join(binary_dir, "bin", "uv"), "/usr/bin/")
