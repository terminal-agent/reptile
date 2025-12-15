import multiprocessing

from typer import Typer

from .annotation import run_annotation_app
from .app import run_gradio_app
from .config import app as config_app
from .data import app as data_app
from .evaluate import run_evaluation
from .mongo_viewer import view_mongodb
from .run import kill_runs, list_runs, run_autopilot

multiprocessing.set_start_method("spawn", force=True)

app = Typer()
app.command(name="run", help="Run the autopilot")(run_autopilot)
app.command(name="annotate", help="Run the annotation app")(run_annotation_app)
app.command(name="list", help="List autopilot runs")(list_runs)
app.command(name="kill", help="Kill autopilot runs")(kill_runs)
app.command(name="gradio", help="Run the autopilot Gradio app")(run_gradio_app)
app.command(name="mongo_viewer", help="View the MongoDB data")(view_mongodb)
app.command(name="evaluate", help="Evaluate the autopilot")(run_evaluation)
app.add_typer(config_app, name="config", help="Manage the autopilot config")
app.add_typer(data_app, name="data", help="View autopilot data")
