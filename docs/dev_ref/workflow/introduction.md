## Overview

Workflows are the orchestration layer that manages the execution flow of nodes and defines the data flow between them. Each workflow type is designed for specific use cases and interaction patterns.

Its key features include:

- **Graph Definition**: Flexibly define the data flow between nodes.
- **Hook System**: Support for lifecycle hooks and monitoring
- **Exception Handling**: Robust error handling with recovery mechanisms
- **Configuration**: Flexible configuration through WorkflowConfig
- **Terminal Integration**: Integration with terminal execution environment

## Available Workflows

- [AutopilotWorkflow](./autopilot_workflow.md): Standard interactive workflow with human supervision, ideal for interactive development and debugging.
- [EditorWorkflow](./editor_workflow.md): Automated workflow using LLM as supervisor, providing automated feedback and editing capabilities.
- [OracleWorkflow](./oracle_workflow.md): Simple workflow for testing and validation, providing standard solutions for benchmarking.

## Workflow Characteristics

| Workflow Type | Use Case | Human Interaction | Automation Level |
|---------------|----------|-------------------|------------------|
| AutopilotWorkflow | Development, Learning, Quality Control | High | Low |
| EditorWorkflow | Automated Operations, Scalable Tasks | Low | High |
| OracleWorkflow | Testing, Validation, Benchmarking | None | Full |


## How to create a new workflow

To create a new workflow, you need to inherit from the `BaseWorkflow` class and implement the `define_graph` method. The `define_graph` method is used to define the dataflow among nodes. You need to use `BaseNode.set_output_nodes` to connect the nodes. Also, you need to set the value for `self.start_node` to specify the start node of the workflow.

```python
from autopilot.workflow.base_workflow import BaseWorkflow

class MyWorkflow(BaseWorkflow):

    def __init__(self, workflow_config: WorkflowConfig):
        super().__init__(name="my_workflow", workflow_config=workflow_config)
        self.node1 = Node1(self.workflow_config)
        self.node2 = Node2(self.workflow_config)
        self.node3 = Node3(self.workflow_config)

        # initialize dataflow
        self.define_graph()

    def define_graph(self):
        self.node1.set_output_nodes(self.node2)
        self.node2.set_output_nodes(self.node3)
        self.start_node = self.node1
```
