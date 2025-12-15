## Guideline on how to build gsm8k tasks for annotation and evaluation

### Build gsm8k tasks
```sh
python tools/gsm8k/build_gsm8k_tasks.py
```
This script transfers a huggingface dataset instance into a terminal-agent task.
The generated tasks will be created under external/gsm8k/tasks
