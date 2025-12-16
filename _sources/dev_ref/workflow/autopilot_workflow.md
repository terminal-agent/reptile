# Autopilot Workflow


## Overview

`AutopilotWorkflow` is the standard interactive workflow with human supervision, designed for interactive development and debugging scenarios. The `AutopilotWorkflow` provides a comprehensive interactive experience where users can supervise, guide, and intervene in the AI agent's execution process. It supports multiple user actions including proceed, feedback, edit, resample, and record operations.


Its key features include:

- **User Actions Support**:
    - Proceed (p): Continue with the current execution flow
    - Feedback (f): Provide feedback to guide the LLM's next response
    - Edit (e)**: Edit a specific step's content
    - Resample (n): Regenerate a specific step with new content
    - Record (r): Record turning points for future reference

- **Interactive Capabilities**:
    - Real-time supervision of AI agent execution
    - Ability to intervene at any step in the workflow
    - Support for branching and backtracking
    - Context preservation across user interventions

## Node Flow

The dataflow among nodes is as follows:

```
InitPromptNode → LLMNode ↔ UserActionNode ↔ TerminalNode
```

1. **InitPromptNode**: Sets up the initial prompt and context for the workflow
2. **LLMNode**: Generates responses and commands based on the context
3. **UserActionNode**: Provides user interaction points for supervision and control
4. **TerminalNode**: Executes commands and returns results


## Use Cases

- **Development**: Interactive development and debugging of AI agents
- **Learning**: Understanding how AI agents solve problems step by step
- **Quality Control**: Manual supervision and correction of AI outputs
- **Training**: Creating training data through human-AI collaboration


## Configuration

The AutopilotWorkflow can be configured through the `WorkflowConfig` with various interaction modes:

- `INTERACTIVE`: Full interactive mode with user supervision
- `EXECUTIVE_ONLY`: Minimal interaction, mostly automated execution
- `INTERACTIVE_BY_ZMQ`: Remote interaction via ZMQ messaging
