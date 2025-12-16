# Run With Sandbox

## Overview

Terminal Agent supports running tasks in sandbox mode. This means the commands are executed in an isolated docker container while the user interaction plane still lies in your host machine. This is useful when you want to run a task in a isolated environment without polluting your host machine.

## Run Benchmarks in Sandbox

We have compiled several benchmarks in our repository for you to evaluate the performance of the terminal agent. These are mainly coding tasks so we run them in sandbox mode to ensure the environment is isolated and correctly built.

```sh
# Terminal-bench task example
autopilot evaluate --benchmark terminal_bench --task hello-world --terminal --interaction interactive

# SWE-bench task example
autopilot evaluate --benchmark swe_bench --task requests-863 --terminal --interaction interactive

# SWE-Gym task example
python tools/swegym/build_swe_tasks.py -t pandas-dev__pandas-47504
autopilot evaluate --benchmark swegym --task pandas-dev__pandas-47504 --terminal --interaction interactive
```
