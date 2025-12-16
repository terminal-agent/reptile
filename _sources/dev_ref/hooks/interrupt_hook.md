# Interrupt Hook

## Overview

`InterruptHook` provides timeout and step limit controls for workflow execution, enabling automatic termination based on time or step count.

Its key features include:

- **Timeout Control**
    - Timeout Monitoring: `Thread(target=monitor_executor, daemon=True)` - Background timeout monitoring
    - Automatic Termination: `self.event.set()` - Sets interrupt event on timeout
    - Termination Reason: `data.termination_reason = f"Timeout {self.timeout}s reached"`

- **Step Limit Control**
    - Step Counting: `len(data.history) > self.max_steps` - Monitors step count
    - Max Steps Enforcement: Terminates workflow when step limit exceeded
    - Step Validation: Validates step count against configured maximum

- **Exception Handling**
    - LLM API Errors: `isinstance(data.last_exception, LLMAPIError)`
    - Context Length: `isinstance(data.last_exception, LLMMaxContextLengthExceeded)`
    - User Interruption: `isinstance(data.last_exception, LLMInterrupted)`

## Configuration

This hook launches a background thread to monitor the execution time and step count. Users can configure the following parameters to control the behavior of the hook:

- **Timeout**: `timeout: Optional[int]` - Maximum execution time in seconds
- **Max Steps**: `max_steps: Optional[int]` - Maximum number of workflow steps
