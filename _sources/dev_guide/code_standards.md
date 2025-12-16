# Code Standards

This document outlines the coding standards and best practices for the Terminal Agent project. All contributors must follow these guidelines to maintain code quality and consistency.

## Documentation Requirements

All public classes, methods, and functions must include docstrings (Some of the class and method documentation to be fixed).

```python
class CalculatorCLI(CLITool):
  """A simple calculator tool for mathematical expressions."""

  def compute(
    self,
    expression: Annotated[str, typer.Argument(help="The computation expression")]
  ) -> int | float:
    """
    Compute a mathematical expression and return the result.

    Args:
      expression: Mathematical expression as a string (e.g., "2 + 3")

    Returns:
      The computed result as int or float
    """
    ret = eval(expression)
    print(ret)
    return float(ret)
```


## Type Annotations

All function parameters and return values must have type annotations:

### Basic Type Annotations

```python
from typing_extensions import Annotated
import typer

def inspect(
  self,
  filepath: Annotated[str, typer.Argument(help="Path to Python file")]
) -> str:
  """Inspect Python file structure and return analysis."""
  # Implementation here
```


## Error Handling

### Custom Exceptions

Search existing custom exceptions for domain-specific errors first, for example:

```python
class LLMAPIError(Exception):
  """Exception raised when the LLM API returns an error."""
  pass

class TermInterrupted(Exception):
  """
  TermInterrupted is an exception raised when the terminal is interrupted by the user.
  """
  pass
```

If not present, create correlated and appropriate one with your feature.

### Exception Handling Patterns

Use `try...except...finally` structure if necessary, which allows you to handle exceptions gracefully and ensure cleanup code always runs, even if an error occurs.

```python
try:
    # Code that may raise an exception
    ...
except CustomError as e:
    # Handle known, expected errors
    ...
finally:
    # Always executed (cleanup, close files, release resources, etc.)
    ...
```


## Logging Standards

### Logger Setup

For the **frontend app and UI modules (i.e., `autopilot/app`)**, use module-level loggers `logging.getLogger(__name__)` with appropriate logging levels, for example:

```python
import logging

logger = logging.getLogger(__name__)

def execute_workflow(...):
  ...
  try:
    task_obj.launch_container()
  except Exception as e:
    logger.exception(
      f"Failed to launch container for {benchmark}/{task}: {e}"
    )
    self._cleanup_current_task(task_obj)
    return
```

For **autopilot system (annotation, evaluation, LLM service, etc)**, we prefer to use `rich.console.Console` class to handle the logging which you could import from `autopilot.utils`, for example:

```python
from autopilot.utils import console

def run_single_eval(...):
  if not eval_only:
    ...
    if reload_eval_path:
      try:
        ...
      except ValueError as e:
        console.print(
          f"Reloading {reload} failed, correct format is <branch>:<traj>:<step>, "
          "where both <traj> and <step> are integers."
        )
        raise e
```
