import typer
from typing_extensions import Annotated

from autopilot.llm.llm import LLM, LLMAPIError, LLMInterrupted

from .tool import TOOLS, CLITool


@TOOLS.register
class AskGeminiCLI(CLITool):
  name: str = "ask_google_ai"
  description: str = """
  Ask a commercial LLM powered by Google Gemini a question and get the response.
  Usage:

  ~~~sh
  ask_google_ai "Your question here"
  ~~~
  """

  def ask(
    self,
    question: Annotated[
      str, typer.Argument(help="The question to ask Google Gemini")
    ],
  ):
    try:
      from threading import Event

      event = Event()
      llm = LLM(model="gemini")
      response = llm.generate(
        system_prompt="", context=[("user", question)], event=event
      )
      print(response)
      return response
    except LLMAPIError:
      print("You cannot use it because no API key.")
      return "Error: No API key"
    except LLMInterrupted:
      print("LLM interrupted, pass control to user.")
      return "Interrupted"

  def register(self):
    self.app.command(
      help="Ask a question to a powerful AI powered by Google Gemini"
    )(self.ask)
