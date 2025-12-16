# Reload Hook

## Overview

`ReloadHook` enables workflow reloading from remote GitHub repositories, allowing workflows to resume from previous states.

Its key features include:

- **Repository Reloading**
    - Prefix Processing: Processes `self.prefix` list of (role, content) tuples
    - Command Re-execution: Re-executes terminal commands from previous session
    - State Restoration: Restores workflow state from previous execution

- **Command Processing**
    - Terminal Commands: `terminal_node._exec_and_return_output(cmd_type, cmd)` - Re-executes commands
    - Terminal Text: `terminal_node.get_terminal_text()` - Gets current terminal state
    - Role Mapping: Maps string roles to Role enums for context restoration

- **Workflow Continuation**
    - Executive Mode: `DirectActionExtraInfo(action="p", target_step=data.num_steps - 1)` - Auto-proceed in executive mode
    - Node Selection: Sets `workflow.start_node` based on last step type
    - Context Integration: Integrates reloaded context into current workflow


## Configuration
- **Prefix Data**: `prefix: List[Tuple[str, str]]` - List of (role, content) pairs to reload
