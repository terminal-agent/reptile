import os
import subprocess
import tempfile


def create_test_file(content: str) -> str:
  """Create temporary file with content"""
  with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write(content)
    return f.name


def test_replace_basic():
  """Test basic replace functionality"""
  content = "Hello world! This is a test."
  temp_file = create_test_file(content)

  try:
    result = subprocess.run(
      ["replace", temp_file, "world", "universe"],
      capture_output=True,
      text=True,
      timeout=10,
    )

    assert result.returncode == 0
    assert "Replaced successfully" in result.stdout

    # Verify file content was changed
    with open(temp_file, "r") as f:
      new_content = f.read()
    assert "Hello universe! This is a test." == new_content

  finally:
    os.unlink(temp_file)


def test_replace_multiline():
  """Test replace with multiline text"""
  content = """def old_function():
    return "old"

def other_function():
    return "other"
"""

  original = """def old_function():
    return "old"
"""

  replacement = """def new_function():
    return "new"
"""

  temp_file = create_test_file(content)

  try:
    result = subprocess.run(
      ["replace", temp_file, original, replacement],
      capture_output=True,
      text=True,
      timeout=10,
    )

    assert result.returncode == 0
    assert "Replaced successfully" in result.stdout

    # Verify replacement
    with open(temp_file, "r") as f:
      new_content = f.read()
    assert "def new_function():" in new_content
    assert "def old_function():" not in new_content

  finally:
    os.unlink(temp_file)


def test_replace_not_found():
  """Test when original text is not found"""
  content = "Hello world!"
  temp_file = create_test_file(content)

  try:
    result = subprocess.run(
      ["replace", temp_file, "nonexistent", "replacement"],
      capture_output=True,
      text=True,
      timeout=10,
    )

    assert result.returncode == 1
    assert "Original text not found in file" in result.stdout

    # File should be unchanged
    with open(temp_file, "r") as f:
      unchanged_content = f.read()
    assert unchanged_content == content

  finally:
    os.unlink(temp_file)


def test_replace_multiple_occurrences():
  """Test when original text appears multiple times"""
  content = "test test test"
  temp_file = create_test_file(content)

  try:
    result = subprocess.run(
      ["replace", temp_file, "test", "replacement"],
      capture_output=True,
      text=True,
      timeout=10,
    )

    assert result.returncode == 1
    assert "Original text appears more than once in the file" in result.stdout

    # File should be unchanged
    with open(temp_file, "r") as f:
      unchanged_content = f.read()
    assert unchanged_content == content

  finally:
    os.unlink(temp_file)


def test_replace_file_not_found():
  """Test when file doesn't exist"""
  result = subprocess.run(
    ["replace", "nonexistent.txt", "old", "new"],
    capture_output=True,
    text=True,
    timeout=10,
  )

  assert result.returncode == 1
  assert "File not found: nonexistent.txt" in result.stdout


def test_replace_wrong_args():
  """Test with wrong number of arguments"""
  # Too few arguments
  result = subprocess.run(
    ["replace", "file.txt"], capture_output=True, text=True, timeout=10
  )

  assert result.returncode == 1
  assert (
    "Usage: replace <filename> <original_text> <replace_text>" in result.stdout
  )

  # Too many arguments
  result = subprocess.run(
    ["replace", "file.txt", "old", "new", "extra"],
    capture_output=True,
    text=True,
    timeout=10,
  )

  assert result.returncode == 1
  assert (
    "Usage: replace <filename> <original_text> <replace_text>" in result.stdout
  )


def test_replace_empty_strings():
  """Test replace with empty strings"""
  content = "Hello world!"
  temp_file = create_test_file(content)

  try:
    # Replace with empty string (deletion)
    result = subprocess.run(
      ["replace", temp_file, " world", ""],
      capture_output=True,
      text=True,
      timeout=10,
    )

    assert result.returncode == 0
    assert "Replaced successfully" in result.stdout

    with open(temp_file, "r") as f:
      new_content = f.read()
    assert new_content == "Hello!"

  finally:
    os.unlink(temp_file)
