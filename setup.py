import os
from typing import List

from setuptools import find_packages, setup


def find_requirements(requirement_files: List[str]) -> list[str]:
  requirements = []
  for requirement_file in requirement_files:
    with open(requirement_file, "r") as f:
      requirements.extend(
        [line.strip() for line in f.read().splitlines() if line.strip()]
      )
  return list(set(requirements))


def find_version(version_file: str) -> str:
  with open(version_file, "r") as f:
    return f.read().strip()


def write_version(version: str) -> str:
  setup_file_path = os.path.abspath(__file__)
  version_py_path = os.path.join(
    os.path.dirname(setup_file_path), "autopilot", "version.py"
  )

  with open(version_py_path, "w") as f:
    f.write(f"__version__ = '{version}'\n")
  return version


version_number = find_version("version.txt")
write_version(version_number)

setup(
  name="autopilot",
  version=version_number,
  packages=find_packages(),
  install_requires=(
    find_requirements(
      [
        "requirements.txt",
        "autopilot/tools/requirements.txt",
      ]
    )
  ),
  extras_require={
    "dev": find_requirements(
      [
        "requirements-dev.txt",
      ]
    ),
  },
  entry_points={
    "console_scripts": [
      "autopilot = autopilot.cli.cli:app",
      "calculator = autopilot.tools.calculator:CalculatorCLI.run",
      "browser = autopilot.tools.browser_use:BrowserUseCLI.run",
      "replace = autopilot.tools.replace:ReplaceTool.run",
      "url2md = autopilot.tools.url2md:Url2Md.run",
      "grep-tree = autopilot.tools.grep_tree:GrepTreeTool.run",
      "inspect = autopilot.tools.inspect_pycode:ASTInspectorCLI.run",
      "ask_google_ai = autopilot.tools.ask_gemini:AskGeminiCLI.run",
      "ask_deepseek = autopilot.tools.ask_deepseek:AskDeepseekCLI.run",
    ]
  },
  package_data={
    "autopilot": ["binaries/**/*", "llm/*.md"],
    "autopilot.tools": ["Makefile", "requirements.txt"],
    "autopilot.terminal": ["default_bashrc"],
    "autopilot.context": ["credentials/*"],
  },
  python_requires=">=3.11",
)
