# Gradio Hook

## Overview

`GradioHook` communicates with the Gradio application via ZMQ and notifies the application about the different stages of the workflow.

For now, it only sends the `WORKFLOW_READY` signal to the application to tell the application that the workflow is ready to receive further instructions.

## Use Cases

- **Web Interface**: Integration with Gradio web applications
- **Remote Control**: Remote workflow control and monitoring
