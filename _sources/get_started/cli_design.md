# Autopilot CLI

## Overview

In `autopilot` package, we wrap various functionalities into a CLI interface. This CLI is designed to be user-friendly and easy to use. It is the primary way to interact with the application and used to manage the application's configuration, data, and operations.

## Commands

### Run Management

- Start a new autopilot run

```sh
autopilot run [-t --terminal] [-m --model] [-f --task-file] [-e --eval-script]
```

`-t --terminal`: whether to create a new tab to showcase the actions taken by the agent in the terminal.
`-m --model`: the model to use for the autopilot run. This will be the name of the model in the configuration file.
`-f --task-file`: the path to the task file to use for the autopilot run. The task file should follow terminal-bench format.
`-e --eval-script`: the path to the evaluation script to use for the autopilot run after performing the task. This is used together with the `-f --task-file` flag.

Some more arguments can be found via `autopilot run --help`.

- List all autopilot runs

```sh
autopilot list
```

This will list all the tmux sessions that are running autopilot.

- Kill autopilot runs

```sh
autopilot run kill [-i --id] [-a --all]
```

`-i --id`: the id of the autopilot run to kill. This is the id of the tmux session.
`-a --all`: whether to kill all autopilot runs. This cannot be used together with the `-i --id` flag.

### Manage configuration

You can use the following commands to manage the configuration file.

```sh
# initialize the configuration file
autopilot config init

# view the configuration file
autopilot config view

# edit the configuration file
autopilot config edit

# update the configuration file with the latest tool list
autopilot config update
```

Please note that `autopilot config init` will create a new configuration file only when there is no configuration file found. The configuration file is placed at `~/.config/autopilot/config.yaml`.
