# MMLU-Pro Task Design

## Overview

MMLU-Pro evaluates language understanding across 14 professional domains with 12,000+ multiple-choice questions. Each question has multiple answer choices.


## Task Generation

MMLU-Pro tasks must be generated from the HuggingFace dataset before they can be used for evaluation. We provide a tool script to download and convert tasks, which you could refer at `tools/mmlu_pro/README.md`.

### Tool Script Usage

Run the task conversion script to download and convert the MMLU-Pro dataset:

```bash
python tools/mmlu_pro/build_mmlu_pro_task.py
```

The script will
1. Downloads the MMLU-Pro dataset from HuggingFace (`TIGER-Lab/MMLU-Pro`)
2. Loads both test and validation splits
3. Creates a directory for **each** task at `external/MMLU-Pro/tasks/{index}/`
4. Saves the instance data as `instance.json` in each task directory


The script processes the entire test set and the progress is displayed via a progress bar.

Example logs:
```bash
data/test-00000-of-00001.parquet: 100%|███████████████████████████████████████████| 4.15M/4.15M [00:02<00:00, 1.55MB/s]
data/validation-00000-of-00001.parquet: 100%|█████████████████████████████████████| 42.9k/42.9k [00:01<00:00, 40.9kB/s]
Generating test split: 100%|███████████████████████████████████████████| 12032/12032 [00:00<00:00, 364824.92 examples/s]
Generating validation split: 100%|████████████████████████████████████████████| 70/70 [00:00<00:00, 59122.29 examples/s]
100%|███████████████████████████████████████████████████████████████████| 12032/12032 [00:01<00:00, 7786.72it/s]
```

Once all the tests processed, you will see the output tasks in `external/MMLU-Pro/tasks/`.


## Task Format

Each MMLU-Pro task represents a single multiple-choice question. Tasks are stored locally in the repository under `external/MMLU-Pro/tasks/`.

### Task Structure

**Task Name**: Integer index as string (e.g., "0", "1", "42")

**Directory Layout**:
```
external/MMLU-Pro/tasks/
├── 0/instance.json
├── 1/instance.json
├── 2/instance.json
...
└── N/instance.json  # Where N is the total number of existing test instances
```

### Data Format

Inside `instance.json`, each conversation is formatted as:

```json
{
   "question_id":70,
   "question":"Typical advertising regulatory bodies suggest, for example that adverts must not: encourage _________, cause unnecessary ________ or _____, and must not cause _______ offence.",
   "options":[
      "Safe practices, Fear, Jealousy, Trivial",
      "Unsafe practices, Distress, Joy, Trivial",
      "Safe practices, Wants, Jealousy, Trivial",
      "Safe practices, Distress, Fear, Trivial",
      "Unsafe practices, Wants, Jealousy, Serious",
      "Safe practices, Distress, Jealousy, Serious",
      "Safe practices, Wants, Fear, Serious",
      "Unsafe practices, Wants, Fear, Trivial",
      "Unsafe practices, Distress, Fear, Serious"
   ],
   "answer":"I",
   "answer_index":8,
   "cot_content":"",
   "category":"business",
   "src":"ori_mmlu-business_ethics"
}
```

The task data is loaded from the local `instance.json` file at `external/MMLU-Pro/tasks/{task_name}/instance.json`. Note the `question_id` is not the same as the task name (task directory).

## Task Implementation & Configuration

- **Task type**: `autopilot/evaluation/tasks/mmlu_pro.py`
- **Dataset Loading**: Loaded from local JSON files in `external/MMLU-Pro/tasks/{task_name}/instance.json`
- **Prompt Template**: `autopilot/prompts/mmlu_pro_prompt.py`

### Docker Environment

**Docker Files Location**: `tools/mmlu_pro/`

```text
build_image/Dockerfile  # Base image (`mmlupro.common:latest`)
Dockerfile  # Task-specific image extending base
docker-compose.yaml  # Container orchestration (patched at runtime to use bridge network)
test_script.sh  # Evaluation script that reads `/testbed/answer.txt`
```

**Container Details**:
- Shared Image: All tasks use the same minimal environment built from the same Dockerfile (Check `tools/mmlu_pro/Dockerfile`)
- Container Name Format: `mmlu_pro_{session_name}`, where `session_name` is composed by `{task_name}-{timestamp}-{session-specific-random-hex-string}`
- Working Directory: `/testbed/` (where agent writes answer)
- Eval Script Path: Copied to `/tmp/tasks/shared_scripts/test_script.sh` in container
- Task Directory: `/tmp/tasks/{task_name}/` in container
- Image Build: Automatically built on first use via `launch_container()` method

### Prompt Format

Questions are formatted with the prompt template defined in `autopilot/prompts/mmlu_pro_prompt.py`.

When constructing input prompt for a task, the answer choices will be formatted as options like:
```
A. Option 1
B. Option 2
C. Option 3
...
J. Option 10
```

### Environment Variables

The following environment variables are configured for each task container:

- `MMLU_PRO_TASK_BUILD_CONTEXT_DIR`: Points to `tools/mmlu_pro/`
- `MMLU_PRO_TASK_DOCKER_CLIENT_IMAGE_NAME`: Set to `"mmlu_pro"`
- `MMLU_PRO_TASK_DOCKER_NAME_PREFIX`: Container name
- `MMLU_PRO_TEST_DIR`: Path to test files
- `MMLU_PRO_TASK_LOGS_PATH` / `MMLU_PRO_CONTAINER_LOGS_PATH`: `/logs`
- `MMLU_PRO_TASK_DOCKER_CLIENT_CONTAINER_NAME`: Container name
- `TEST_DIR`: `/tmp/tasks/{task_name}/tests`
- `TASK_DIR`: `/tmp/tasks/{task_name}`
- `COMPOSE_PROJECT_NAME`: Container name
- `COMPOSE_DOCKER_CLI_BUILD` / `DOCKER_BUILDKIT`: Docker build settings
<!-- prevent hardcoding MMLU_PRO_TASK_LOGS_PATH, MMLU_PRO_CONTAINER_LOGS_PATH -->

### Evaluation Success Criteria

The success criteria is string-matched evaluation (`string-match`):
1. Agent writes single letter to `/testbed/answer.txt`
2. Evaluation script (`test_script.sh`) reads file content using `cat /testbed/answer.txt`
3. Compare if the answer choice selected is the same as corresponding ground truth

## References

- **Official Repository**: [github.com/TIGER-AI-Lab/MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro)
- **Dataset**: [huggingface.co/datasets/TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro)
