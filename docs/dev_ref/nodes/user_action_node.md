# User Action Node


## Overview

`UserActionNode` provides user interaction capabilities for supervising and controlling workflow execution. It currently handles proceed, feedback, edit, resample, and record operations.

Its key features include:

- **User Actions Selection**
    - Proceed (p): `action == "p"` - Continue workflow execution
    - Feedback (f): `action == "f"` - Provide feedback to LLM
    - Edit (e): `action == "e"` - Edit specific step content
    - Resample (n): `action == "n"` - Regenerate step content
    - Record (r): `action == "r"` - Record turning points

- **Command Processing**
    - Subtask commands: `cmd_type == "subtask"` - Opens substack with `data.open_substack()`
    - Context commands: `cmd_type == "context"` - Executes Python code for context modification
    - Terminal commands: Executes terminal commands via TerminalNode


## Context Commands
- **Summarize**: `summarize(start_idx, end_idx, summary)` - Summarizes conversation segments
- **Dynamic execution**: Uses `exec(cmd, {}, available_objects)` for context modification



## Edit Functionality
```python
def _edit(self, message: Message, data: ContextData, resample=False):
    if resample:
        new_content = ""
    else:
        # Open editor with temp file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            f.write(message.content)
        os.system(f"{self.editor} {f.name}")
        # Read edited content

    if new_content != message.content:
        data.branch_at(message.step - 1)  # Create branch
        extra_info = EditExtraInfo(edit_prefix=new_content, content_before_edit=message.content)
        return self.llm_node, extra_info
```

## Implementation

```python
def run(self, data: ContextData, extra_info: Optional[ExtraInfo] = None):
    if isinstance(extra_info, DirectActionExtraInfo):
        action = extra_info.action
        target_step = extra_info.target_step
    else:
        action, target_step = self._user_input(data)

    if action == "f":
        return self._feedback(data)
    elif action == "e":
        target_message = data.current_branch[target_step]
        return self._edit(target_message, data)
    elif action == "n":
        target_message = data.current_branch[target_step]
        return self._edit(target_message, data, resample=True)
    elif action == "r":
        return self._record(data)
    elif action == "p":
        return self._proceed(data)
```
