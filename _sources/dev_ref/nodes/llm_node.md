# LLM Node

## Overview

`LLMNode` generates AI responses using Large Language Models. It handles streaming generation, interrupt mechanisms, and editing capabilities.

Its key features include:

- **Streaming Generation**
    - Real-time output: `self.console.stream(generation_stream, use_markdown=True)`
    - Interrupt support: Uses `self.interrupt_event` for interruption
    - Markdown rendering: `use_markdown=True` for rich output

- **Editing Support**
    - Edit handling: Processes `EditExtraInfo` with `edit_prefix` and `content_before_edit`
    - Resampling: Regenerates content when `resample=True`
    - Context preservation: Maintains conversation context across edits

- **Command Integration**
    - Tool integration: Uses `TOOLS.get_tools_description()` in system prompt
    - Command extraction: Commands extracted by `extract_commands()` utility
    - Multiple types: Supports bash, key, subtask, context commands

## Configuration

The `LLMNode` is configured via both the `workflow_config` and the `models` field in the global configuration file (you can edit via `autopilot config edit` command). A sample configuration for `models` is shown below. This configuration defines two parts:

1. model selection and credentials: defines how to access the LLM API.
2. model priority: if the user does not specify the model in the `workflow_config`, the `LLMNode` will use the model with the highest priority.

```yaml
models:
  - name: deepseek
    credentials:
      api_key: xxxx
      base_url: https://api.deepseek.com
    parameters:
      model: deepseek-chat
    priority: 0
  - name: gemini
    credentials:
      api_key: xxx
      base_url: https://generativelanguage.googleapis.com/v1beta/openai/
    parameters:
      model: gemini-1.5-flash
    priority: 0
```

If the user wants to select the model to use without modifying the priority, they can set the `model` field in the `workflow_config` to the name of the model. For example, if the user wants to use the `deepseek` model, they can set the `workflow_config` to:

```python
workflow_config = WorkflowConfig(
  model="deepseek",
  ...
)
```
