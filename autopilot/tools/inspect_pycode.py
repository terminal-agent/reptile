import ast
from pathlib import Path

import typer
from typing_extensions import Annotated

from .tool import TOOLS, CLITool


class BlockVisitor(ast.NodeVisitor):
  """AST visitor that records all class and function definitions with line numbers."""

  def __init__(self):
    self.stack = []
    self.results = []

  def _get_decorators_and_docstring(self, node):
    # decorators: list of (text, lineno)
    decorators = [
      (ast.unparse(dec), getattr(dec, "lineno", getattr(node, "lineno", 1)))
      for dec in getattr(node, "decorator_list", [])
    ]
    # robust docstring extraction (supports ast.Str / ast.Constant(str))
    docstring = ast.get_docstring(node)
    docstring_lineno = None
    if getattr(node, "body", None) and isinstance(node.body[0], ast.Expr):
      v = node.body[0].value
      if isinstance(v, ast.Str) or (
        isinstance(v, ast.Constant) and isinstance(v.value, str)
      ):
        docstring_lineno = getattr(node.body[0], "lineno", None)
    return decorators, docstring, docstring_lineno

  def visit_ClassDef(self, node):
    name = ".".join(self.stack + [node.name])
    decorators, docstring, _ = self._get_decorators_and_docstring(node)
    # start from first decorator if present, else class line
    if decorators:
      start_lineno = min(dec_lineno for _, dec_lineno in decorators)
    else:
      start_lineno = node.lineno
    end_lineno = node.end_lineno
    self.results.append(
      {
        "type": "class",
        "name": name,
        "start": start_lineno,
        "end": end_lineno,
        "decorators": [dec for dec, _ in decorators],
        "docstring": docstring,
      }
    )
    self.stack.append(node.name)
    self.generic_visit(node)
    self.stack.pop()

  def _visit_func(self, node):
    name = ".".join(self.stack + [node.name])
    decorators, docstring, _ = self._get_decorators_and_docstring(node)
    # start from first decorator if present, else def line
    if decorators:
      start_lineno = min(dec_lineno for _, dec_lineno in decorators)
    else:
      start_lineno = node.lineno
    end_lineno = node.end_lineno
    self.results.append(
      {
        "type": "function",
        "name": name,
        "start": start_lineno,
        "end": end_lineno,
        "decorators": [dec for dec, _ in decorators],
        "docstring": docstring,
      }
    )
    self.stack.append(node.name)
    self.generic_visit(node)
    self.stack.pop()

  def visit_FunctionDef(self, node):
    self._visit_func(node)

  def visit_AsyncFunctionDef(self, node):
    self._visit_func(node)


@TOOLS.register
class ASTInspectorCLI(CLITool):
  name: str = "inspect"
  description: str = """
  Analyze Python file to list all class and function definitions,
  with their start and end line numbers.

  Example:
    inspect your_file.py

  Output format:
    function my_func  line 1-6
      function my_func decorator: @dec1 @dec2
      function my_func docstring: Example docstring...
  """

  def inspect(
    self, filepath: Annotated[str, typer.Argument(help="Path to Python file")]
  ) -> str:
    """Analyze the file and print class/function definitions with line numbers."""
    file = Path(filepath)
    if not file.exists():
      print(f"[ERROR] File {filepath} does not exist.")
      return ""

    if file.is_dir():
      print(f"[ERROR] {filepath} is a directory, not a file.")
      return ""

    if file.suffix != ".py":
      print(f"[ERROR] {filepath} is not a Python file.")
      return ""

    try:
      with file.open("r", encoding="utf-8") as f:
        content = f.read()
    except UnicodeDecodeError:
      print(f"[ERROR] Failed to read file {filepath}: UnicodeDecodeError")
      return ""
    except SyntaxError:
      print(f"[ERROR] Failed to read file {filepath}: SyntaxError")
      return ""
    except Exception as e:
      print(f"[ERROR] Failed to read file {filepath}: {e}")
      return ""

    try:
      tree = ast.parse(content, filename=filepath)
    except Exception as e:
      print(f"[ERROR] Failed to AST parse {filepath}: {e}")
      return ""

    visitor = BlockVisitor()
    visitor.visit(tree)

    if not visitor.results:
      print(f"No class or function definitions found in {filepath}")
      return ""

    for item in visitor.results:
      decorators = item.get("decorators", [])
      docstring = item.get("docstring", "")

      # Skip items that have neither decorators nor docstring
      if not decorators and not docstring:
        continue

      indent = "  " * item["name"].count(".")
      print(
        f"{indent}{item['type']} {item['name']}  line {item['start']}-{item['end']}"
      )
      if decorators:
        print(
          f"{indent}  {item['type']} {item['name']} decorator: {' '.join('@' + d for d in decorators)}"
        )
      if docstring:
        one_line = docstring.replace("\n", "\\n")
        max_len = 100
        if len(one_line) > max_len:
          folded = len(one_line) - max_len
          shown = one_line[:max_len] + "…"
          # sed command: unquoted range, quoted filepath (handles spaces)
          print(
            f'{indent}  {item["type"]} {item["name"]} docstring: {shown} (+{folded} chars folded; use: sed -n {item["start"]},{item["end"]}p "{filepath}")'
          )
        else:
          print(
            f"{indent}  {item['type']} {item['name']} docstring: {one_line}"
          )

    return ""

  def register(self):
    self.app.command(help="Inspect class/function structure of a Python file")(
      self.inspect
    )
