import os
import subprocess
import sys
import tempfile


def create_test_file(content: str) -> str:
  """Create temporary Python file"""
  with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
    f.write(content)
    return f.name


def test_cli_basic():
  """Test basic CLI functionality"""
  test_code = '''class TestClass:
    """Test docstring"""

    @property
    def test_method(self):
        """Method docstring"""
        pass
'''

  temp_file = create_test_file(test_code)
  try:
    result = subprocess.run(
      ["inspect", temp_file], capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0
    assert "class TestClass" in result.stdout
    assert "function TestClass.test_method" in result.stdout
    assert "decorator: @property" in result.stdout

  finally:
    os.unlink(temp_file)


def test_cli_help():
  """Test help command"""
  result = subprocess.run(
    ["inspect", "--help"], capture_output=True, text=True, timeout=10
  )

  assert result.returncode == 0
  assert "inspect" in result.stdout.lower()


def test_cli_errors():
  """Test error handling"""
  # Non-existent file
  result = subprocess.run(
    ["inspect", "nonexistent.py"], capture_output=True, text=True, timeout=10
  )
  assert "does not exist" in result.stdout

  # No arguments
  result = subprocess.run(
    ["inspect"], capture_output=True, text=True, timeout=10
  )
  assert result.returncode != 0


def test_module_import():
  """Test module can be imported"""
  result = subprocess.run(
    [
      sys.executable,
      "-c",
      "from autopilot.tools.inspect_pycode import ASTInspectorCLI",
    ],
    capture_output=True,
    text=True,
    timeout=5,
  )
  assert result.returncode == 0


def test_async_functions():
  """Test async function detection"""
  test_code = '''async def async_func():
    """Async function"""
    pass
'''

  temp_file = create_test_file(test_code)
  try:
    result = subprocess.run(
      ["inspect", temp_file], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert "function async_func" in result.stdout
  finally:
    os.unlink(temp_file)


def test_nested_classes():
  """Test nested class definitions"""
  test_code = '''class Outer:
    """Outer class"""

    class Inner:
        """Inner class"""
        pass
'''

  temp_file = create_test_file(test_code)
  try:
    result = subprocess.run(
      ["inspect", temp_file], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert "class Outer" in result.stdout
    assert "class Outer.Inner" in result.stdout
  finally:
    os.unlink(temp_file)


def test_decorators():
  """Test function decorators"""
  test_code = '''@decorator1
@decorator2
def decorated_func():
    """Decorated function"""
    pass
'''

  temp_file = create_test_file(test_code)
  try:
    result = subprocess.run(
      ["inspect", temp_file], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert "@decorator1 @decorator2" in result.stdout
  finally:
    os.unlink(temp_file)


def test_empty_file():
  """Test empty Python file"""
  test_code = """# Empty file
"""

  temp_file = create_test_file(test_code)
  try:
    result = subprocess.run(
      ["inspect", temp_file], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert "No class or function definitions found" in result.stdout
  finally:
    os.unlink(temp_file)
