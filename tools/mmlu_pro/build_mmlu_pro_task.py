import json
import os

from datasets import load_dataset
from tqdm import trange


def main():
  dataset = load_mmlu_pro()
  for i in trange(len(dataset["test"])):
    name = str(i)
    build_task(name, dataset["test"][i])


def build_task(name, data):
  prefix = "external/MMLU-Pro"
  dst_folder = f"{prefix}/tasks/{name}"
  os.makedirs(dst_folder, exist_ok=True)
  with open(f"{dst_folder}/instance.json", "w") as f:
    json.dump(data, f)


def load_mmlu_pro():
  dataset = load_dataset("TIGER-Lab/MMLU-Pro")
  test_df, val_df = dataset["test"], dataset["validation"]

  return {"test": test_df, "val": val_df}


if __name__ == "__main__":
  main()
