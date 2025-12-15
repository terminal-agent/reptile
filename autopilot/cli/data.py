import os
from tempfile import NamedTemporaryFile
from typing import Any, List, Optional

import typer
import yaml
from filelock import FileLock
from git import Repo
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
  Footer,
  Header,
  Label,
  ListItem,
  ListView,
  MarkdownViewer,
  Select,
)
from typing_extensions import Annotated

from autopilot.config import GLOBAL_CONFIG
from autopilot.constants import _CACHE_ROOT
from autopilot.utils import console

repo_path = os.path.join(_CACHE_ROOT, "yaml_data")
sessions_path = os.path.join(_CACHE_ROOT, "sessions")

app = typer.Typer()


class Session(object):
  def __init__(self, filename):
    self.filename = filename
    with open(self.filename) as f:
      self.history = yaml.safe_load(f)
    self.num_traj = self.history[-1]["traj"] + 1
    self.trajs: List[List[Any]] = [[] for _ in range(self.num_traj)]
    prev_traj = 0
    for item in self.history:
      traj, step = item["traj"], item["step"]
      # a fork happens, we copy the previous traj upto step - 1
      if traj != prev_traj:
        self.trajs[traj].extend(self.trajs[traj - 1][:step])
        prev_traj = traj
      self.trajs[traj].append(item)

  def markdown(self, idx):
    traj = self.trajs[idx]
    texts = []
    for i, t in enumerate(traj):
      role, content = t["role"], t["content"]
      if "edit_prefix" in t:
        ann = "llm,amend"
      else:
        ann = role[:4]
      texts.append(f"# Step {i} ({ann})")
      if role == "llm":
        texts.append(content)
      else:
        texts.append(f"```text\n{content}\n```")
    result = "\n".join(texts)
    return result


def initialize_repo(repo_path: str, branch: Optional[str] = None) -> Repo:
  if GLOBAL_CONFIG.telemetry is None or GLOBAL_CONFIG.telemetry.github is None:
    raise ValueError("Telemetry or GitHub is not configured")

  repo_url = GLOBAL_CONFIG.telemetry.github.repo_url
  lock_file = f"{repo_path}.lock"
  lock = FileLock(lock_file, timeout=30)  # wait for 30 seconds to get the lock
  with lock:
    if not os.path.exists(repo_path):
      if branch:
        Repo.clone_from(repo_url, repo_path, branch=branch, single_branch=True)
      else:
        Repo.clone_from(repo_url, repo_path)
  return Repo(repo_path)


class TrajViewer(MarkdownViewer):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.selected_block_id = None

  def update_content(self, content) -> None:
    self.selected_block_id = None
    self.document.update(content)

  def _on_markdown_table_of_contents_selected(self, message) -> None:
    # block{id}
    self.selected_block_id = int(message.block_id[5:])
    super()._on_markdown_table_of_contents_selected(message)


class SessionList(ListView):
  class SessionSelected(Message):
    def __init__(self, session: str) -> None:
      self.session = session
      super().__init__()

  def on_list_view_selected(self, event: ListView.Selected) -> None:
    name = event.item.query_one(Label).session  # type: ignore[attr-defined]
    self.post_message(self.SessionSelected(name))

  def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
    if event.item is None:
      return
    name = event.item.query_one(Label).session  # type: ignore[attr-defined]
    self.post_message(self.SessionSelected(name))


class TrajList(ListView):
  class TrajSelected(Message):
    def __init__(self, idx: str) -> None:
      self.idx = idx
      super().__init__()

  def on_list_view_selected(self, event: ListView.Selected) -> None:
    idx = event.item.query_one(Label).idx  # type: ignore[attr-defined]
    self.post_message(self.TrajSelected(idx))

  def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
    if event.item is None:
      return
    idx = event.item.query_one(Label).idx  # type: ignore[attr-defined]
    self.post_message(self.TrajSelected(idx))


class ReloadInfo(Exception):
  def __init__(self, branch, traj_idx, step_idx):
    self.branch = branch
    self.traj_idx = traj_idx
    self.step_idx = step_idx

  def __str__(self):
    return f"{self.branch}:{self.traj_idx}:{self.step_idx}"


class ViewerApp(App):
  """A TUI for viewing files in a Git repository."""

  BINDINGS = [
    ("q", "quit", "Quit the app"),
    ("ctrl+r", "replay()", "Replay to the selected step"),
  ]

  CSS = """
  TrajViewer {
      width: 80%;
  }
  SessionList {
      height: 50%;
  }
  """

  def __init__(self):
    super().__init__()

    if (
      GLOBAL_CONFIG.telemetry is None or GLOBAL_CONFIG.telemetry.github is None
    ):
      raise ValueError("Telemetry or GitHub is not configured")
    self.repo_url = GLOBAL_CONFIG.telemetry.github.repo_url
    self.repo_path = repo_path
    self.repo = initialize_repo(self.repo_path)
    self.fetch_updates()
    self.author_branches = self._get_branches()
    self.selected_author = "All"
    self.selected_session = self.author_branches["All"][0]
    self.selected_traj = 0

  def action_replay(self):
    traj_viewer = self.query_one(TrajViewer)
    step_idx = traj_viewer.selected_block_id
    if step_idx is None or self.session is None:
      return
    raise ReloadInfo(self.selected_session, self.selected_traj, step_idx)

  def _handle_exception(self, error: Exception) -> None:
    if isinstance(error, ReloadInfo):
      raise error
    else:
      super()._handle_exception(error)

  def fetch_updates(self):
    try:
      self.repo.remote().fetch()
      self.app.notify(
        "Successfully fetched updates from remote.", severity="success"
      )
    except Exception as e:
      self.app.notify(f"Failed to fetch updates: {e}", severity="error")

  def compose(self) -> ComposeResult:
    """Compose our UI."""
    yield Header()
    with Horizontal():
      with Vertical():
        yield Select(
          id="select_author",
          value="All",
          options=[(author, author) for author in self.author_branches.keys()],
        )
        yield SessionList(id="session_list")
        yield TrajList(id="traj_list")
      yield TrajViewer(id="traj_viewer")
    yield Footer()

  def _get_branches(self):
    """Load branches and author emails."""
    remote_branches = [ref.name for ref in self.repo.remote().refs]
    commit_time = {}
    for branch in remote_branches:
      try:
        commit = self.repo.commit(branch)
        commit_time[branch] = commit.committed_date
      except Exception:
        commit_time[branch] = 0
    sorted_branches = sorted(
      remote_branches, key=lambda branch: commit_time[branch], reverse=True
    )
    author_branches = {"All": sorted_branches}
    for i, branch in enumerate(sorted_branches):
      try:
        author_email = self._get_author_email(branch)
        if author_email not in author_branches:
          author_branches[author_email] = []
        author_branches[author_email].append(branch)
      except Exception:
        continue
    return author_branches

  def _get_author_email(self, branch: str) -> str:
    """Get the author email of the last commit on the session."""
    try:
      author_email = self.repo.git.log("-1", "--format=%ae", branch)
      return author_email.strip()  # type: ignore[no-any-return]
    except Exception:
      return "Unknown"

  def on_mount(self) -> None:
    pass

  def _update_session_list(self):
    to_extend = []
    for i, session in enumerate(self.author_branches[self.selected_author]):
      widget = Label(session)
      widget.session = session  # type: ignore[attr-defined]
      to_extend.append(ListItem(widget))
    self._clear_session_list()
    session_list = self.query_one("#session_list")
    session_list.extend(to_extend)

  def _clear_session_list(self) -> None:
    session_list = self.query_one(SessionList)
    session_list.clear()
    self._clear_traj_list()

  def _update_traj_list(self) -> None:
    to_extend = []
    for i in range(self.session.num_traj):
      label = Label(f"{i}")
      label.idx = i  # type: ignore[attr-defined]
      to_extend.append(ListItem(label))
    self._clear_traj_list()
    traj_list = self.query_one(TrajList)
    traj_list.extend(to_extend)

  def _clear_traj_list(self) -> None:
    traj_list = self.query_one(TrajList)
    traj_list.clear()
    traj_viewer = self.query_one(TrajViewer)
    traj_viewer.update_content("")

  def on_traj_list_traj_selected(self, message: TrajList.TrajSelected) -> None:
    self.selected_traj = int(message.idx)
    traj_viewer = self.query_one(TrajViewer)
    content = self.session.markdown(self.selected_traj)
    traj_viewer.update_content(content)

  def on_session_list_session_selected(
    self, message: SessionList.SessionSelected
  ) -> None:
    self.selected_session = message.session
    branch_name = message.session.split("/", 1)[-1]
    self.repo.git.checkout(branch_name)
    filename = os.path.join(repo_path, "history.yml")
    self.session = Session(filename)
    self._update_traj_list()

  def on_select_changed(self, event: Select.Changed) -> None:
    self.selected_author = event.value
    self._update_session_list()


@app.command(name="viewer", help="Launch TUI viewer.")
def viewer() -> None:
  viewer_app = ViewerApp()
  try:
    viewer_app.run()
  except ReloadInfo as r:
    console.print(f"Add --reload {r} option to reload.")


@app.command(name="view", help="view the data of a specific session.")
def view(
  session: Annotated[
    str, typer.Option("-s", "--session", help="Session name to view data.")
  ],
  print: Annotated[
    bool,
    typer.Option(
      "--print/--no-print",
      help="print in console, otherwise open with vs code",
    ),
  ] = True,
) -> None:
  path = os.path.join(sessions_path, session)
  if os.path.exists(path):
    console.log(f"session found in {sessions_path}.")
    filename = os.path.join(sessions_path, session, "history.yml")
  else:
    console.log(f"session not found in {sessions_path}.")
    console.log(f"looking for session in {repo_path}.")
    repo = initialize_repo(repo_path)
    repo.remote().fetch()
    repo.git.checkout(session)
    filename = os.path.join(repo_path, "history.yml")
  session_obj = Session(filename)
  text = session_obj.markdown(-1)
  if print:
    console.print(Markdown(text))
  else:
    with NamedTemporaryFile("w", suffix=".md", delete=False) as f:
      f.write(text)
      os.system(f"code {f.name}")
