## Guideline on how to build SWEGym tasks for annotation and evaluation

### Build SWEGym tasks
```sh
python tools/swegym/build_swe_tasks.py -t $TASK_ID
```
This script transfers a huggingface dataset instance into a terminal-agent task.
The generated tasks will be created under external/swegym/tasks

Or you can
```sh
python tools/swegym/build_swe_tasks.py -s $START_IDX -e $END_IDX
```
`START_IDX` and `END_IDX` indicate the huggingface dataset range.



### Build SWEGym tasks
```sh
python tools/swegym/build_swe_tasks.py --swebench -t $TASK_ID
```
This script transfers a huggingface dataset instance into a terminal-agent task.
The generated tasks will be created under external/swebench-verified/tasks

Or you can
```sh
python tools/swegym/build_swe_tasks.py --swebench -s $START_IDX -e $END_IDX
```
`START_IDX` and `END_IDX` indicate the huggingface dataset range.
