
### reloading swebench/terminal tasks
```
autopilot evaluate \
--benchmark swe_bench \
--task sglang-grep-tree-1 \
--reload sglang-grep-tree-1-20250707-144905-306e:1:5 \
--interaction interactive --terminal
```

### single eval on a reload task
```
autopilot evaluate \
--benchmark swe_bench \
--task sglang-grep-tree-1 \
--reload sglang-grep-tree-1-20250707-144905-306e:1:5 \
--reload-eval-path external/reload-config/grep-tree-reload-eval.yml
```
where [external/reload-config/grep-tree-reload-eval.yml](https://github.com/terminal-agent/reptile/blob/main/external/reload-config/grep-tree-reload-eval.yml) stores the evaluation configs for reload.

### batch eval on reload tasks
```
autopilot evaluate \
--benchmark swe_bench \
--reload-eval-path external/reload-config/grep-tree-reload-eval.yml
```
All reload tasks within [external/reload-config/grep-tree-reload-eval.yml](https://github.com/terminal-agent/reptile/blob/main/external/reload-config/grep-tree-reload-eval.yml) will be tested in this batch mode.

### batch eval with parallel models
```
autopilot evaluate \
--benchmark swe_bench \
--model "devstral" \
--model "devstral-sft-0904"
```

## MMLU Pro Benchmark
```
# single-eval
autopilot evaluate \
--benchmark mmlu_pro \
--task 1 --terminal \
--interaction interactive \
--eval-criteria string-match --no-log-to-github --no-log-to-mongodb

# single-eval with naive interaction
autopilot evaluate \
--benchmark mmlu_pro \
--task 1 --terminal \
--interaction naive \
--eval-criteria naive --no-log-to-github --no-log-to-mongodb --cache-level naive

# batch-eval
autopilot evaluate \
--benchmark mmlu_pro \
--interaction executive_only \
--eval-criteria string-match --no-log-to-github --no-log-to-mongodb

# batch-eval with naive interaction
autopilot evaluate \
--benchmark mmlu_pro \
--interaction naive \
--parallel 20 \
--eval-criteria naive --no-log-to-github --no-log-to-mongodb --cache-level naive
```

## LoCoMo Benchmark
```
# single-eval
autopilot evaluate \
--benchmark locomo \
--task 0_1 --terminal \
--interaction interactive \
--eval-criteria llm-judge

# batch-eval
autopilot evaluate \
--benchmark locomo \
--interaction executive_only \
--eval-criteria llm-judge --no-log-to-github --no-log-to-mongodb
```
