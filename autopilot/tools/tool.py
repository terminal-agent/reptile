from abc import ABC, abstractmethod
from typing import Type, TypeVar

from typer import Typer

__all__ = ["CLITool", "TOOLS"]

ToolType = TypeVar("ToolType", bound="CLITool")


class CLITool(ABC):
  """
  An abstract class for the CLI tool. Tools inheriting this class can be built as command line tools and be used in the workflow.

  Args:
    name (str): the name of the tool
    description (str): the description of the tool
    app (Typer): the typer app for the tool

  Returns:
    None
  """

  name: str
  description: str
  app: Typer = Typer()

  def __init__(self):
    self.register()

  @abstractmethod
  def register(self):
    pass

  @classmethod
  def run(cls):
    cls().app()


class ToolRegistry:
  """
  A registry for the CLI tools defined in this project.
  """

  def __init__(self):
    self.data = {}

  def register(self, cls: Type[ToolType]) -> Type[ToolType]:
    """
    Register a CLI tool to the registry.

    Usage:
    ~~~python
    @TOOLS.register
    class MyTool(CLITool):
      name = "mytool"
      description = "This is the description of mytool"
    ~~~

    Args:
      cls (Type[ToolType]): the class of the tool to register

    Returns:
      cls (Type[ToolType]): the class of the tool to register
    """
    self.data[cls.name] = {
      "description": cls.description,
    }
    return cls

  def show(self) -> None:
    """
    Print the registered tools.
    """
    for name, data in self.data.items():
      print(f"{name}: {data['description']}")

  def get_tools_description(self) -> str:
    """
    Generate formatted tools description for system prompt.

    Returns:
      tools_desc (str): the formatted tools description

    """
    tools_desc = "For all the tools, you can use `--help` to get the help information of the tool.\n"
    # Add all registered tools
    for name, data in self.data.items():
      desc_lines = data["description"].strip().split("\n")
      formatted_desc = desc_lines[0]
      if len(desc_lines) > 1:
        formatted_desc += "\n" + "\n".join(
          f"  {line}" for line in desc_lines[1:]
        )

      tools_desc += f"- {name}: {formatted_desc}\n"
    return tools_desc


TOOLS = ToolRegistry()
