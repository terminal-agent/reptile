# Annotation

## Overview

To annotate the trajectory for code-agent, we need apply expert-level annotation.

We have two types of tasks:
- (ongoing) Software Engineering -> we choose SWEGym as training set.
- Terminal Task -> we are working on problem collection.

## Build SWEGym tasks

This script transfers the [original swegym huggingface-dataset](https://huggingface.co/datasets/SWE-Gym/SWE-Gym) instance into agent-readable task format.
The generated tasks will be created under `external/swegym/tasks`.

```sh
### build specific tasks
python tools/swegym/build_swe_tasks.py -t $TASK_ID

### build dataset in target interval
python tools/swegym/build_swe_tasks.py -s $START_IDX -e $END_IDX

### build whole dataset
python tools/swegym/build_swe_tasks.py
```
`START_IDX` and `END_IDX` indicate the huggingface dataset range.

Warning: don't annotate the problem with prefix `project-monai__monai`, since their docker size is too large.


## Quickstart for annotation

```
# Terminal-bench task example
autopilot evaluate --benchmark terminal_bench --task hello-world --terminal --interaction interactive

# SWE-bench task example
autopilot evaluate --benchmark swe_bench --task requests-863 --terminal --interaction interactive

# SWE-Gym task example
autopilot evaluate --benchmark swegym --task pandas-dev__pandas-47504 --terminal --interaction interactive
```

## Annotation Principle

First look at https://github.com/terminal-agent/AnnotationGuidelines for get the annotation principle.

If you have any other question, contact cunxiao and longxu.
