from typing import Annotated

import typer

from autopilot.app.gradio.mongo_viewer import MongoViewer


def view_mongodb(
  port: Annotated[
    int, typer.Option("-p", "--port", help="The port to use")
  ] = 8000,
):
  viewer_app = MongoViewer()
  viewer_app.launch(port=port)
