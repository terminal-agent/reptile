# Reptile: Terminal Agent with Human-in-the-Loop Learning

## 📝 Overview

Reptile is a Terminal Agent that enables interaction with an LLM agent directly in your terminal. The agent can execute any command or custom CLI tool to accomplish tasks, and users can define their own tools and commands for the agent to utilize.


Compared with other CLI agents (e.g., Claude Code and Mini SWE-Agent), Reptile stands out for two reasons:

- **Terminal-only beyond Bash-only**: Simple and stateful execution, which is more efficient than bash-only (you don't need to specify the environment in every command). It doesn't require the complicated MCP protocol—just a naive bash tool under the REPL protocol.

- **Human-in-the-Loop Learning**: Users can inspect every step and provide prompt feedback, i.e., give feedback under the USER role or edit the LLM generation under the ASSISTANT role.

### ⚡ Functions
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

This section will guide you through the installation and setup of the Reptile.

**Why Choose Reptile?** Unlike other agent tools, Reptile is designed to be developer-friendly: **you can get started quickly without Docker**, and **easily use your own locally deployed LLM service** (OpenAI-compatible API format). We believe a development tool should adapt to how developers want to set it up, not force them into a specific deployment model.

### 📍 Run locally (no sandbox required)

**Step 1. Install autopilot**

```sh
# Git clone this repo
git lfs install  # make sure this succeeds, otherwise you may need to install lfs first.
git clone git@github.com:terminal-agent/reptile.git --recurse-submodules

# If you forget to clone with --recurse-submodules,
# run `git submodule update --init --recursive`


# Install the autopilot package (ensure your python version>=3.11)
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

### Demonstartions
This video shows how to use the Reptile in two minutes.

[![Reptile Quickstart](https://img.youtube.com/vi/_ENWi5uxupo/0.jpg)](https://www.youtube.com/watch?v=_ENWi5uxupo)


This video shows how to do human-in-the-loop sft annotation.

[![Reptile Annotation](https://img.youtube.com/vi/izcwX2tMsnU/0.jpg)](https://www.youtube.com/watch?v=izcwX2tMsnU&t=2s)


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

We host a [documentation website](https://terminal-agent.github.io/reptile/) covering both basic and advanced features of Reptile.

Alternatively, you can view the documentation locally using the [doc index](docs/README.md).

## 📝 Open Blogs

We maintain a series of blog posts to document our progress and share insights.

- [Terminal-Backend: How to detect the boundary of REPL](https://terminal-agent.github.io/blog/tool/)
- [Workflow: the roadmap of Reptile project](https://terminal-agent.github.io/blog/workflow/)
- [Data Annotation: How to make human annotation more effective](https://terminal-agent.github.io/blog/annotation/)
- [WIP] RL Training

We hope our lessons learned and experiences can accelerate the development of autonomous/AGI agents.


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
