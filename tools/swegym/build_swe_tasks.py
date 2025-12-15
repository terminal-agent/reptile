import os
import stat
import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from constants import PROMPT_TEMPLATE
from datasets import load_dataset

# Import external swebench version from submodule for build functionality
# This ensures we use the version with TestSpec support
submodule_path = (
  Path(__file__).parent.parent.parent / "external" / "swebench-fork"
)
submodule_path_str = str(submodule_path)
if submodule_path_str not in sys.path:
  sys.path.insert(0, submodule_path_str)

from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS
from swebench.harness.test_spec import TestSpec, make_test_spec


def generate_solution(dir: str) -> None:
  """Generate solution.sh from solution.md file"""
  solution_md_path = os.path.join(dir, "solution.md")
  solution_sh_path = os.path.join(dir, "solution.sh")

  solution_pattern = "A: "

  if os.path.exists(solution_sh_path):
    return
  if not os.path.exists(solution_md_path):
    raise FileNotFoundError(f"solution.md not found in {dir}")

  with open(solution_md_path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")
  for i, line in enumerate(lines):
    if line.startswith(solution_pattern):
      diff_content = (
        line[len(solution_pattern) :] + "\n" + "\n".join(lines[i + 1 :])
      )
      break
  else:
    raise LookupError("Could not find solution pattern in solution.md")

  solution_sh_content = f"""
#!/bin/bash

cat > /testbed/solution_patch.diff << 'EOF'
{diff_content}
EOF

cd /testbed
patch --fuzz=5 -p1 -i /testbed/solution_patch.diff
"""

  with open(solution_sh_path, "w", encoding="utf-8") as f:
    f.write(solution_sh_content)
  # Make solution.sh executable
  os.chmod(solution_sh_path, os.stat(solution_sh_path).st_mode | stat.S_IEXEC)


def postprocess_eval_script(
  instance: TestSpec, patch: str, verify: bool = False
) -> str:
  eval_script: str = instance.eval_script
  eval_script_lines = eval_script.splitlines()
  #  remove lines with pip install
  install_cmd = MAP_REPO_VERSION_TO_SPECS[instance.repo][instance.version].get(
    "install", ""
  )
  if install_cmd:
    eval_script_lines = [
      line
      for line in eval_script_lines
      if not line.strip().startswith(install_cmd)
    ]
  if eval_script_lines and eval_script_lines[-1].strip().startswith(
    "git checkout"
  ):
    eval_script = "\n".join(eval_script_lines[:-1]) + (
      "\n" if len(eval_script_lines) > 1 else ""
    )

  if verify:
    eval_script_lines = eval_script.splitlines()
    # add patch at second last line
    patch_cmd = (
      f"git apply -v - <<'EOF_114329324912'\n{patch}\nEOF_114329324912"
    )
    eval_script_lines[-1] = patch_cmd + "\n" + eval_script_lines[-1]
    eval_script = "\n".join(eval_script_lines)

  if instance.repo == "pandas-dev/pandas":
    env_script = instance.setup_env_script
    if "python=3.8" in env_script:
      eval_script_lines = eval_script.splitlines()
      eval_script_lines[-1] = (
        "conda install -c conda-forge 'hypothesis<6.114'\n"
        + eval_script_lines[-1]
      )
      eval_script = "\n".join(eval_script_lines)
  return eval_script


def build_task(
  instance: TestSpec,
  problem_statement: str,
  patch: str,
  verify: bool = False,
  swebench: bool = False,
):
  if swebench:
    prefix = "external/swebench-verified"
  else:
    prefix = "external/swegym"
  if verify:
    dst_folder = f"{prefix}/tasks/verify-{instance.instance_id}"
  else:
    dst_folder = f"{prefix}/tasks/{instance.instance_id}"
  os.makedirs(dst_folder, exist_ok=True)
  os.makedirs(f"{dst_folder}/build_image", exist_ok=True)

  with open(f"{dst_folder}/build_image/setup_env.sh", "w") as f:
    f.write(instance.setup_env_script)

  with open(f"{dst_folder}/build_image/Dockerfile", "w") as f:
    f.write(instance.base_dockerfile)
    f.write("\n")
    env_dockerfile = instance.env_dockerfile
    env_dockerfile_lines = env_dockerfile.splitlines()
    if env_dockerfile_lines and env_dockerfile_lines[0].strip().startswith(
      "FROM"
    ):
      env_dockerfile = "\n".join(env_dockerfile_lines[1:])
    else:
      raise ValueError(
        f"Expected env_dockerfile to start with FROM, but got: {env_dockerfile[:100] if env_dockerfile else 'empty'}"
      )
    f.write(env_dockerfile)

  with open(f"{dst_folder}/Dockerfile", "w") as f:
    f.write(instance.instance_dockerfile)

  with open(f"{dst_folder}/setup_repo.sh", "w") as f:
    f.write(instance.install_repo_script)

  task_yaml = dict(
    descriptions=[
      dict(
        key="base",
        description=problem_statement,
      )
    ],
    difficulty="medium",
    category="debugging",
    tags=[
      "coding",
      "swegym",
    ],
    parser_name="pytest",
    max_agent_timeout_sec=360.0,
    max_test_timeout_sec=60.0,
    test_scripts=[
      "setup-uv-pytest.sh",
      "run-uv-pytest.sh",
    ],
    run_tests_in_same_shell=False,
    env_name="",
    # Add test metadata for better evaluation
    test_metadata=dict(
      fail_to_pass_tests=instance.FAIL_TO_PASS,
      pass_to_pass_tests=instance.PASS_TO_PASS,
      total_fail_to_pass=len(instance.FAIL_TO_PASS),
      total_pass_to_pass=len(instance.PASS_TO_PASS),
      repo=instance.repo,
      version=instance.version,
      instance_id=instance.instance_id,
    ),
  )

  with open(f"{dst_folder}/task.yaml", "w") as f:
    yaml.dump(task_yaml, f)

  with open(f"{dst_folder}/run-tests.sh", "w") as f:
    eval_script = postprocess_eval_script(instance, patch, verify)
    f.write(eval_script)

  with open(f"{dst_folder}/solution.md", "w") as f:
    f.write(f"Q: {problem_statement}\nREPO:{instance.instance_id}\nA: {patch}")

  generate_solution(dst_folder)

  print(f"✅ {dst_folder.split('/')[-1]} done")


@click.command()
@click.option("--start_idx", "-s", type=int, default=0)
@click.option(
  "--end_idx", "-e", type=int, default=100000000
)  # default to build the whole dataset
@click.option("--task_ids", "-t", type=str, default=None)
@click.option("--verify", "-v", is_flag=True)
@click.option("--swebench", is_flag=True)
def main(start_idx, end_idx, task_ids, verify, swebench):
  if task_ids:
    task_ids = task_ids.split(",")
    if swebench:
      dataset = load_dataset(
        "princeton-nlp/SWE-bench_Verified", split="test"
      ).filter(
        lambda x: x["instance_id"] in task_ids
        or x["instance_id"].lower() in task_ids
      )
    else:
      dataset = load_dataset("SWE-gym/SWE-gym", split="train").filter(
        lambda x: x["instance_id"] in task_ids
        or x["instance_id"].lower() in task_ids
      )
  else:
    if swebench:
      dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
      dataset = dataset.select(range(start_idx, min(end_idx, len(dataset))))
    else:
      dataset = load_dataset("SWE-gym/SWE-gym", split="train")
      dataset = dataset.select(range(start_idx, min(end_idx, len(dataset))))
  for d in dataset:
    test_spec_instance = make_test_spec(d)
    patch = d["patch"]
    problem_statement = PROMPT_TEMPLATE.format(
      problem_statement=d["problem_statement"]
    )
    build_task(
      test_spec_instance,
      problem_statement,
      patch,
      verify=verify,
      swebench=swebench,
    )


if __name__ == "__main__":
  main()
