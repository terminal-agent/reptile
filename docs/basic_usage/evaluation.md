# Evaluation


## Overview

We have 5 types of tasks for evaluation:
- Software Engineering: SWEbench-verified, SWE-rebench(WIP).
- Terminal Task: Terminal-bench
- Context Management: LoCoMo
- General LLM: MMLU-Pro, GSM8K
- Agent Task: Tau-2 (WIP)

## Build SWEBench-Verified tasks

This script transfers the [original swebench-verified huggingface-dataset](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified) instance into agent-readable task format.
The generated tasks will be created under `external/swebench-verified/tasks`.

```sh
python tools/swegym/build_swe_tasks.py --swebench
```

## Benchmark

Some examples of how to evaluate different benchmarks are shown below.

- **Terminal Bench**
```
# single-eval
autopilot evaluate \
--benchmark terminal_bench \
--task hello-world \
--interaction executive_only \
--eval-criteria rule-based \
--no-log-to-github --no-log-to-mongodb

# batch-eval
autopilot evaluate \
--parallel 16 \
--benchmark terminal_bench \
--interaction executive_only \
--eval-criteria rule-based \
--no-log-to-github --no-log-to-mongodb
```

**SWEBench-verified Verified**

```
# single-eval
autopilot evaluate \
--benchmark swebench_verified \
--task astropy__astropy-12907 \
--interaction executive_only \
--eval-criteria classified-pytest \
--no-log-to-github --no-log-to-mongodb

# batch-eval
autopilot evaluate \
--parallel 16 \
--benchmark swebench_verified \
--interaction executive_only \
--eval-criteria classified-pytest \
--no-log-to-github --no-log-to-mongodb
```

**MMLU-Pro Benchmark**

```
# single-eval
autopilot evaluate \
--benchmark mmlu_pro \
--task 1 \
--interaction executive_only \
--eval-criteria string-match \
--no-log-to-github --no-log-to-mongodb

# single-eval with naive interaction
autopilot evaluate \
--benchmark mmlu_pro \
--task 1 \
--interaction naive \
--cache-level naive \
--eval-criteria naive --no-log-to-github --no-log-to-mongodb

# batch-eval
autopilot evaluate \
--benchmark mmlu_pro \
--parallel 20 \
--interaction executive_only \
--eval-criteria string-match \
--no-log-to-github --no-log-to-mongodb

# batch-eval with naive interaction
autopilot evaluate \
--benchmark mmlu_pro \
--interaction naive \
--parallel 20 \
--eval-criteria naive \
--cache-level naive \
--no-log-to-github --no-log-to-mongodb
```

**LoCoMo Benchmark**

```
# single-eval
autopilot evaluate \
--benchmark locomo \
--task 0_1 \
--interaction executive_only \
--eval-criteria llm-judge \
--no-log-to-github --no-log-to-mongodb

# batch-eval
autopilot evaluate \
--benchmark locomo \
--parallel 16 \
--interaction executive_only \
--eval-criteria llm-judge \
--no-log-to-github --no-log-to-mongodb
```

**GSM8K Benchmark**

```
# single-eval
autopilot evaluate \
--benchmark gsm8k \
--task 1 \
--interaction executive_only \
--eval-criteria string-match \
--no-log-to-github --no-log-to-mongodb

# single-eval with naive interaction
autopilot evaluate \
--benchmark gsm8k \
--task 1 \
--interaction naive \
--eval-criteria naive \
--cache-level naive \
--no-log-to-github --no-log-to-mongodb

# batch-eval
autopilot evaluate \
--benchmark gsm8k \
--parallel 20 \
--interaction executive_only \
--eval-criteria string-match \
--no-log-to-github --no-log-to-mongodb

# batch-eval with naive interaction
autopilot evaluate \
--benchmark gsm8k \
--interaction naive \
--parallel 20 \
--eval-criteria naive \
--cache-level naive \
--no-log-to-github --no-log-to-mongodb
```

## Advanced Function

We have also built some advanced features for better evaluation.

### Batch Eval with Parallel Models
```
autopilot evaluate \
--benchmark terminal_bench \
--parallel 16 \
--model "devstral" \
--model "devstral-sft-0904" \
--interaction executive_only \
--eval-criteria rule-based \
--no-log-to-github --no-log-to-mongodb
```

### Reloading tasks
```
autopilot evaluate \
--benchmark swe_bench \
--task sglang-grep-tree-1 \
--reload sglang-grep-tree-1-20250707-144905-306e:1:5 \
--interaction interactive \
--no-log-to-github --no-log-to-mongodb
```

### Single Eval on Reload Task
```
autopilot evaluate \
--benchmark swe_bench \
--task sglang-grep-tree-1 \
--reload sglang-grep-tree-1-20250707-144905-306e:1:5 \
--reload-eval-path external/reload-config/grep-tree-reload-eval.yml \
--interaction executive_only \
--eval-criteria classified-pytest \
--no-log-to-github --no-log-to-mongodb
```
where [external/reload-config/grep-tree-reload-eval.yml](https://github.com/terminal-agent/reptile/blob/main/external/reload-config/grep-tree-reload-eval.yml) stores the evaluation configs for reload.

### Batch Eval on Reload Tasks
```
autopilot evaluate \
--benchmark swe_bench \
--reload-eval-path external/reload-config/grep-tree-reload-eval.yml \
--interaction executive_only \
--eval-criteria classified-pytest \
--no-log-to-github --no-log-to-mongodb
```
All reload tasks within [external/reload-config/grep-tree-reload-eval.yml](https://github.com/terminal-agent/reptile/blob/main/external/reload-config/grep-tree-reload-eval.yml) will be tested in this batch mode.
