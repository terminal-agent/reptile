
<div align="center">
<a href="https://terminal-agent.github.io/blog/"><img src="https://github.com/terminal-agent/terminal-agent.github.io/blob/main/static/img/terminal_agent_logo.png?raw=true" alt="terminal-agent banner" style="height: 10em"/></a>
</div>


<div align="center">

[![Docs](https://img.shields.io/badge/Docs-green?style=for-the-badge&logo=materialformkdocs&logoColor=white)](https://mini-swe-agent.com/latest/)
[![Blogs](https://img.shields.io/badge/Blogs-darkgreen?style=for-the-badge&logo=blogger&logoColor=white)](https://terminal-agent.github.io/blog/)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-terminal--agent%2Freptile-blue?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAyCAYAAAAnWDnqAAAAAXNSR0IArs4c6QAAA05JREFUaEPtmUtyEzEQhtWTQyQLHNak2AB7ZnyXZMEjXMGeK/AIi+QuHrMnbChYY7MIh8g01fJoopFb0uhhEqqcbWTp06/uv1saEDv4O3n3dV60RfP947Mm9/SQc0ICFQgzfc4CYZoTPAswgSJCCUJUnAAoRHOAUOcATwbmVLWdGoH//PB8mnKqScAhsD0kYP3j/Yt5LPQe2KvcXmGvRHcDnpxfL2zOYJ1mFwrryWTz0advv1Ut4CJgf5uhDuDj5eUcAUoahrdY/56ebRWeraTjMt/00Sh3UDtjgHtQNHwcRGOC98BJEAEymycmYcWwOprTgcB6VZ5JK5TAJ+fXGLBm3FDAmn6oPPjR4rKCAoJCal2eAiQp2x0vxTPB3ALO2CRkwmDy5WohzBDwSEFKRwPbknEggCPB/imwrycgxX2NzoMCHhPkDwqYMr9tRcP5qNrMZHkVnOjRMWwLCcr8ohBVb1OMjxLwGCvjTikrsBOiA6fNyCrm8V1rP93iVPpwaE+gO0SsWmPiXB+jikdf6SizrT5qKasx5j8ABbHpFTx+vFXp9EnYQmLx02h1QTTrl6eDqxLnGjporxl3NL3agEvXdT0WmEost648sQOYAeJS9Q7bfUVoMGnjo4AZdUMQku50McDcMWcBPvr0SzbTAFDfvJqwLzgxwATnCgnp4wDl6Aa+Ax283gghmj+vj7feE2KBBRMW3FzOpLOADl0Isb5587h/U4gGvkt5v60Z1VLG8BhYjbzRwyQZemwAd6cCR5/XFWLYZRIMpX39AR0tjaGGiGzLVyhse5C9RKC6ai42ppWPKiBagOvaYk8lO7DajerabOZP46Lby5wKjw1HCRx7p9sVMOWGzb/vA1hwiWc6jm3MvQDTogQkiqIhJV0nBQBTU+3okKCFDy9WwferkHjtxib7t3xIUQtHxnIwtx4mpg26/HfwVNVDb4oI9RHmx5WGelRVlrtiw43zboCLaxv46AZeB3IlTkwouebTr1y2NjSpHz68WNFjHvupy3q8TFn3Hos2IAk4Ju5dCo8B3wP7VPr/FGaKiG+T+v+TQqIrOqMTL1VdWV1DdmcbO8KXBz6esmYWYKPwDL5b5FA1a0hwapHiom0r/cKaoqr+27/XcrS5UwSMbQAAAABJRU5ErkJggg==)](https://deepwiki.com/terminal-agent/reptile)

</div>



## 📝 Overview

Reptile is a Terminal Agent that enables interaction with an LLM agent directly in your terminal. The agent can execute any command or custom CLI tool to accomplish tasks, and users can define their own tools and commands for the agent to utilize.


Compared with other CLI agents (e.g., Claude Code and Mini SWE-Agent), Reptile stands out for two reasons:

- **Terminal-only beyond Bash-only**: Simple and stateful execution, which is more efficient than bash-only (you don't need to specify the environment in every command). It doesn't require the complicated MCP protocol—just a naive bash tool under the REPL protocol.

- **Human-in-the-Loop Learning**: Users can inspect every step and provide prompt feedback, i.e., give feedback under the USER role or edit the LLM generation under the ASSISTANT role.


<figure style="text-align: center; margin: 1rem 0;">
  <img src="https://hackmd.io/_uploads/Syidwml7be.png" style="width: 60%; display: block; margin: 0 auto;">
</figure>


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

### Demonstrations

Click on the videos below to watch:

<table>
  <tr>
    <td width="50%">
      <a href="https://www.youtube.com/watch?v=_ENWi5uxupo">
        <img src="https://img.youtube.com/vi/_ENWi5uxupo/0.jpg" alt="Reptile Quickstart" width="100%">
      </a>
      <p align="center">Quickstart in Two Minutes</p>
    </td>
    <td width="50%">
      <a href="https://www.youtube.com/watch?v=izcwX2tMsnU&t=2s">
        <img src="https://img.youtube.com/vi/izcwX2tMsnU/0.jpg" alt="Reptile Annotation" width="100%">
      </a>
      <p align="center">Human-in-the-Loop  Annotation</p>
    </td>
  </tr>
</table>


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

We maintain a comprehensive [documentation website](https://terminal-agent.github.io/reptile/) that covers both basic usage and advanced features of Reptile.

For offline access, you can also browse the documentation locally via the [doc index](docs/README.md).

## 📝 Open Blogs

We maintain a series of blog posts to document our progress and share insights.

- [Terminal Tool: How to detect the boundary of REPL](https://terminal-agent.github.io/blog/tool/)
- [Workflow: How to achieve human-in-the-loop learning](https://terminal-agent.github.io/blog/workflow/)
- [Data: How to achieve on-policy annotation for better learning](https://terminal-agent.github.io/blog/annotation/)
- [WIP] RL Training

We hope our lessons learned and experiences can accelerate the development of autonomous/AGI agents.

## Acknowledgement

We are grateful for the excellent community work that has inspired this project, including [terminal-bench](https://www.tbench.ai/) and [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent). We sincerely thank the community for their valuable contributions and insights.

## Citation

If you find Reptile useful in your research or applications, please cite:

```bibtex
@misc{reptile2025,
  title={Reptile: Terminal-Agent with Human-in-the-loop Learning},
  author={Dou, Longxu and Du, Cunxiao and Li, Shenggui and Wang, Tianduo and Zhang, Tianjie and Liu, Tianyu and Chen, Xianwei and Tang, Chenxia and Zhao, Yuanheng and Lin, Min},
  year={2025},
  url={https://github.com/terminal-agent/reptile},
  note={GitHub repository}
}
```
