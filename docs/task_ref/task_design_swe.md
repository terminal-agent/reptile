# SWE-Bench Task Design

## Overview

SWE-Bench (Software Engineering Benchmark) evaluates AI agents on real-world software engineering tasks from GitHub repositories. Tasks include bug fixing (Pull Request tasks) and code comprehension (QA tasks) across popular open-source projects.

We have compiled several benchmarks in our repository for you to evaluate the performance of terminal agents. These tasks follow a unified workflow for evaluation. One example task is [sglang-6709-easy-1](https://github.com/terminal-agent/swebench-tasks/tree/main/tasks/sglang-6709-easy-1).

## Task Setup

SWE-Bench tasks are stored locally in the repository under `external/swe-bench/tasks/`. Each task represents either a GitHub issue requiring a code fix or a question about the codebase.

If you didn't see `external/swe-bench/`, run the following command to pull submodule (i.e., submodule `https://github.com/terminal-agent/swebench-tasks.git`):

```bash
git submodule update --init --recursive
```

## Task Format

**Task Name**: Descriptive name following the pattern `{repo}-{issue_number}` or `{repo}-{issue_number}-{variant}`.

Examples: `requests-863`, `django-10924`, `sglang-6709-easy-1`

**Directory Layout**:
```
requests-863/
├── task.yaml              # Task description and metadata
├── Dockerfile             # Task-specific container definition
├── build_image/           # Base image setup (repo-level environment)
├── setup_repo.sh          # Repository cloning and checkout script
└── run-tests.sh          # Evaluation script
```

These tasks consist of the following key components:

- `build_image` (Optional): Set up a docker image (terminal tools and python environment) for a repo, e.g., `psf/requests`.

- `Dockerfile`: Starts from the repo-specific docker image, and runs `setup_repo.sh` to set up for the env for the issue.

- `setup_repo.sh`: Clones the github repo and resets it to the commit where the issue occurs.

- `task.yaml`: Contains the task description (issue text) as the instruction for LLMs.

- `run-tests.sh`

    * For QA tasks, in `task.yaml`, instruct the LLM to write its answer into a `.txt`, then check the content of that file to determine whether the LLM passes the test. An example: [sglang-6709-easy-1](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/sglang-6709-easy-1/run-tests.sh#L28).

    * For Pull Requests tasks, run the unit tests to check whether the modification works. Example: [requests-863](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/requests-863/run-tests.sh#L14).

**Note: Most of the above are fixed templates, so only need to modify the task specific parts to create new tasks: base environment setup, github repo address, commit id, task instruction and judge function.**

## Task Implementation & Configuration

- **Task Type**: `autopilot/evaluation/tasks/swe_bench.py`
- **Dataset Loading**: Loaded from local YAML files in `external/swe-bench/tasks/{task_name}/task.yaml`

### Docker Environment

**Container Details**:
- Image Name Format: `swe_bench_{task_name}` (each task has its own image extending from base)
- Container Name Format: `swe_bench_{session_name}`, where `session_name` is composed by `{task_name}-{timestamp}-{session-specific-random-hex-string}`
- Working Directory: `/app/testbed/` (where agent executes commands)
- Network Mode: Bridge (patched from docker-compose default)
- Image Build: Base image built on first use if not present. Task-specific image built automatically via `launch_container()`

**File Locations in Container**:
- Repository: `/app/testbed/`
- Answer file (QA tasks): `/app/testbed/answer.txt`
- Patch file (PR tasks): `/tmp/tasks/patch.txt`
- Evaluation script: `/tmp/tasks/shared_scripts/test_script.sh`
- Task files: `/tmp/tasks/{task_name}/`
- Shared scripts: `/tmp/tasks/shared_scripts/`

### Environment Variables

The following environment variables are configured for each task container:

- `SWE_BENCH_TASK_BUILD_CONTEXT_DIR`: Points to task directory
- `SWE_BENCH_TASK_DOCKER_CLIENT_IMAGE_NAME`: Set to `swe_bench_{task_name}`
- `SWE_BENCH_TASK_DOCKER_NAME_PREFIX`: Container name
- `SWE_BENCH_TEST_DIR`: Path to test files
- `SWE_BENCH_TASK_LOGS_PATH` / `SWE_BENCH_CONTAINER_LOGS_PATH`: `/logs`
- `SWE_BENCH_TASK_DOCKER_CLIENT_CONTAINER_NAME`: Container name
- `TEST_DIR`: `/tmp/tasks/{task_name}/tests`
- `TASK_DIR`: `/tmp/tasks/{task_name}`
- `COMPOSE_PROJECT_NAME`: Container name
- `COMPOSE_DOCKER_CLI_BUILD` / `DOCKER_BUILDKIT`: Docker build settings
<!-- prevent hardcoding SWE_BENCH_TASK_LOGS_PATH, SWE_BENCH_CONTAINER_LOGS_PATH -->

### Evaluation Success Criteria

The success criteria is rule-based evaluation (`rule-based`):

#### For QA Tasks

Verification checks whether required keywords appear in `/app/testbed/answer.txt`. For example, see the implementation in [sglang-6709-easy-1](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/sglang-6709-easy-1/run-tests.sh#L21):

```bash
...

# check whether /app/testbed/answer.txt exists
if [[ ! -f /app/testbed/answer.txt ]]; then
    echo "ERROR: /app/testbed/answer.txt does not exist."
    exit 10
fi

# keywords to check in /app/testbed/answer.txt
keywords=("make_layers" "Qwen2" "Mixtral" "Llama" "Phi3Small" "Qwen3")

# check if all keywords are present in /app/testbed/answer.txt
missing_keywords=()
for kw in "${keywords[@]}"; do
    if ! grep -qi "$kw" /app/testbed/answer.txt; then
        missing_keywords+=("$kw")
    fi
done

if [[ ${#missing_keywords[@]} -ne 0 ]]; then
    echo "ERROR: The following keywords are missing in /app/testbed/answer.txt:"
    for kw in "${missing_keywords[@]}"; do
        echo " - $kw"
    done
    exit 11
fi

echo "All required keywords found in /app/testbed/answer.txt."
```

#### For PR Tasks

SWE-Bench evaluation follows a standard pipeline, see eval for [requests-863](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/requests-863/run-tests.sh):
- [Display the git diff](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/requests-863/run-tests.sh#L10)
- [Apply issue-specific tests](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/requests-863/run-tests.sh#L15)
- [Run the unit tests](https://github.com/terminal-agent/swebench-tasks/blob/main/tasks/requests-863/run-tests.sh#L62)

Example evaluation script structure:
```bash
#!/bin/bash
cd /app/testbed

# Display changes made by agent
git diff

# Apply new test case for this issue
git apply -v - <<'EOF'
diff --git a/tests/test_requests.py b/tests/test_requests.py
...
EOF

# Run the specific test
pytest -rA tests/test_requests.py::TestSuite::test_new_feature
```

The task passes if:
- `fail_to_pass_tests`: Tests that were failing before the fix now pass
- `pass_to_pass_tests`: Tests that were passing before remain passing (no regression)

### How to Write `run-tests.sh`

The `run-tests.sh` script is the evaluation script that determines task success. The script should return exit code 0 if the task succeeds; any other return value indicates failure.

## References

- **Official Repository**: [github.com/SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench)
- **Example Tasks we created for eval**: [github.com/Sailor-Agents/swebench-tasks](https://github.com/terminal-agent/swebench-tasks)
