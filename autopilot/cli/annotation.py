from typing import Annotated

import typer

from autopilot.app.gradio import AnnotationGradioApp


def run_annotation_app(
  port: Annotated[
    int, typer.Option("-p", "--port", help="The port to use")
  ] = 8003,
  zmq_port: Annotated[
    int, typer.Option("-z", "--zmq-port", help="The zmq port to use")
  ] = 8004,
  log_to_mongodb: Annotated[
    bool,
    typer.Option("--log-to-mongodb/--no-log-to-mongodb", help="Log to MongoDB"),
  ] = True,
  log_to_github: Annotated[
    bool,
    typer.Option("--log-to-github/--no-log-to-github", help="Log to GitHub"),
  ] = True,
):
  # run gradio
  app = AnnotationGradioApp(
    port=port,
    zmq_port=zmq_port,
    log_to_mongodb=log_to_mongodb,
    log_to_github=log_to_github,
  )
  app.launch()
