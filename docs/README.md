# Documentation

We recommend new contributors to start from writing documentation, which helps you quickly understand the Annotation codebase.
Most documentation files are located under the `docs/` folder.

## Quick Start for Build Doc Locally

### Install Dependency

```bash
apt-get update && apt-get install -y pandoc parallel retry
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Add New Documentation

You can add a markdown file to the `docs` folder and add the file to the `index.rst` file.

```bash
# build html
make html

# serve this thml for viewing
make serve
```

## Doc Index
### 🚀 Get Started

- [Quickstart Guide](get_started/quickstart.md) - Get up and running quickly
- [Run Sandbox](get_started/run_sandbox.md) - Running Terminal-Bench or SWE-Bench in sandbox
- [CLI Design](get_started/cli_design.md) - Command line interface design
- [Tools](get_started/tools.md) - Available tools and utilities

### ⚙️ Basic Usage

- [Annotation](basic_usage/annotation.md) - Annotation system usage
- [LLM Service](basic_usage/llm_service.md) - Large language model service configuration
- [Evaluation](basic_usage/evaluation.md) - Evaluation framework and metrics
- [User Interface](basic_usage/user_interface.md) - User interface components

### 🔧 Developer Reference

- [Workflow Design](dev_ref/workflow_design.md) - Workflow architecture and design
- [Workflow Components](dev_ref/workflow/index.rst) - Detailed workflow components
- [Hooks System](dev_ref/hooks/index.rst) - Hooks and event system
- [Nodes](dev_ref/nodes/index.rst) - Node-based execution system

### 📋 Developer Guideline

- [Development for Autopilot](dev_guide/dev_for_autopilot.md) - Development guidelines for autopilot
- [Code Standards](dev_guide/code_standards.md) - Coding standards and best practices

### 📝 Task Reference

- [SWE Task Design](task_ref/swe_task_design.md) - Software engineering task design
