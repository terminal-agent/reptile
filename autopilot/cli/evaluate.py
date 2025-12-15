import importlib
import os
from pathlib import Path
from typing import Annotated, List, Optional

import typer

from autopilot.config import GLOBAL_CONFIG
from autopilot.evaluation.batch_eval import batch_evaluate
from autopilot.evaluation.single_eval import run_single_eval
from autopilot.evaluation.tasks import TASKS
from autopilot.utils import console

# Validate eval_criteria
valid_criteria = [
  "rule-based",
  "llm-judge",
  "string-match",
  "swebench",
  "classified-pytest",
  "naive",
]


def run_evaluation(
  benchmark: Annotated[
    str, typer.Option("--benchmark", help="The benchmark to evaluate")
  ],
  task: Annotated[
    Optional[str], typer.Option("--task", help="The task to evaluate")
  ] = None,
  model: Annotated[
    Optional[List[str]], typer.Option("--model", help="The model to evaluate")
  ] = None,
  parallel: Annotated[
    int, typer.Option("--parallel", help="The number of parallel evaluations")
  ] = 4,
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
  reload: Annotated[
    str, typer.Option("--reload", help="The reload to evaluate")
  ] = "",
  reload_eval_path: Annotated[
    str,
    typer.Option(
      "--reload-eval-path",
      help="The path to the reload evaluation yml file",
    ),
  ] = "",
  editor: Annotated[
    str, typer.Option("--editor", help="The editor to evaluate")
  ] = "",
  interaction: Annotated[
    str, typer.Option("--interaction", help="The interaction to evaluate")
  ] = "executive_only",
  terminal: Annotated[
    bool, typer.Option("--terminal", help="Whether to use the terminal")
  ] = False,
  output_dir: Annotated[
    str, typer.Option("--output-dir", help="The output directory")
  ] = f"{Path(__file__).parent.parent.parent}/results",
  eval_criteria: Annotated[
    Optional[str],
    typer.Option(
      "--eval-criteria",
      help="The evaluation criteria (rule-based, llm-judge, string-match, swebench, classified-pytest, naive)",
    ),
  ] = None,
  cache_level: Annotated[
    str,
    typer.Option(
      "--cache-level",
      help="Docker cache level to use (none, base, env, all and naive). If 'all', no Docker images will be cleaned. If 'naive', we will not use the docker but run autopilot in host machine directly.",
    ),
  ] = "all",
  strong_scaffold: Annotated[
    bool,
    typer.Option(
      "--strong-scaffold/--no-strong-scaffold",
      help="Enable strong scaffold mode to control terminal node behavior",
    ),
  ] = False,
):
  # ========================
  # Evaluation Tool
  # ========================

  if eval_criteria is None:
    if benchmark in [
      "swebench_verified",
      "swebench_verified_focus",
      "swegym",
      "swegym_focus",
    ]:
      eval_criteria = "classified-pytest"
    elif benchmark in [
      "terminal_bench",
      "terminal_bench_focus",
      "terminal_bench_sample",
      "swe_bench",
    ]:
      eval_criteria = "rule-based"
    elif benchmark in ["mmlu_pro", "gsm8k"]:
      eval_criteria = "string-match"
    elif benchmark in ["locomo"]:
      eval_criteria = "llm-judge"
    else:
      raise ValueError(f"Unknown benchmark: {benchmark}")
  elif eval_criteria not in valid_criteria:
    raise typer.BadParameter(
      f"Invalid eval_criteria: {eval_criteria}. Must be one of: {', '.join(valid_criteria)}"
    )

  if interaction in ["interactive"]:
    terminal = True

  console.print(f"Output directory: {os.path.abspath(output_dir)}")
  console.print(f"Benchmark type: {benchmark}")
  console.print(f"Evaluation criteria: {eval_criteria}")

  if task is None:
    # ========================
    # Batch Evaluation
    # ========================
    llm_configs = GLOBAL_CONFIG.models
    if model:
      # Check if all specified models exist in config
      models = model
    else:
      target_config = max(llm_configs, key=lambda x: x.priority)
      models = [target_config.name]

    console.print("[bold green]Starting batch evaluation[/bold green]")
    console.print(f"Models to evaluate: {models}")

    if reload_eval_path:
      console.print(f"Batch reload evaluation for {reload_eval_path}")
    batch_evaluate(
      output_dir=output_dir,
      models=models,
      parallel=parallel,
      benchmark=benchmark,
      interaction=interaction,
      log_to_mongodb=log_to_mongodb,
      log_to_github=log_to_github,
      eval_criteria=eval_criteria,
      editor=editor,
      cache_level=cache_level,
      reload_eval_path=reload_eval_path,
      strong_scaffold=strong_scaffold,
    )
  else:
    # ========================
    # Single Evaluation
    # ========================
    os.makedirs(output_dir, exist_ok=True)
    console.print(
      f"[bold green]Starting evaluation for {benchmark}/{task}[/bold green]"
    )
    console.print(f"Output directory: {os.path.abspath(output_dir)}")
    task_instance = TASKS.get(benchmark).from_name(task, benchmark)

    # Single model evaluation - use first model if multiple provided
    model_name = model[0] if model else None
    if model and len(model) > 1:
      console.print(
        f"[yellow]Multiple models provided: {model}, using first model: {model_name}[/yellow]"
      )

    success, output_file = run_single_eval(
      task=task_instance,
      output_dir=output_dir,
      reload=reload,
      reload_eval_path=reload_eval_path,
      interaction=interaction,
      terminal=terminal,
      model=model_name,
      log_to_mongodb=log_to_mongodb,
      log_to_github=log_to_github,
      eval_criteria=eval_criteria,
      editor=editor,
      cache_level=cache_level,
      strong_scaffold=strong_scaffold,
    )
    color = "green" if success else "red"
    status = "Succeed" if success else "Fail"
    console.print(
      f"[green]{reload if reload else task_instance.name}[/green] [{color}]{status}[/{color}] ({output_file})"
    )
