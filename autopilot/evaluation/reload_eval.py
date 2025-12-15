import re
from pathlib import Path
from typing import Dict, List

import yaml

from autopilot.utils import extract_commands


def reload_eval_fn(
  completion_steps: List[Dict],
  reload: str,
  reload_eval: str,
  eval_output_file: Path,
):
  from .batch_eval import PROJECT_DIR

  reload_eval_path = PROJECT_DIR / reload_eval

  if reload_eval_path.exists() and reload_eval_path.suffix in (".yml", ".yaml"):
    with open(reload_eval_path, "r") as f:
      reload_eval_yml = yaml.safe_load(f)

    try:
      requirements = reload_eval_yml[reload]
    except KeyError:
      with open(eval_output_file, "at") as f:
        f.write(
          f"Reload evaluation requirements for {reload} not found in {reload_eval}\n"
        )
      raise KeyError(
        f"Reload evaluation requirements for {reload} not found in {reload_eval}"
      )

    try:
      success = True
      llm_outputs = [
        step["content"] for step in completion_steps if step["role"] == "llm"
      ]
      # llm_outputs[0], currently only extract the first LLM output step
      commands = extract_commands(llm_outputs[0])
      with open(eval_output_file, "at") as f:
        if len(commands) > 1:
          f.write("Multiple commands found in LLM output\n")
          success = False
        elif len(commands) == 0:
          f.write("No commands found in LLM output\n")
          success = False
        else:
          required_satisfied = (
            False if requirements["required"] else True
          )  # no required patterns, so it's always satisfied

          # Handle required regex patterns (OR logic - any one satisfied is OK)
          for pattern in requirements["required"]:
            if re.search(pattern, commands[0][1], re.DOTALL):
              required_satisfied = True
              break

          if not required_satisfied:
            f.write("No required regex patterns matched\n")
            success = False
          else:
            f.write("Required regex patterns matched\n")

          # Handle forbidden regex patterns (AND logic - any one found is an error)
          for pattern in requirements["forbidden"]:
            if re.search(pattern, commands[0][1], re.DOTALL):
              f.write("Forbidden regex pattern matched: `{}`\n".format(pattern))
              success = False

    # IndexError: completion_steps == [] or no code block in LLMs' output
    except IndexError:
      with open(eval_output_file, "at") as f:
        f.write("LLM output in wrong format or empty.\n")
      success = False

    if success:
      with open(eval_output_file, "at") as f:
        f.write("Tests passed!\n")

    return success, eval_output_file

  else:
    with open(eval_output_file, "at") as f:
      f.write(
        f"Reload evaluation file {reload_eval} not found or unsupported format.\n"
      )
    raise FileNotFoundError(
      f"Reload evaluation file {reload_eval} not found or unsupported format."
    )
