from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from autopilot.utils import extract_commands


class Role(Enum):
  """
  This is the role of the message.
  """

  USER = "user"
  LLM = "llm"


class MessageType(Enum):
  """
  Different types of messages for the console to process accordingly.
  """

  LOG = "log"
  WARNING = "warning"
  ERROR = "error"
  FORMATTING = "formatting"
  USER_PROMPT = "user_prompt"
  LLM_RESPONSE = "llm_response"
  TERMINAL_RESPONSE = "terminal_response"
  ACTION = "action"
  WORKFLOW_READY = "workflow_ready"
  WORKFLOW_TURN_END = "workflow_turn_end"
  NO_COMMAND_FOUND = "no_command_found"


@dataclass
class VLLMInfo:
  """
  vLLM information structure for LLM responses.

  Args:
      token_ids (Optional[List[int]]): the token ids from LLM response
      prompt_token_ids (Optional[List[int]]): the prompt token ids from LLM request
  """

  token_ids: Optional[List[int]] = None
  prompt_token_ids: Optional[List[int]] = None

  def to_dict(self) -> Dict[str, Any]:
    """
    Convert to dictionary.

    Returns:
      dict: the dictionary representation
    """
    return {
      "token_ids": self.token_ids,
      "prompt_token_ids": self.prompt_token_ids,
    }


@dataclass
class Message:
  """
  This is the message structure to track for the history of the workflow.

  Args:
      role (Role): the role of the message
      name (str): the name of the message
      content (str): the content of the message
      step (int): the step index of the message
      traj (int): the trajectory index of the message
      task_id (int): the task index of the message
      extra_info (Dict[str, Any]): the extra information of the message
  """

  role: Role
  name: str
  content: str
  step: int
  traj: int
  task_id: int
  extra_info: Dict[str, Any] = field(default_factory=dict)

  def to_dict(self):
    """
    Convert the message to a dictionary.

    Returns:
      dict: the dictionary of the message
    """
    return dict(
      role=self.role.value,
      name=self.name,
      content=self.content,
      step=self.step,
      traj=self.traj,
      task_id=self.task_id,
      extra_info=self.extra_info,
    )


@dataclass
class ExtraInfo:
  """
  ExtraInfo is the extra information that a node leaves for its next node.
  """

  pass

  def to_dict(self):
    """
    Convert the extra information to a dictionary.

    Returns:
      dict: the dictionary of the extra information
    """
    return asdict(self)


@dataclass
class EditExtraInfo(ExtraInfo):
  """
  EditExtraInfo contains data regarding the user's edit of a message.
  """

  edit_prefix: Optional[str] = None
  content_before_edit: Optional[str] = None


@dataclass
class DirectActionExtraInfo(ExtraInfo):
  """
  DirectActionExtraInfo contains data regarding the user's direct action.
  """

  action: Optional[str] = None
  target_step: Optional[int] = None


@dataclass
class RedirectedOutputExtraInfo(ExtraInfo):
  """
  RedirectedOutputExtraInfo contains data regarding the redirected output.
  """

  output: Optional[str] = None


@dataclass
class InstructionExtraInfo(ExtraInfo):
  """
  InstructionExtraInfo contains data regarding the user's instruction.
  """

  instruction: Optional[str] = None


@dataclass
class ReloadExtraInfo(ExtraInfo):
  """
  ReloadExtraInfo contains data regarding the reloaded workflow. To indicate whether the reloading has finished in ZMQConsole.
  """

  reloaded_finished: bool = False


class InteractionMode(Enum):
  """
  Different modes of interaction with the user, so that workflow will behave differently under different modes.
  """

  EXECUTIVE_ONLY = "executive_only"
  INTERACTIVE = "interactive"
  INTERACTIVE_BY_ZMQ = "interactive_by_zmq"
  ORACLE = "oracle"
  NAIVE = "naive"


@dataclass
class WorkflowConfig:
  """
  WorkflowConfig contains the configuration for the workflow.

  Args:
    interaction_mode (InteractionMode): the mode of interaction with the user
    system_prompt (str): the system prompt to use for the workflow
    sandbox (Optional[str]): the sandbox to use for the workflow, default to None
    model (Optional[str]): the model to use for the workflow, default to None
    zmq_host (Optional[str]): the host to use for the ZMQ connection, default to None
    zmq_port (Optional[int]): the port to use for the ZMQ connection, default to None
    max_steps (Optional[int]): the maximum number of total steps, default to None
    max_current_steps (Optional[int]): the maximum number of steps in the current branch, default to None
    time_out (Optional[int]): the timeout in seconds, default to None
    strong_scaffold (bool): enable strong scaffold mode to control terminal node behavior, default to False
  """

  interaction_mode: InteractionMode
  system_prompt: str
  sandbox: Optional[str] = None
  model: Optional[str] = None
  zmq_host: Optional[str] = None
  zmq_port: Optional[int] = None
  max_steps: Optional[int] = None
  max_current_steps: Optional[int] = None
  time_out: Optional[int] = None
  strong_scaffold: bool = False


@dataclass
class ContextData:
  """
  This is the data structure to track for the history of the workflow.

  Args:
      history (List[Message]): the history of the workflow, default to an empty list
      current_branch (List[Message]): the current branch of the workflow, default to an empty list
      branch_counter (int): the number of branches in the history, default to 0
      subtask_stack (List[Tuple[int, int]]): the stack of subtasks, default to an empty list
      traj_tracker (Dict[int, int]): track the maximum trajectory of each step, default to an empty dict
      turning_info (Dict[str, Dict[str, List[str]]]): track the turning points, default to an empty dict
      vllm_info_map (Dict[int, VLLMInfo]): track the vLLM info for each step, default to an empty dict
      task_counter (int): the number of tasks, default to 0
      current_task_id (int): the current task id, default to 0
      termination_reason (str): the reason for the termination of the workflow, default to None
      last_exception (Exception): the exception for the termination of the workflow, default to None
  """

  history: List[Message] = field(default_factory=list)
  cmd_history: List[str] = field(default_factory=list)
  current_branch: List[Message] = field(default_factory=list)
  branch_counter: int = 0
  subtask_stack: List[Tuple[int, int]] = field(default_factory=list)

  ### record
  traj_tracker: Dict[int, int] = field(default_factory=dict)
  turning_info: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
  vllm_info_map: Dict[int, VLLMInfo] = field(default_factory=dict)

  ### subtask
  task_counter: int = 0
  current_task_id: int = 0

  ### interruption
  termination_reason: Optional[str] = None
  last_exception: Optional[Exception] = None

  @property
  def last_message(self) -> Optional[Message]:
    """
    Return the last message in the current branch.

    Returns:
        message (Message): the last message in the current branch
    """
    if len(self.current_branch) == 0:
      return None
    return self.current_branch[-1]

  @property
  def num_steps(self) -> int:
    """
    Return the number of steps in the history.

    Returns:
        num_steps (int): the number of steps in the history
    """
    return len(self.current_branch)

  @property
  def num_branches(self) -> int:
    """
    Return the number of branches in the history.

    Returns:
        num_branches (int): the number of branches in the history
    """
    return self.branch_counter + 1

  @property
  def current_branch_idx(self) -> int:
    """
    Return the index of the current branch in the history.

    Returns:
        current_branch_idx (int): the index of the current branch in the history
    """

    return self.branch_counter

  def append(
    self,
    role: str,
    name: str,
    content: str,
    extra_info: Optional[ExtraInfo] = None,
    token_ids: Optional[List[int]] = None,
    prompt_token_ids: Optional[List[int]] = None,
  ) -> None:
    """
    Add the message to the history.

    Args:
        role (Role): the role of the message
        name (str): the name of the message
        content (str): the content of the message
        extra_info (Dict[str, Any]): the extra information of the message, default to an empty dict
        token_ids (Optional[List[int]]): the token ids from LLM response (for vllm)
        prompt_token_ids (Optional[List[int]]): the prompt token ids from LLM request (for vllm)
    """
    step = self.num_steps
    traj = self.current_branch_idx
    current_task_id = self.current_task_id
    message = Message(
      role=Role(role),  # type: ignore[arg-type]
      name=name,
      content=content,
      step=step,
      traj=traj,
      task_id=current_task_id,
      extra_info=extra_info.to_dict() if extra_info else {},
    )
    self.current_branch.append(message)
    self.history.append(message)
    self.traj_tracker[step] = traj
    self.vllm_info_map[step] = VLLMInfo(
      token_ids=token_ids, prompt_token_ids=prompt_token_ids
    )

    commands = extract_commands(content)
    if len(commands) > 0:
      self.cmd_history.append(commands[0][1])

  def branch_at(self, step: int) -> None:
    """
    Branch the history at the given step.

    Args:
        step (int): the step index to check out to a new branch.
    """
    if not (-1 <= step and step < len(self.current_branch)):
      raise IndexError(f"Branch at {step} out of range")
    self.branch_counter += 1
    self.current_branch = self.current_branch[: step + 1]
    # destroy the subtask stack if it becomes out of scope after
    # truncating at index
    while len(self.subtask_stack) > 0:
      if step < self.subtask_stack[-1][0]:
        self.subtask_stack.pop(-1)
      else:
        break
    self.current_task_id = (
      self.subtask_stack[-1][1] if self.subtask_stack else 0
    )

  # ================================================
  # Subtask utilities
  # ================================================
  @property
  def substack(self) -> List[Message]:
    """
    Return the current substack.

    Returns:
        substack (List[Message]): the current substack
    """
    return self.current_branch[self.substack_bottom :]

  @property
  def substack_bottom(self) -> int:
    """
    Return the bottom of the current substack.

    Returns:
        substack_bottom (int): the bottom of the current substack
    """
    if len(self.subtask_stack) == 0:
      return 0
    return self.subtask_stack[-1][0]

  def absolute_step_to_relative_step(self, step: int) -> str:
    """
    Convert an absolute step index to a relative step index.

    Args:
        step (int): the absolute step index to convert.
    """
    # TODO (FrankLeeeee): make sure that inputs and outputs are both integers
    relative_step = ""
    prev_level = 0
    for i, _ in self.subtask_stack:
      if step >= i:
        relative_step += f"{i - prev_level}."
        prev_level = i
      else:
        break
    relative_step += f"{step - prev_level}"
    return relative_step

  def relative_step_to_absolute_step(self, relative_step: str) -> int:
    """
    Convert a relative step index to an absolute step index.

    Args:
        relative_step (str): the relative step index to convert.

    Returns:
        absolute_step (int): the absolute step index
    """
    # TODO (FrankLeeeee): make sure that inputs and outputs are both integers
    return sum(map(int, relative_step.split(".")))

  def close_substack(self) -> None:
    """
    Close the current substack.
    """
    if len(self.subtask_stack) == 0:
      raise ValueError("No subtask to close")
    step, _ = self.subtask_stack[-1]
    self.branch_at(step - 1)

  def open_substack(self) -> None:
    """
    Open a new substack.
    """
    self.task_counter += 1
    self.current_task_id = self.task_counter
    self.subtask_stack.append((len(self.current_branch), self.current_task_id))

  @property
  def in_substack(self) -> bool:
    """
    Check if the current branch is in a substack.

    Returns:
        in_substack (bool): True if the current branch is in a substack, False otherwise
    """
    return len(self.subtask_stack) > 0

  # ================================================
  # Turning point utilities
  # ================================================

  def record_turning_point(
    self, required_patterns: str, forbidden_patterns: str
  ) -> None:
    """
    Record a turning point.

    Args:
        required_patterns (str): the required commands to be executed
        forbidden_patterns (str): the forbidden commands to be executed
    """
    step = self.num_steps - 2  # the last terminal step
    traj = self.traj_tracker[step]
    turning_point = f"{traj}:{step}"

    def _parse_pattern(commands):
      if not commands:
        return []
      return [c.lstrip() for c in commands.split(",") if c.lstrip()]

    required_patterns = _parse_pattern(required_patterns)
    forbidden_patterns = _parse_pattern(forbidden_patterns)

    if turning_point not in self.turning_info:
      self.turning_info[turning_point] = {"required": [], "forbidden": []}

    # skip duplicated commands
    for item, key in [
      (required_patterns, "required"),
      (forbidden_patterns, "forbidden"),
    ]:
      for r in item:
        if r not in self.turning_info[turning_point][key]:
          self.turning_info[turning_point][key].append(r)
