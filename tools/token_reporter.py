import os
import sys

import tiktoken
import yaml
from rich import box
from rich.console import Console
from rich.table import Table


def count_tokens(text: str, model: str = "gpt-4") -> int:
  ## TODO: use the tokenizer model
  encoding = tiktoken.encoding_for_model(model)
  return len(encoding.encode(text, disallowed_special=()))


def analyze_tokens(workspace_path):
  console = Console()

  table = Table(
    title="Token Usage Per Turn",
    box=box.ROUNDED,
    show_header=True,
    header_style="bold magenta",
  )

  table.add_column("Turn", justify="right", style="cyan")
  table.add_column("Name", style="green")
  table.add_column("Role", style="green")
  table.add_column("Tokens", justify="right", style="blue")
  table.add_column("Content Preview", style="yellow")

  total_tokens = 0
  with open(os.path.join(workspace_path, "history.yml"), "r") as f:
    history = yaml.safe_load(f)

  for i, item in enumerate(history):
    message, role = item["content"], item["role"]
    name = item["name"]
    if "edit_prefix" in item["extra_info"]:
      name = "llm,amend"
    step = str(item["step"])
    tokens = count_tokens(message)
    total_tokens += tokens
    preview = (message[:47] + "...") if len(message) > 50 else message
    preview = preview.replace("\n", " ")
    table.add_row(step, name, role, str(tokens), preview)

  table.add_row(
    "Total",
    "",
    "",
    str(total_tokens),
    f"Total messages: {len(history)}",
    style="bold",
  )

  console.print("\n[bold]Token Usage Analysis[/bold]")
  console.print(table)


if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: token_reporter.py <workspace_path>")
    sys.exit(1)

  analyze_tokens(sys.argv[1])
