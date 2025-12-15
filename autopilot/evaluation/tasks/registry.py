from typing import List


class TaskRegistry:
  """Registry for evaluation tasks.

  Usage:

  @TASKS.register("task_name")
  class MyTask:
      ...
  """

  def __init__(self):
    self.tasks = {}

  def register(self, name: str):
    def decorator(cls):
      if name in self.tasks:
        raise ValueError(f"Task {name} is already registered.")
      self.tasks[name] = cls
      return cls

    return decorator

  def get(self, name: str):
    if name not in self.tasks:
      raise ValueError(f"Task {name} is not registered.")
    return self.tasks[name]

  def list_tasks(self) -> List[str]:
    return list(self.tasks.keys())


TASKS = TaskRegistry()
