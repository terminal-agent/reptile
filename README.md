# Terminal Agent

## 🔎 Table of Contents

- [📝 Overview](#-overview)
- [🚀 Setup](#-setup)
  - [📍 Run Locally](#-run-locally)
  - [🐳 Run with Docker](#-run-with-docker)
- [📚 Documentation](#-documentation)
  - [🚀 Get Started](#-get-started)
  - [⚙️ Basic Usage](#️-basic-usage)
  - [🔧 Developer Reference](#-developer-reference)
  - [📋 Developer Guideline](#-developer-guideline)
  - [📝 Task Reference](#-task-reference)

## 📝 Overview

Reptile is a Terminal Agent that enables interaction with an LLM agent directly in your terminal. The agent can execute any command or custom CLI tool to accomplish tasks, and users can define their own tools and commands for the agent to utilize.


<table>
<tr>
<td width="50%">
<a href="https://terminal-agent.github.io/reptile/get_started/quickstart.html"><strong>Terminal UI</strong></a> (<code>autopilot run</code>)
</td>
<td>
<a href="https://terminal-agent.github.io/reptile/basic_usage/user_interface.html"><strong>Web UI</strong></a> (<code>autopilot gradio</code>)
</td>
</tr>
<tr>
<td width="50%">

  ![tui-case](https://github.com/terminal-agent/terminal-agent.github.io/blob/main/content/blog/workflow/cases/tui-file-inspection.gif?raw=true)

</td>
<td>

  ![web-case](https://github.com/terminal-agent/terminal-agent.github.io/blob/main/content/blog/workflow/cases/webui-stock-case-edit.gif?raw=true)

</td>
</tr>
<tr>
  <td>
    <a href="https://terminal-agent.github.io/reptile/basic_usage/evaluation.html"><strong>Batch Evaluation</strong></a> (<code>autopilot evaluate</code>)
  </td>
  <td>
    <a href="https://github.com/terminal-agent/reptile/blob/main/tools/webTrajViewer.html"><strong>Trajectory Viewer</strong></a>
  </td>
<tr>
<tr>

<td>

![batch-eval](https://github.com/terminal-agent/terminal-agent.github.io/blob/main/content/blog/workflow/cases/batch-eval-tbench.gif?raw=true)

</td>

<td>

![data-viewer](https://github.com/terminal-agent/terminal-agent.github.io/blob/main/content/blog/workflow/cases/data-viewer.gif?raw=true)

</td>
</tr>
</table>

## 🚀 Setup

This section will guide you through the installation and setup of the Terminal Agent.

### 📍 Run locally

**Step 1. Install autopilot**

```sh
# Git clone this repo
git lfs install  # make sure this succeeds, otherwise you may need to install lfs first.
git clone git@github.com:terminal-agent/reptile.git --recurse-submodules

# Install the autopilot package
cd reptile

# if you are a developer, you can install the package in development mode
pip install -v -e .

# otherwise install as a normal user.
# pip install -v .
```

**Step 2. Run the agent**

```sh
# initialize
autopilot config init

# run the agent
autopilot run --terminal
```

### 🐳 Run Terminal-Bench or SWE-Bench in Sandbox

```sh
# Terminal-bench task example
autopilot evaluate --benchmark terminal_bench --task hello-world --terminal --interaction interactive

# SWE-bench task example
autopilot evaluate --benchmark swe_bench --task requests-863 --terminal --interaction interactive

# SWE-Gym task example
python tools/swegym/build_swe_tasks.py -t pandas-dev__pandas-47504
autopilot evaluate --benchmark swegym --task pandas-dev__pandas-47504 --terminal --interaction interactive
```

## 📚 Documentation

### 🚀 Get Started

- [Quickstart Guide](docs/get_started/quickstart.md) - Get up and running quickly
- [Run Sandbox](docs/get_started/run_sandbox.md) - Running Terminal-Bench or SWE-Bench in sandbox
- [CLI Design](docs/get_started/cli_design.md) - Command line interface design
- [Tools](docs/get_started/tools.md) - Available tools and utilities

### ⚙️ Basic Usage

- [Annotation](docs/basic_usage/annotation.md) - Annotation system usage
- [LLM Service](docs/basic_usage/llm_service.md) - Large language model service configuration
- [Evaluation](docs/basic_usage/evaluation.md) - Evaluation framework and metrics
- [User Interface](docs/basic_usage/user_interface.md) - User interface components

### 🔧 Developer Reference

- [Workflow Design](docs/dev_ref/workflow_design.md) - Workflow architecture and design
- [Workflow Components](docs/dev_ref/workflow/index.rst) - Detailed workflow components
- [Hooks System](docs/dev_ref/hooks/index.rst) - Hooks and event system
- [Nodes](docs/dev_ref/nodes/index.rst) - Node-based execution system

### 📋 Developer Guideline

- [Development for Autopilot](docs/dev_guide/dev_for_autopilot.md) - Development guidelines for autopilot
- [Code Standards](docs/dev_guide/code_standards.md) - Coding standards and best practices

### 📝 Task Reference

- [SWE Task Design](docs/task_ref/swe_task_design.md) - Software engineering task design

## Citation

If you find Reptile useful in your research or applications, please cite:

```bibtex
@misc{reptile2025workflow,
  title={Reptile: Terminal-Agent with Human-in-the-loop Learning},
  author={Dou, Longxu and Li, Shenggui and Du, Cunxiao and Wang, Tianduo and Zhang, Tianjie and Liu, Tianyu and Chen, Xianwei and Tang, Chenxia and Zhao, Yuanheng and Lin, Min},
  year={2025},
  howpublished={\url{https://terminal-agent.github.io/blog/workflow/}},
  note={Blog}
}
```
