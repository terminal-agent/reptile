# Editor Node

## Overview

`EditorNode` uses an LLM as supervisor to provide automated feedback and editing capabilities, reducing human intervention in workflows.

Its key features include:

- **Automated Supervision**
    - LLM Supervisor: Uses separate `editor_llm` model for supervision
    - Automatic Feedback: Generates feedback without human intervention
    - LGTM Approval: `"LGTM" in feedback` triggers proceed action
    - Quality Control: Ensures output quality through automated review


## Configuration

The editor LLM can be configured via the following fields:

- **Constructor Argument**: We can pass`editor_llm` to the `EditorNode` constructor to specify the LLM model to use for supervision.
- **Supervisor Prompts**: We can modify `autopilot.prompts.SUPERVISOR_PROMPT` and `autopilot.prompts.SUPERVISOR_SYSTEM_PROMPT` to change the behavior of the editor LLM.
