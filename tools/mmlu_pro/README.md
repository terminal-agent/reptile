## Guideline on how to build MMLU-Pro tasks for annotation and evaluation

### Build MMLU-Pro tasks
```sh
python tools/mmlu_pro/build_mmlu_pro_task.py
```
This script downloads the MMLU-Pro dataset from HuggingFace and converts each instance into a terminal-agent task.
The generated tasks will be created under `external/MMLU-Pro/tasks/`
