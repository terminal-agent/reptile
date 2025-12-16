# Quickstart

## Installation

First of all, let's clone the repository.

```sh
# Git clone this repo
git lfs install  # make sure this succeeds, otherwise you may need to install lfs first.
git clone https://github.com/terminal-agent/reptile.git --recurse-submodules

# Install the autopilot package
cd Terminal-Agents
```

Then you can install `autopilot` with the command below:

::::{tab-set}

:::{tab-item} pip

```bash
pip install -v .
```

:::

:::{tab-item} uv

We recommend you to create a new virtual environment for the terminal agent.

```bash
uv venv --python 3.11
source .venv/bin/activate

uv pip install -v .
```

:::

:::{tab-item} developer mode

```
# if using pip
pip install -v -e .[dev]

# if using uv
uv pip install -v -e .[dev]
```

:::

::::

## Run the Agent

Before running the agent, you need to initialize the config. You need to edit this config file to set up the LLM key and optional remote telemetry storage. The init configuration is only a reference configuration, you can modify it according to your needs.

```sh
# initialize the config
autopilot config init

# edit the config
autopilot config edit
```

Next, you can run the agent in terminal mode.

```sh
# run the agent
autopilot run --terminal

# if you want to disable telemetry
autopilot run --terminal --no-log-to-mongodb --no-log-to-github
```

For more details about the CLI, you can refer to the [CLI Design](cli_design.md) page.

You can try the example tasks below to have a try with the terminal agent.

1. Show me the the weather of Singpore right now by API.
2. Calculate the average stock price of SEA over the last three months by calling the Finance API.
