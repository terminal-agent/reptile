from typing import Annotated, Optional

import typer

from autopilot.app.gradio import AutopilotGradioApp


def run_gradio_app(
  port: Annotated[
    int, typer.Option("-p", "--port", help="The port to use")
  ] = 8000,
  zmq_port: Annotated[
    int, typer.Option("-z", "--zmq-port", help="The zmq port to use")
  ] = 8001,
  model: Annotated[
    Optional[str],
    typer.Option(
      "-m",
      "--model",
      help="The model to use. Fallback to the model with the highest priority if not provided.",
    ),
  ] = None,
  sandbox: Annotated[
    Optional[str], typer.Option("-s", "--sandbox", help="The sandbox to use")
  ] = None,
  name: Annotated[
    Optional[str],
    typer.Option(
      "-n",
      "--name",
      help="The task session name to use. Fallback to 'gradio-session' if not provided.",
    ),
  ] = None,
  max_steps: Annotated[
    int,
    typer.Option(
      "--max-steps",
      help="The maximum number of steps to run the autopilot",
    ),
  ] = 200,
  max_time: Annotated[
    int,
    typer.Option("--max-time", help="The maximum time to run the autopilot"),
  ] = 600,
  log_to_mongodb: Annotated[
    bool,
    typer.Option(
      "--log-to-mongodb/--no-log-to-mongodb",
      help="Control whether to push the data to telemetry",
    ),
  ] = True,
  log_to_github: Annotated[
    bool,
    typer.Option(
      "--log-to-github/--no-log-to-github",
      help="Control whether to push the data to github",
    ),
  ] = True,
):
  # Provide default values for optional parameters
  if name is None:
    name = "gradio-session"  # Default name

  # run gradio
  app = AutopilotGradioApp(
    model=model,
    sandbox=sandbox,
    name=name,
    max_steps=max_steps,
    max_time=max_time,
    log_to_mongodb=log_to_mongodb,
    log_to_github=log_to_github,
  )
  app.launch(port=port, zmq_port=zmq_port)
