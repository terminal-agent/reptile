# LoCoMo Task Design

## Overview

LoCoMo (Long Conversation Memory) evaluates long-term conversational memory across extended multi-session dialogues. Tasks test cross-session information retrieval and temporal reasoning.

## Data Loading

LoCoMo tasks are loaded from a pre-existing local dataset file. No separate generation step is required.

**Dataset Location**: `external/locomo/data/locomo10.json`

The dataset is loaded automatically when initializing any LoCoMo task instance via `LocomoTask.load_locomo()`.

## Task Format

### Task Structure

**Task Name Format**: `<conversation_id>_<question_id>`
- Both IDs are zero-based numeric indices
- Examples: `0_0`, `0_1`, `5_3`, `9_12`
- Format: Conversation index (0-9) + underscore + question index within that conversation
- `LocomoTask.task_names()` is used for task name formation

### Data Format

The dataset is a JSON array where each element represents one multi-tern conversation with multiple QA pairs. For example:

```json
{
  "sample_id": "conv-26",
  "qa": [
    {
      "question":"When did Caroline go to the LGBTQ support group?",
      "answer":"7 May 2023",
      "evidence":[
          "D1:3"
      ],
      "category":2
    },
    // ...
  ],
  "conversation": {
    "speaker_a": "Caroline",
    "speaker_b": "Melanie",
    "session_1_date_time": "1:56 pm on 8 May, 2023",
    "session_1": [
      {
          "speaker":"Caroline",
          "dia_id":"D1:1",
          "text":"Hey Mel! Good to see you! How have you been?"
      },
      {
          "speaker":"Melanie",
          "dia_id":"D1:2",
          "text":"Hey Caroline! Good to see you! I'm swamped with the kids & work. What's up with you? Anything new?"
      },
      // ...
    ],
    "session_2_date_time":"1:14 pm on 25 May, 2023",
    "session_2": [
      {
          "speaker":"Melanie",
          "dia_id":"D2:1",
          "text":"Hey Caroline, since we last chatted, I've had a lot of things happening to me. I ran a charity race for mental health last Saturday \u2013 it was really rewarding. Really made me think about taking care of our minds."
      },
      // ...
    ],
  },
  "observation": {
    // ...
  },
  "session_summary": {
    // ...
  }
}
```

`conversation` and `qa` for a conversation are two key fields we focus on.

**`conversation`**: Contains list of sessions (`session_<num>`) and their timestamps (`session_<num>_date_time`). The numbers `<num>` represent the chronological order of the sessions.
  - `speaker_a`, `speaker_b`: Names of the two conversation participants
  - `session_N`: Array of chat messages for session N (N starts from 1)
    - Each turn contains:
      - `speaker`: Name of the speaker
      - `dia_id`: Dialog ID (format: "D<session>:<turn>", e.g., "D1:3")
      - `text`: Content of the dialog
  - `session_N_date_time`: Timestamp string (format: "HH:MM am/pm on DD Month, YYYY")

**`qa`**: Array of question-answer pairs about this conversation
  - `question`: The question to answer
  - `answer`: Ground truth answer
  - `evidence`: References to relevant parts (e.g., ["D1:3"] refers to session 1, turn 3)
  - `category`: Question category type

## Task Implementation & Configuration

- **Task type**: `autopilot/evaluation/tasks/locomo.py`
- **Data Loading**: `load_locomo()` reads `locomo10.json` at class initialization
- **Prompt Template**: `autopilot/prompts.py`

### Docker Environment

**Docker Files Location**: `tools/locomo/`

```text
build_image/Dockerfile
Dockerfile  # Task-specific image extending base
docker-compose.yaml  # Container orchestration (patched at runtime to use bridge network)
test_script.sh  # Evaluation script
```

**Container Details**:
- Shared Image: All tasks use the same minimal environment built from the same Dockerfile (Check `tools/locomo/Dockerfile`)
- Container Name Format: `locomo_{session_name}`, where `session_name` is composed by `{task_name}-{timestamp}-{session-specific-random-hex-string}`
- Working Directory: `/testbed/` (where conversation.txt is written)
- Eval Script Path: Copied to `/tmp/tasks/shared_scripts/test_script.sh` in container
- LLM Judge Path: `/tmp/tasks/shared_scripts/llm_judge.py`
- Image Build: Automatically built on first use via `launch_container()` method

**File Locations in Container**:
- Processed conversation: `/testbed/conversation.txt` (written by `LocomoTask.write_conversation()`)
- Agent's answer: `/testbed/answer.txt`
- Gold answer: `/tmp/tasks/answer.txt`

### Prompt Format

The conversation is processed chronologically by session timestamp using `LocomoTask.process_conversation`, then formatted with the prompt template in `autopilot/prompts/locomo_prompt.py`

**Processing Steps**:
1. Extract all sessions from conversation data
2. Sort sessions by timestamp (converted to sortable format)
3. Format each session with timestamp header
4. Messages shown as `{speaker_name}: {text}`
5. Sessions separated by double newlines

### Environment Variables

The following environment variables are configured for each task container:

- `LOCOMO_TASK_BUILD_CONTEXT_DIR`: Points to `tools/locomo/`
- `LOCOMO_TASK_DOCKER_CLIENT_IMAGE_NAME`: Set to `"locomo"`
- `LOCOMO_TASK_DOCKER_NAME_PREFIX`: Container name
- `LOCOMO_TEST_DIR`: Path to test files
- `LOCOMO_TASK_LOGS_PATH` / `LOCOMO_CONTAINER_LOGS_PATH`: `/logs`
- `LOCOMO_TASK_DOCKER_CLIENT_CONTAINER_NAME`: Container name
- `TEST_DIR`: `/tmp/tasks/{task_name}/tests`
- `TASK_DIR`: `/tmp/tasks/{task_name}`
- `COMPOSE_PROJECT_NAME`: Container name
- `COMPOSE_DOCKER_CLI_BUILD` / `DOCKER_BUILDKIT`: Docker build settings
<!-- prevent hardcoding LOCOMO_TASK_LOGS_PATH, LOCOMO_CONTAINER_LOGS_PATH -->

### Evaluation Success Criteria

The success criteria is judged by LLM (`llm-judge`) with the following flow:
1. Agent receives full conversation history + question via LOCOMO_PROMPT
2. Agent generates answer and writes it to `/testbed/answer.txt`
3. Evaluation script (`test_script.sh`) invokes LLM judge to compare answers
4. LLM judge compares agent answer to ground truth answer and provide a conclusion (e.g., CORRECT or WRONG)

## References

- **Official Repository**: [github.com/snap-research/locomo](https://github.com/snap-research/locomo)
- **Project Page**: [snap-research.github.io/locomo](https://snap-research.github.io/locomo/)
