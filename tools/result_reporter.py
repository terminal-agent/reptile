"""Merge CSV results files into model comparison format.

This module provides functionality to merge multiple CSV result files
from different models into a single comparison table.
"""

import argparse
import os
import re
from pathlib import Path
from typing import List

import pandas as pd


def extract_model_name_from_path(file_path: str) -> str:
  """Extract model name from file path.

  Args:
      file_path: Path to the CSV file.

  Returns:
      Extracted model name from directory name.
  """
  # Extract directory name as model name
  parent_dir = Path(file_path).parent.name

  # If parent directory is 'results', try to extract from results_xxx pattern
  if parent_dir == "results":
    match = re.search(r"results_([^/]+)", file_path)
    if match:
      return match.group(1)
    return "baseline"  # Default name for base results directory

  # Use directory name as model name, remove 'results_' prefix if exists
  if parent_dir.startswith("results_"):
    return parent_dir[8:]  # Remove 'results_' prefix

  return parent_dir


def validate_csv_file(file_path: str) -> bool:
  """Validate if CSV file has required columns.

  Args:
      file_path: Path to the CSV file.

  Returns:
      True if file is valid, False otherwise.
  """
  try:
    df = pd.read_csv(file_path)
    required_columns = {"Task", "Status", "Session"}
    return required_columns.issubset(df.columns)
  except Exception:
    return False


def merge_csv_files_comparison(
  input_files: List[str], output_file: str
) -> None:
  """Merge multiple CSV files into a model comparison table.

  Creates a comparison table where:
  - Each row represents a task
  - Each column (except first) represents a model's performance on that task
  - First column is 'Task', subsequent columns are model names

  Args:
      input_files: List of input CSV file paths.
      output_file: Output CSV file path.

  Raises:
      ValueError: If no files were successfully read or required columns are missing.
  """
  all_data = []

  for file_path in input_files:
    if not os.path.exists(file_path):
      print(f"Warning: File {file_path} does not exist, skipping")
      continue

    if not validate_csv_file(file_path):
      print(
        f"Warning: File {file_path} missing required columns (Task, Status, Session), skipping"
      )
      continue

    try:
      df = pd.read_csv(file_path)
      model_name = extract_model_name_from_path(file_path)

      # Keep only Task and Status columns, add Model column
      df_clean = df[["Task", "Status"]].copy()
      df_clean["Model"] = model_name
      all_data.append(df_clean)

      print(
        f"Successfully read file: {file_path} ({len(df_clean)} rows) - Model: {model_name}"
      )
    except Exception as e:
      print(f"Error: Cannot read file {file_path}: {e}")
      continue

  if not all_data:
    raise ValueError("No files were successfully read")

  # Combine all data
  combined_df = pd.concat(all_data, ignore_index=True)

  # Create pivot table: rows=Task, columns=Model, values=Status
  pivot_df = combined_df.pivot_table(
    index="Task",
    columns="Model",
    values="Status",
    aggfunc="first",  # Handle duplicates by taking first occurrence
    fill_value="N/A",
  )

  # Reset index to make Task a regular column (first column)
  pivot_df = pivot_df.reset_index()
  pivot_df.columns.name = None  # Remove the 'Model' label from column headers

  # Save results
  pivot_df.to_csv(output_file, index=False)

  # Display summary
  _display_merge_summary(pivot_df, output_file)


def _display_merge_summary(pivot_df: pd.DataFrame, output_file: str) -> None:
  """Display merge operation summary statistics.

  Args:
      pivot_df: The merged pivot DataFrame.
      output_file: Output file path.
  """
  model_columns = [col for col in pivot_df.columns if col != "Task"]

  print(
    f"\nComparison completed! {len(pivot_df)} tasks compared across {len(model_columns)} models"
  )
  print(f"Results saved to: {output_file}")

  print(f"\nSummary:")
  print(f"Total tasks: {len(pivot_df)}")
  print(f"Models compared: {len(model_columns)}")
  print(f"Models: {', '.join(model_columns)}")

  print(f"\nStatus distribution by model:")
  for model in model_columns:
    status_counts = pivot_df[model].value_counts()
    print(f"\n{model}:")
    for status, count in status_counts.items():
      if status != "N/A":
        print(f"  {status}: {count}")


def collect_input_files(
  input_paths: List[str], pattern: str = "batch_results.csv"
) -> List[str]:
  """Collect input files from paths (files or directories).

  Args:
      input_paths: List of file or directory paths.
      pattern: Filename pattern to search in directories.

  Returns:
      List of valid input file paths.
  """
  input_files = []

  for path in input_paths:
    if os.path.isfile(path):
      input_files.append(path)
    elif os.path.isdir(path):
      # Search for pattern in directory
      pattern_files = list(Path(path).glob(pattern))
      input_files.extend(str(f) for f in pattern_files)
    else:
      print(f"Warning: Path {path} is neither file nor directory")

  return input_files


def main() -> None:
  """Main function to parse arguments and execute merge operation."""
  parser = argparse.ArgumentParser(
    description="Merge CSV results files into model comparison format"
  )
  parser.add_argument(
    "input_files", nargs="+", help="Input CSV file paths or directories"
  )
  parser.add_argument(
    "-o", "--output", required=True, help="Output CSV file path"
  )
  parser.add_argument(
    "--pattern",
    default="batch_results.csv",
    help="Filename pattern to search in directories (default: batch_results.csv)",
  )

  args = parser.parse_args()

  # Collect input files
  input_files = collect_input_files(args.input_files, args.pattern)

  if not input_files:
    print("Error: No valid input files found")
    return

  try:
    merge_csv_files_comparison(input_files, args.output)
  except ValueError as e:
    print(f"Error: {e}")


if __name__ == "__main__":
  main()
