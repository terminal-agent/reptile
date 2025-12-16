# Telemetry Hook

## Overview

`TelemetryHook` records workflow data to remote repositories (GitHub) or databases (MongoDB) for analysis and monitoring.

Its key features include:

- **Data Logging**
    - System Prompt: Records system prompts
    - History Tracking: Records workflow history in YAML format
    - Turning Points: Records turning point information for analysis
    - Metadata: Records model information and user details

- **GitHub Integration**
    - Repository Management: Initialize a empty git repo and set the remote URL
    - SSH Authentication: Uses SSH keys for repository access
    - Async Push: Asynchronously push the chat history and other information to the remote repository

- **MongoDB Integration**
    - Database Connection: Create connection to MongoDB
    - Document Storage: Stores the chat history and other information in MongoDB documents
