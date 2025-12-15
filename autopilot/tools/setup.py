import os
from typing import List

from setuptools import setup

script_dir = os.path.dirname(os.path.abspath(__file__))


def find_requirements(requirement_files: List[str]) -> list[str]:
  requirements = []
  for requirement_file in requirement_files:
    with open(requirement_file, "r") as f:
      requirements.extend(
        [line.strip() for line in f.read().splitlines() if line.strip()]
      )
  return list(set(requirements))


parent_dir = os.path.join(script_dir, "../")

setup(
  name="autopilot_tools",
  package_dir={"": parent_dir},
  packages=["tools"],
  install_requires=find_requirements([f"{script_dir}/requirements.txt"]),
  entry_points={
    "console_scripts": [
      "calculator = tools.calculator:CalculatorCLI.run",
      "browser = tools.browser_use:BrowserUseCLI.run",
      "replace = tools.replace:ReplaceTool.run",
      "url2md = tools.url2md:Url2Md.run",
      "grep-tree = tools.grep_tree:GrepTreeTool.run",
      "inspect = tools.inspect_pycode:ASTInspectorCLI.run",
    ]
  },
  python_requires=">=3.11",
)
