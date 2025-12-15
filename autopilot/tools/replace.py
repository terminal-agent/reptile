import sys

from .tool import TOOLS


# NOTE: `ReplaceTool` does not inherit from CLITool on purpose,
@TOOLS.register  # type: ignore[arg-type]
class ReplaceTool:  # type: ignore[type-var]
  name = "replace"
  description = """
  Replace content in a file from command line arguments.

  Usage:
    ```sh
    read -r -d '' original <<'EOF'
    <original_text>
    EOF

    read -r -d '' replace <<'EOF'
    <replace_text>
    EOF

    replace <filename> "$original" "$replace"
    ```
"""

  def register(self):
    pass

  @classmethod
  def run(cls):
    if len(sys.argv) != 4:
      print("Usage: replace <filename> <original_text> <replace_text>")
      sys.exit(1)
    filename, original, replace = sys.argv[1:]
    try:
      with open(filename, "rt") as file:
        content = file.read()
    except FileNotFoundError:
      print(f"File not found: {filename}")
      sys.exit(1)
    except Exception as e:
      print(f"Error reading file: {e}")
      sys.exit(1)

    count = content.count(original)
    if count == 0:
      print("Original text not found in file")
      sys.exit(1)
    elif count > 1:
      print("Original text appears more than once in the file")
      sys.exit(1)
    content = content.replace(original, replace)
    with open(filename, "wt") as file:
      file.write(content)
    print("Replaced successfully")
