# Terminal-Bench Task Design

## Overview

Terminal-Bench evaluates AI agents on real-world terminal tasks spanning system administration, software development, data processing, optimization, and debugging.

## Task Setup

Terminal-Bench tasks are stored locally in the repository. The benchmark is included as a Git submodule under `external/terminal-bench/`. To initialize the tasks, run the following command to pull submodules. *If you have run this command and the benchmark directory is presenting under `external/terminal-bench/`, then you just ignore this section.*

```bash
git submodule update --init --recursive
```

Tasks are now located at `external/terminal-bench/tasks/` once the submodule is initialized.

## Task Format

Each Terminal-Bench task represents a self-contained terminal challenge. Tasks are stored locally in the repository under `external/terminal-bench/tasks/`.

### Task Structure

**Task Name**: Directory name is descriptive names indicating the problem of the task to solve, such as "hello-world" and "find-error-in-code".

**Directory Layout**:
```
hello-world/
├── task.yaml              # Task instruction and metadata
├── docker-compose.yaml    # Container configuration
├── Dockerfile             # Base image and dependencies
├── tests/test_*.py        # Pytest test files
├── run-tests.sh          # Evaluation script
└── solution.sh or solution.yaml   # Reference solution
```

### Data Format

The task metadata is loaded from the local `task.yaml` file at `external/terminal-bench/tasks/{task_name}/task.yaml`. For example:

```yaml
instruction: |-
  Create a file called /app/hello.txt. Write "Hello, world!" to it.
difficulty: easy | medium | hard
category: file-operations
tags: [file-operations]
parser_name: pytest
max_agent_timeout_sec: 900.0
max_test_timeout_sec: 180.0
expert_time_estimate_min: 1
junior_time_estimate_min: 1
```

## Task Implementation & Configuration

- **Task type**: `autopilot/evaluation/tasks/terminal_bench.py`
- **Dataset Loading**: Loaded from local YAML files in `external/terminal-bench/tasks/{task_name}/task.yaml`

### Docker Environment

**Docker Files Location**: `external/terminal-bench/tasks/{task_name}/`

```text
Dockerfile  # Task-specific image with dependencies
docker-compose.yaml  # Container orchestration (patched at runtime to use bridge network)
tests/test_*.py  # Pytest test files for evaluation
run-tests.sh  # Evaluation script that runs pytest
solution.sh or solution.yaml  # Optional reference solution
```

**Container Details**:
- Image Name Format: `terminal_bench_{task_name}` (each task has its own image). For example, `terminal_bench_triton-interpret`.
- Container Name Format: `terminal_bench_{session_name}`, where `session_name` is composed by `{task_name}-{timestamp}-{session-specific-random-hex-string}`. For example, `terminal_bench_triton-interpret-20251122-183325-5551`.
- Working Directory: `/app/` (where agent executes commands)
- Network Mode: Bridge (patched from docker-compose default)
- Image Build: Automatically built on first use via `launch_container()` method

### Evaluation Success Criteria

The success criteria is rule-based evaluation (`rule-based`):
1. Agent executes commands within the container environment
2. Evaluation script (`run-tests.sh`) runs pytest tests in `/app/tests/`
3. Script checks exit code and output for success indicators
4. Task passes if exit code is 0 and output contains "Tests passed!" (or equivalent success message)

Example evaluation script:
```bash
#!/bin/bash
cd /app
pytest tests/ -v
if [ $? -eq 0 ]; then
    echo "Tests passed!"
    exit 0
fi
exit 1
```

## References

- **Official Repository**: [github.com/laude-institute/terminal-bench](https://github.com/laude-institute/terminal-bench)
