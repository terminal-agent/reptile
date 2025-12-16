# Oracle Workflow

## Overview

`OracleWorkflow` is a simple workflow designed for testing and validation scenarios, providing standard solutions for benchmarking and solution verification.The `OracleWorkflow` implements a straightforward linear execution flow that provides known, correct solutions. It is primarily used for testing, validation, and benchmarking purposes where the expected output is already known.

Its key features include:

- **Standard Solutions**:
    - Gold Solutions: Provides pre-defined, correct solutions
    - Deterministic Output: Consistent, predictable results
    - Validation Support: Enables comparison with other workflow outputs
    - Benchmarking: Serves as a baseline for performance evaluation

- **Simple Execution**:
    - Linear Flow: Straightforward execution without complex branching
    - Minimal Interaction: No user intervention required
    - Fast Execution: Optimized for quick validation runs
    - Reliable Results: Guaranteed correct output for testing scenarios

This workflow is designed for:
- **Simplicity**: Minimal complexity for reliable testing
- **Consistency**: Same output every time for reliable validation
- **Speed**: Fast execution for efficient testing cycles
- **Isolation**: Independent of AI model performance or variability

## Node Flow

The dataflow among nodes is as follows:

```
InitPromptNode → OracleNode → TerminalNode
```

1. **InitPromptNode**: Sets up the initial prompt and context for the workflow
2. **OracleNode**: Provides the standard/gold solution
3. **TerminalNode**: Executes the solution and returns results


## Use Cases

- **Testing**: Validating that the system can execute known solutions correctly
- **Benchmarking**: Comparing performance of different AI models or approaches
- **Validation**: Ensuring that the terminal execution environment works correctly
- **Quality Assurance**: Verifying that the workflow infrastructure functions properly

## Configuration

The OracleWorkflow requires minimal configuration:
- **Workflow Config**: Basic workflow configuration
- **Terminal Setup**: Terminal environment for command execution
- **Solution Script**: The gold solution script to be executed

## Implementation Details

The OracleNode provides a hardcoded solution:

```bash
bash /tmp/tasks/shared_scripts/solution.sh
```
