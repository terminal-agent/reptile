import csv
import os
from pathlib import Path
from typing import cast

from rich.table import Table

from autopilot.utils import console, execute_cmd


def generate_report(
  output_dir: str,
  results: list[tuple[str, str, str, str, str]],
) -> None:
  """
  Generate a summary table and CSV report for batch evaluation results.
  Args:
      output_dir (str): Directory to save the report.
      results (list): List of (task_name, model, status, session_name, reload_arg) tuples.
  """
  if not results:
    return

  successful_tasks = sum(
    1 for _, _, status, _, _ in results if "Succeed" in status
  )

  table = Table(title="Batch Evaluation Results")
  table.add_column("Task", style="cyan")
  table.add_column("Model", style="magenta")
  table.add_column("Status", style="green")
  table.add_column("Session", style="cyan")
  table.add_column("ReloadArg", style="cyan")

  csv_data = [["Task", "Model", "Status", "Session", "ReloadArgument"]]
  for task_name, model, status, session_name, reload_arg in results:
    table.add_row(task_name, model, status, session_name, reload_arg)
    csv_data.append([task_name, model, status, session_name, reload_arg])
  csv_file = os.path.join(output_dir, "batch_results.csv")

  console.print(table)
  console.print(
    f"\nSummary: {successful_tasks}/{len(results)} tasks completed successfully"
  )

  with open(csv_file, "w", newline="") as f:
    csv.writer(f).writerows(csv_data)
  console.print(f"Results saved to {csv_file}")


def generate_token_report(workspace):
  """
  Generate a token usage report for a given workspace.
  Args:
      workspace (str): Path to the workspace directory.
  """
  project_dir = Path(__file__).parent.parent.parent
  try:
    token_report = execute_cmd(
      [
        "python",
        os.path.join(project_dir, "tools", "token_reporter.py"),
        workspace,
      ]
    )
    console.print(token_report, markup=False)
  except Exception as e:
    console.print(
      f"[yellow]Failed to generate token report: {e}[/yellow]", markup=False
    )
