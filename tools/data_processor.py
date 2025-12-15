import argparse
import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import git
from rich.console import Console

console = Console()

repo_path = os.path.expanduser("~/.cache/terminal-agent/data")


def process_data() -> Dict[str, List[List[Tuple[str, str]]]]:
  """
  Iterates through all branches, converts files into a list of [(role, content), ...],
  and returns a list of prefixes that satisfy the specified conditions.
  """
  try:
    repo = git.Repo(repo_path)
    repo.remote().fetch()
  except Exception as e:
    console.log(f"Error initializing or fetching repo: {e}")
    return {}

  ret = {}
  # when branches have the same prefix, keep only the one with the highest index
  branches = [branch.name.split("/")[-1] for branch in repo.remote().refs]
  branch_versions: Dict[str, int] = defaultdict(int)
  for branch in branches:
    try:
      prefix, index_str = branch.rsplit("-", 1)
      index = int(index_str)
    except Exception:
      # Ignore branches that don't match the expected pattern
      console.log(f"Branch {branch} ignored.")
      continue
    if index > branch_versions[prefix]:
      branch_versions[prefix] = index
  branches = [f"{k}-{v}" for k, v in branch_versions.items()]

  for branch in branches:
    try:
      # Extract the actual branch name from the remote ref
      repo.git.checkout(branch, force=True)  # Checkout branch

      file_list = get_file_list()
      data = []

      if "system_prompt.txt" in file_list:
        with open(os.path.join(repo_path, "system_prompt.txt"), "rt") as f:
          system_prompt = f.read()
        data.append(("system", system_prompt))

      for filename in file_list:
        filepath = os.path.join(repo_path, filename)
        with open(filepath, "rt") as f:
          text = f.read()
          role, content = text.split("\n", 1)
          data.append((role, content))

      branch_data = get_prefixes(data)
      ret[branch] = branch_data
      if len(branch_data) > 0:
        console.log(f"Gathered {len(branch_data)} data from branch: {branch}")

    except Exception as e:
      console.log(f"Error processing branch {branch}: {e}")
      continue

  return ret


def get_file_list() -> List[str]:
  """Get the list of files in the current branch."""
  files = set()
  for item in os.listdir(repo_path):
    item_path = os.path.join(repo_path, item)
    if os.path.isfile(item_path):
      files.add(item)
  i = 0
  ordered_files = []
  while f"{i}.txt" in files:
    ordered_files.append(f"{i}.txt")
    i += 1
  return ordered_files


def get_prefixes(data: List[Tuple[str, str]]) -> List[List[Tuple[str, str]]]:
  """
  Walks through the list of (role, content) tuples and returns a list of prefixes
  that satisfy the specified conditions.
  """
  prefixes = []
  for i, (role, content) in enumerate(data):
    if i == 0:
      continue
    if role == "user":
      # when the previous llm round has no code, it means that
      # this user round is not triggered by ctrl-c
      if i > 0 and data[i - 1][0] == "llm" and "```" not in data[i - 1][1]:
        continue
      for j in range(i + 1, len(data)):
        if data[j][0] == "llm":
          prefixes.append(data[: i + 1] + [data[j]])
          break
  return prefixes


def write_json(filepath: str, data: List[Tuple[str, str]]) -> None:
  """Writes data to a JSON file."""

  def normalize_role(role):
    if role == "user":
      return "user"
    elif role == "llm":
      return "assistant"
    elif role == "terminal":
      return "user"
    else:
      return role

  json_data = [
    {"role": normalize_role(role), "content": content} for role, content in data
  ]
  with open(filepath, "wt") as f:
    json.dump(json_data, f, indent=2)


def write_markdown(filepath: str, data: List[Tuple[str, str]]) -> None:
  """Writes data to a Markdown file."""
  texts = []
  for i, (role, content) in enumerate(data):
    if role == "user":
      texts.append(f"# * Step {i}")
    else:
      texts.append(f"# Step {i}")
    if role == "llm":
      texts.append(content)
    else:
      texts.append(f"```text\n{content}\n```")
  content_str = "\n".join(texts)
  with open(filepath, "wt") as f:
    f.write(content_str)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    description="Process data and output prefixes to files."
  )
  parser.add_argument(
    "--output_dir",
    type=str,
    default="output",
    help="The directory to output the files to.",
  )
  parser.add_argument(
    "--output_format",
    type=str,
    choices=["json", "md"],
    default="json",
    help="The format to output the files in (json or md).",
  )
  args = parser.parse_args()

  output_dir = args.output_dir
  output_format = args.output_format

  if not os.path.exists(output_dir):
    os.makedirs(output_dir)

  prefixes = process_data()

  for name, items in prefixes.items():
    # Extract branch name from the first element of the prefix
    for item in items:
      filename = f"{name}-{len(item)}.{output_format}"
      filepath = os.path.join(output_dir, filename)
      if output_format == "json":
        write_json(filepath, item)
      elif output_format == "md":
        write_markdown(filepath, item)
      console.log(f"Wrote prefix to {filepath}")
