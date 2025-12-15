import argparse
from pathlib import Path

import yaml
from pymongo import MongoClient

from autopilot.config import GLOBAL_CONFIG


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--output-dir", type=str, default="./session_synced")
  parser.add_argument("--force", action="store_true")
  parser.add_argument("--user", type=str)
  parser.add_argument(
    "--session-name-keyword",
    type=str,
  )
  return parser.parse_args()


class MongoDBSyncer:
  def __init__(self):
    self.client = MongoClient(
      f"mongodb://{GLOBAL_CONFIG.telemetry.mongodb.username}:{GLOBAL_CONFIG.telemetry.mongodb.password}@{GLOBAL_CONFIG.telemetry.mongodb.host}:{GLOBAL_CONFIG.telemetry.mongodb.port}"
    )
    self.db = self.client[GLOBAL_CONFIG.telemetry.mongodb.database]
    self.collection = self.db[GLOBAL_CONFIG.telemetry.mongodb.collection]

  def sync_all_data(
    self,
    output_dir: str,
    force: bool = False,
    session_name_keyword: str = None,
    username: str = None,
  ):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # iterate over all sessions
    for session in self.collection.distinct("session_name"):
      session_dst_dir = output_dir.joinpath(session)
      data = self.collection.find_one({"session_name": session})

      if session_dst_dir.exists() and not force:
        continue
      else:
        session_dst_dir.mkdir(parents=True, exist_ok=True)

        session_user_name = data["username"]
        if username and username != session_user_name:
          continue
        if session_name_keyword and session_name_keyword not in session:
          continue

        with open(session_dst_dir.joinpath("history.yml"), "w") as f:
          for item in data["chat_history"]:
            ordered_item = {}
            if "content" in item:
              ordered_item["content"] = item["content"]
            for key in [
              "extra_info",
              "name",
              "role",
              "step",
              "task_id",
              "traj",
            ]:
              if key in item:
                ordered_item[key] = item[key]

            f.write(
              yaml.safe_dump(
                [ordered_item],  # Wrap in list to get the "-" prefix
                sort_keys=False,
                default_flow_style=False,
                width=float("inf"),
              )
            )
            f.write("\n")

        with open(session_dst_dir.joinpath("other_info.yml"), "w") as f:
          yaml.dump(
            dict(model_name=data["model_name"], username=data["username"]), f
          )

        with open(session_dst_dir.joinpath("system_prompt.txt"), "w") as f:
          f.write(data["system_prompt"])


def main():
  args = parse_args()
  syncer = MongoDBSyncer()
  syncer.sync_all_data(
    output_dir=args.output_dir,
    force=args.force,
    session_name_keyword=args.session_name_keyword,
    username=args.user,
  )


if __name__ == "__main__":
  main()
