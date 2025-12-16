## Overview

Hooks provide lifecycle management and sidecar functionality for workflows. All hooks inherit from the `BaseHook` abstract base class and can be registered to workflows for monitoring, logging, and control flow management.

## Hook Design

Hooks can be executed at different points in the workflow lifecycle:

- **Pre-run**: before workflow starts
- **Pre-node**: before each node execution
- **Post-node**: after each node execution
- **Post-run**: after workflow finishes

## Available Hooks

We currently provide the following hooks in the `autopilot` library:

- [CheckpointingHook](./checkpointing_hook.md)
Automatically saves workflow state to Git repositories for version control and recovery.

- [InterruptHook](./interrupt_hook.md)
Provides timeout and step limit controls for workflow execution with automatic termination.

- [ReloadHook](./reload_hook.md)
Enables workflow reloading from remote GitHub repositories for state restoration.

- [GradioHook](./gradio_hook.md)
Provides ZMQ communication integration for Gradio-based user interfaces.

- [TelemetryHook](./telemetry_hook.md)
Records workflow data to remote repositories (GitHub) or databases (MongoDB).

## Hook Characteristics

| Hook Type | Primary Use | Data Storage | Integration |
|-----------|-------------|--------------|-------------|
| CheckpointingHook | State Management | Git Repository | Local |
| InterruptHook | Execution Control | None | Local |
| ReloadHook | State Restoration | GitHub | Remote |
| GradioHook | UI Integration | ZMQ Messages | Remote |
| TelemetryHook | Data Collection | GitHub/MongoDB | Remote |

## Add a New Hook

To add a new hook, you need to inherit from the `BaseHook` class and implement the `pre_run_execute`, `pre_node_execute`, `post_node_execute`, and `post_run_execute` methods.

```python
from autopilot.hooks import BaseHook

class MyHook(BaseHook):

  def pre_run_execute(self, data: ContextData, workflow: BaseWorkflow):
    # do something before the workflow starts
    ...

  def pre_node_execute(self, data: ContextData, node: BaseNode):
    # do something before the node starts
    ...

  def post_node_execute(self, data: ContextData, node: BaseNode):
    # do something after the node finishes
    ...

  def post_run_execute(self, data: ContextData, workflow: BaseWorkflow):
    # do something after the workflow finishes
    ...

# register the hook to the workflow
workflow.register_hook(MyHook())
```
