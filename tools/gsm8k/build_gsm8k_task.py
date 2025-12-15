import json
import os

from datasets import load_dataset
from tqdm import trange


def main():
  dataset = load_gsm8k()
  for split in ["train"]:
    for i in trange(len(dataset[split])):
      name = str(i)
      build_task(name, dataset[split][i])


def build_task(name, data):
  prefix = "external/gsm8k"
  dst_folder = f"{prefix}/tasks/{name}"
  os.makedirs(dst_folder, exist_ok=True)
  with open(f"{dst_folder}/instance.json", "w") as f:
    json.dump(data, f)


def load_gsm8k():
  dataset = load_dataset("openai/gsm8k", "main")
  train_df, test_df = dataset["train"], dataset["test"]

  return {"train": train_df, "test": test_df}


if __name__ == "__main__":
  main()
