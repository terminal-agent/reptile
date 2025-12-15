#!/usr/bin/env python3
"""
Script to extract succeed tasks from batch_results.csv and add them to swegym_valid_tasks.txt
"""

import csv
import os
from pathlib import Path


def main():
  # Get the script directory
  script_dir = Path(__file__).parent

  # Paths
  csv_path = (
    script_dir.parent.parent / "results_swegym_oracle" / "batch_results.csv"
  )
  tasks_file_path = script_dir / "swegym_valid_tasks.txt"

  # Read CSV and extract succeed tasks
  succeed_tasks = []
  if not csv_path.exists():
    print(f"Error: {csv_path} not found")
    return

  with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
      if row["Status"].strip() == "Succeed":
        task_name = row["Task"].strip()
        if task_name:
          succeed_tasks.append(task_name)

  with open(tasks_file_path, "w", encoding="utf-8") as f:
    for task in sorted(succeed_tasks):
      f.write(f"{task}\n")

  print(f"Added {len(succeed_tasks)} new succeed tasks to {tasks_file_path}")


if __name__ == "__main__":
  main()
