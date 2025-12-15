import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import List, Optional, Tuple

from autopilot.evaluation.tasks import Task
from autopilot.utils import console


def run_swebench_eval(
  task: Task,
  output_dir: str,
  session_name: str,
) -> Tuple[bool, str]:
  """run swe-bench evaluation for patch.txt.

  Return True or False if the patch.txt is valid. If not, return False and the error message.
  """

  session_dir = os.path.join(output_dir, session_name)
  patch_txt_path = os.path.join(session_dir, "patch.txt")
  eval_output_file = os.path.join(session_dir, "eval_output.txt")

  if not os.path.exists(patch_txt_path):
    with open(eval_output_file, "w") as f:
      f.write("No patch file found")
    return False, eval_output_file

  instance_id = task.name
  model_name = "Default"
  try:
    with open(patch_txt_path, "r", encoding="utf-8") as f:
      patch_content = f.read()
  except UnicodeDecodeError:
    try:
      with open(patch_txt_path, "r", encoding="latin-1") as f:
        patch_content = f.read()
    except UnicodeDecodeError:
      with open(patch_txt_path, "r", encoding="cp1252") as f:
        patch_content = f.read()

  predictions = [
    {
      "instance_id": instance_id,
      "model_name_or_path": model_name,
      "model_patch": patch_content,
    }
  ]

  with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    json.dump(predictions, f, indent=2)
    predictions_path = f.name

  try:
    if task.benchmark in ["swebench_verified", "swebench_verified_focus"]:
      dataset_name = "SWE-bench"
      split = "test"
      _args = {
        "namespace": "swebench",
        "rewrite_reports": False,
        "modal": False,
      }
      # Import the main function for swebench_verified (using swebench-fork)
      from swebench.harness.run_evaluation import main as run_evaluation_main
    elif task.benchmark in ["swegym"]:
      dataset_name = "SWE-Gym/SWE-Gym"
      split = "train"
      _args = {}
      # switch to swegym-forked-swebench
      submodule_path = (
        Path(__file__).parent.parent.parent / "external" / "swebench-fork"
      )
      submodule_path_str = str(submodule_path)
      if submodule_path_str not in sys.path:
        sys.path.insert(0, submodule_path_str)
        console.print(f"Switched to swegym-forked-swebench")
      # Import the main function after switching the path
      from swebench.harness.run_evaluation import main as run_evaluation_main
    else:
      raise ValueError(f"Unsupported benchmark: {task.benchmark}")

    # Suppress tqdm and other progress bar output
    old_tqdm_disable = os.environ.get("TQDM_DISABLE")
    os.environ["TQDM_DISABLE"] = "1"

    # Redirect both stdout and stderr to suppress evaluation progress bars
    with open(os.devnull, "w") as devnull:
      with redirect_stdout(devnull), redirect_stderr(devnull):
        # Temporarily replace sys.stdout and sys.stderr to ensure complete suppression
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
          report_file_path = run_evaluation_main(
            dataset_name=dataset_name,
            split=split,
            instance_ids=[instance_id],
            predictions_path=predictions_path,
            max_workers=1,
            force_rebuild=False,
            cache_level="env",
            clean=True,
            open_file_limit=4096,
            run_id=f"eval_{session_name}",
            timeout=1800,
            **_args,
          )
        finally:
          sys.stdout = old_stdout
          sys.stderr = old_stderr
          # Restore TQDM_DISABLE environment variable
          if old_tqdm_disable is None:
            os.environ.pop("TQDM_DISABLE", None)
          else:
            os.environ["TQDM_DISABLE"] = old_tqdm_disable

    # Move the report file to session_dir if it's not already there
    if not os.path.dirname(report_file_path) == session_dir:
      report_filename = os.path.basename(report_file_path)
      # move the report file to session_dir
      target_report_path = os.path.join(session_dir, report_filename)
      shutil.move(report_file_path, target_report_path)
      # move the logs to session_dir
      report_logs = os.path.join(
        report_file_path.parent,
        "logs",
        "run_evaluation",
        f"eval_{session_name}",
        model_name,
        instance_id,
      )
      shutil.move(report_logs, os.path.join(session_dir, "logs"))

    with open(target_report_path, "r") as f:
      eval_result = json.load(f)
    if eval_result.get("resolved_instances", 0) == 1:
      success = True
    else:
      success = False

    with open(eval_output_file, "w") as f:
      f.write("Evaluation completed successfully using main function\n")
      f.write(f"Instance ID: {instance_id}\n")
      f.write(f"Run ID: eval_{session_name}\n")
      f.write(f"Result: {success}\n")
      f.write("=" * 50 + "\n")
      f.write(f"Evaluation log:\n")
      f.write(json.dumps(eval_result, indent=2))

  except Exception as e:
    with open(eval_output_file, "w") as f:
      f.write(f"Evaluation failed: {str(e)}")
    success = False
  return success, eval_output_file


if __name__ == "__main__":
  from autopilot.evaluation.tasks import SWEBenchVerifiedTask, SWEGymTask

  # task = SWEBenchVerifiedTask(name="pydata__xarray-3095")
  # run_swebench_eval(task, "output", "pydata__xarray-3095_test")

  task = SWEGymTask(name="pandas-dev__pandas-47504")
  run_swebench_eval(task, "output", "pandas-dev__pandas-47504_test")
