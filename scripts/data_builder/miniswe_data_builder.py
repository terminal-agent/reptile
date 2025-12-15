"""MiniSWE data preparation script for terminal agent training."""

import argparse
import os
import sys
from typing import Dict, Optional

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datasets import load_dataset
from tqdm import tqdm

from autopilot.prompts import SYSTEM_PROMPT
from autopilot.tools import TOOLS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_builder.utils import TEST_FILE, TEST_SAMPLES, TRAIN_FILE

DATASET_NAME = "Kwai-Klear/SWE-smith-mini_swe_agent_plus-trajectories-66k"

autopilot_system_prompt = SYSTEM_PROMPT.format(
  tools_description=TOOLS.get_tools_description()
)


def process_item(item: Dict) -> Optional[Dict]:
  """Process and validate a single dataset item."""
  messages = item if isinstance(item, list) else item.get("messages", item)

  if not isinstance(messages, list) or len(messages) == 0:
    return None

  if messages[-1]["role"] == "user":
    messages = messages[:-1]

  if len(messages) == 0 or len(messages) > 250:
    return None

  # Replace first system message content with autopilot system prompt
  if len(messages) > 0 and messages[0].get("role") == "system":
    messages[0] = {"role": "system", "content": autopilot_system_prompt}

  if "MINI_SWE_AGENT_FINAL_OUTPUT" in messages[-1]["content"]:
    messages[-1]["content"] = messages[-1]["content"].replace(
      "echo MINI_SWE_AGENT_FINAL_OUTPUT && git", "git"
    )

  return {"messages": messages, "tokens": 0, "num_steps": len(messages)}


def process_and_save(dataset, output_file: str, batch_size: int = 1000) -> int:
  """Process dataset and save directly to parquet file using streaming."""
  writer = None
  buffer = []
  total_rows = 0

  print("Processing dataset...")
  for item in tqdm(dataset):
    if processed := process_item(item):
      buffer.append(processed)

      if len(buffer) >= batch_size:
        table = pa.Table.from_pylist(buffer)

        if writer is None:
          writer = pq.ParquetWriter(output_file, table.schema)

        writer.write_table(table)
        total_rows += len(buffer)
        buffer = []

  # Write remaining data
  if buffer:
    table = pa.Table.from_pylist(buffer)
    if writer is None:
      writer = pq.ParquetWriter(output_file, table.schema)
    writer.write_table(table)
    total_rows += len(buffer)

  if writer:
    writer.close()

  return total_rows


def extract_test_set(input_file: str, output_file: str, num_samples: int):
  """Extract first N samples for test set."""
  parquet_file = pq.ParquetFile(input_file)
  batch = next(parquet_file.iter_batches(batch_size=num_samples))

  if len(batch) > num_samples:
    batch = batch.slice(0, num_samples)

  pq.write_table(pa.Table.from_batches([batch]), output_file)
  print(f"Saved {len(batch)} test samples")


def print_statistics(input_file: str):
  """Compute and print dataset statistics."""
  parquet_file = pq.ParquetFile(input_file)
  steps = []

  print("Computing statistics...")
  for batch in parquet_file.iter_batches(batch_size=5000):
    steps.extend(batch.to_pandas()["num_steps"].tolist())

  steps = np.array(steps)

  print("\n" + "=" * 50)
  print(f"Total samples: {len(steps):,}")
  print(
    f"Steps - Min: {np.min(steps)}, Max: {np.max(steps)}, Mean: {np.mean(steps):.1f}"
  )
  print(
    f"Percentiles - 50th: {np.percentile(steps, 50):.1f}, "
    f"90th: {np.percentile(steps, 90):.1f}, 99th: {np.percentile(steps, 99):.1f}"
  )
  print("=" * 50)


def main():
  parser = argparse.ArgumentParser(description="Prepare MiniSWE training data")
  parser.add_argument(
    "--print-detail", action="store_true", help="Print statistics"
  )
  parser.add_argument("--split", default="train", help="Dataset split")
  parser.add_argument(
    "--batch-size",
    type=int,
    default=1000,
    help="Batch size for streaming write",
  )
  args = parser.parse_args()

  script_path = os.path.dirname(os.path.abspath(__file__))
  local_dir = os.path.join(script_path, "data/miniswe-autopilot/")
  os.makedirs(local_dir, exist_ok=True)

  output_train = os.path.join(local_dir, TRAIN_FILE)
  output_test = os.path.join(local_dir, TEST_FILE)

  # Load and process dataset
  print(f"Loading dataset: {DATASET_NAME}")
  dataset = load_dataset(DATASET_NAME, split=args.split, streaming=True)

  # Process and save directly
  total = process_and_save(dataset, output_train, args.batch_size)
  print(f"\n✓ Saved {total:,} training samples")

  # Extract test set
  extract_test_set(output_train, output_test, TEST_SAMPLES)

  # Statistics
  if args.print_detail:
    print_statistics(output_train)

  print("✓ Complete")


if __name__ == "__main__":
  main()
