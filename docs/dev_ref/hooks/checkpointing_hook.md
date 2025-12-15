# Checkpointing Hook

## Overview

`CheckpointingHook` automatically saves workflow state to Git repositories for version control and recovery.

Its key features include:

- **Git Integration**
    - Auto Git Init: `self.git("init")` - Initializes Git repository
    - Automatic Commits: `self.git("commit", "-m", "checkpoint")` - Commits changes
    - Session Management: Creates unique session names with timestamps

- **Checkpoint Management**
    - Size Validation: Checks checkpoint size before committing
    - User Confirmation: Prompts user for large checkpoints
    - Automatic Disable: Disables hook if user declines large checkpoints

## Hook Lifecycle

- **Pre-run**: Initializes repository
- **Post-node**: Commits after each node execution
