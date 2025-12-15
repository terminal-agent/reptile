import typer
from typing_extensions import Annotated

from autopilot.llm.llm import LLM, LLMAPIError, LLMInterrupted

from .tool import TOOLS, CLITool


@TOOLS.register
class AskDeepseekCLI(CLITool):
  name: str = "ask_deepseek"
  description: str = """
  Ask a commercial LLM powered by Deepseek a question and get the response.
  Usage:

  ~~~sh
  ask_deepseek "Your question here"
  ~~~
  """

  def ask(
    self,
    question: Annotated[
      str, typer.Argument(help="The question to ask Deepseek")
    ],
  ):
    try:
      from threading import Event

      event = Event()
      llm = LLM(model="deepseek")
      response = llm.generate(
        system_prompt="", context=[("user", question)], event=event
      )
      print(response)
    except LLMAPIError:
      print("You cannot use it because no API key.")
    except LLMInterrupted:
      print("LLM interrupted, pass control to user.")

  def register(self):
    self.app.command(
      help="Ask a question to a powerful AI powered by Deepseek"
    )(self.ask)
