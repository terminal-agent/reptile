# Editor Workflow

## Overview

`EditorWorkflow` is an automated workflow that uses an LLM as a supervisor to provide feedback and editing capabilities, reducing the need for human intervention. The `EditorWorkflow` implements an automated supervision system where a separate LLM (editor) acts as a supervisor to review, provide feedback, and edit the outputs of the main LLM worker. This creates a hierarchical AI system with automated quality control.

Its key features include:

- **Automated Supervision**:
    - LLM Supervisor: Uses a separate LLM model as an editor/supervisor
    - Automatic Feedback: Provides automated feedback without human intervention
    - Quality Control: Ensures output quality through automated review
    - Iterative Improvement: Allows the worker LLM to improve based on supervisor feedback

- **Editor Capabilities**:
    - Reviews worker LLM outputs for accuracy and completeness
    - Provides constructive feedback for improvement
    - Can edit and modify worker outputs when necessary
    - Supports "LGTM" (Looks Good To Me) approval for satisfactory outputs


## Node Flow

The dataflow among nodes is as follows:

```
InitPromptNode → LLMNode ↔ EditorNode ↔ TerminalNode
```

1. **InitPromptNode**: Sets up the initial prompt and context for the workflow
2. **LLMNode**: Generates responses and commands (the worker LLM)
3. **EditorNode**: Reviews and provides feedback on the worker's output (the supervisor LLM)
4. **TerminalNode**: Executes commands and returns results

## Use Cases

- **Automated Development**: Fully automated AI agent development with minimal human oversight
- **Quality Assurance**: Automated quality control for AI-generated content
- **Scalable Operations**: Large-scale operations where human supervision is not feasible
- **Consistent Standards**: Maintaining consistent output quality across multiple executions

## Configuration

The EditorWorkflow requires:
- **Worker LLM**: The main LLM model for task execution
- **Editor LLM**: The supervisor LLM model for review and feedback
- **Supervisor Prompts**: Specialized prompts for the editor's supervision role

## Implementation Details

The `EditorNode` inherits from UserActionNode but replaces human interaction with LLM supervision:
- Uses `SUPERVISOR_PROMPT` and `SUPERVISOR_SYSTEM_PROMPT` for editor guidance
- Implements automated feedback generation
- Supports iterative improvement cycles
- Maintains the same workflow structure as AutopilotWorkflow but with automated supervision
