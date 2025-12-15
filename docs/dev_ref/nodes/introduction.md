# Node

## Overview
A node is an operation unit in a workflow, where all nodes inherit from the [`BaseNode`](https://github.com/terminal-agent/reptile/blob/main/autopilot/node/base.py) abstract base class. Each node represents a specific functional step in the workflow, responsible for handling particular tasks and determining the next execution flow.

## Available Nodes

We currently provide the following nodes in the `autopilot` library:

- [InitPromptNode](./init_prompt_node.md)
Initialization node that sets up initial prompts and context as the workflow entry point.

- [LLMNode](./llm_node.md)
Core AI reasoning node that generates responses using Large Language Models with streaming generation and editing capabilities.

- [TerminalNode](./terminal_node.md)
Command execution node that runs shell commands and keyboard inputs, capturing terminal output for workflow processing.

- [UserActionNode](./user_action_node.md)
Interactive control node providing user actions: proceed, feedback, edit, resample, and record operations.

- [EditorNode](./editor_node.md)
Automated supervision node using LLM as supervisor for feedback and editing, reducing human intervention.

- [OracleNode](./oracle_node.md)
Testing node that provides standard solutions for validation and benchmarking scenarios.

## Node Characteristics

| Node Type | Primary Use | Interaction Level | Automation Level |
|-----------|-------------|-------------------|------------------|
| LLMNode | AI Generation | None | High |
| TerminalNode | Command Execution | None | High |
| UserActionNode | User Control | High | Low |
| EditorNode | Automated Supervision | Low | High |
| OracleNode | Testing/Validation | None | Full |
| InitPromptNode | Workflow Initialization | None | Full |


## Add a New Node

To add a new node, you need to inherit from the `BaseNode` class and implement the `run` method.

Below is an example of creating a new node `MyNode`. We need to implement override three methods in the base class:

- `__init__`: Initialize the node, assign the name, role, workflow_config and terminal for the base class. In addition, you can define your own attributes, for example, if you want to have another LLM, you can create a new attribute e.g. `self.llm = OpenAI()`.
- `set_output_nodes`: This tells the node what the next node can be. It can accept one or multiple nodes. If multiple output nodes are accepted, `MyNode` will choose only one node as the output node depending its logic.
- `run`: Implement the logic of the node. This method will return the next node and any additional information that the next node needs to know.


```python
from autopilot.node import BaseNode


class MyNode(BaseNode):

  def __init__(
    self,
    workflow_config: WorkflowConfig,
  ):
    super().__init__(
      name="my-node",
      role=Role.USER,
      workflow_config=workflow_config,  # type: ignore
      terminal=None,
    )

  def set_output_nodes(self, output_node: SomeOtherNode):
    self.output_node = output_node

  def run(
    self, data: ContextData, extra_info: Optional[ExtraInfo] = None
  ) -> Tuple[Optional["BaseNode"], Optional[Dict[str, Any]]]:
    extra_info = do_something(data, extra_info)
    return self.output_node, extra_info
```
