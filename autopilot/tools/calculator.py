import typer
from typing_extensions import Annotated

from .tool import TOOLS, CLITool


@TOOLS.register
class CalculatorCLI(CLITool):
  name: str = "calculator"
  description: str = """
  A simple calculator, for example: calculator 2*6, this will print 12.
  Usage:

  ```sh
  calculator <expression>
  ```
  But maybe you're more familiar with shell command `expr`, or you can always
  invoke python directly.
  """

  def compute(
    self,
    expression: Annotated[
      str, typer.Argument(help="The computation expression as a string")
    ],
  ) -> int | float:
    ret = eval(expression)
    print(ret)
    return float(ret)

  def register(self):
    self.app.command(help="Compute an expression")(self.compute)
