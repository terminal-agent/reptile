# Init Prompt Node


## Overview

`InitPromptNode` is the starting node of the workflow. It asks the user for an initial prompt. Its duties can be summarized as follows:

- **Prompt Setup**: Establishes initial prompt for workflow
- **Context Initialization**: Prepares initial context data
- **Workflow Entry**: Serves as starting node for workflows
- **State Preparation**: Sets up initial workflow state

## Implementation

```python
def __init__(self, terminal: Term, workflow_config: WorkflowConfig):
    super().__init__(
        name="init-prompt",
        role=Role.USER,
        workflow_config=workflow_config,
        terminal=terminal,
    )
```

## Use Cases
- **Workflow Start**: Initializes new workflow instances
- **Context Setup**: Sets up initial context and state
- **Environment Preparation**: Prepares execution environment
