import asyncio
import json
import logging
import os
import subprocess
from enum import Enum
from functools import wraps
from typing import Literal, Optional

import rpyc
import typer
from browser_use import Browser
from browser_use.browser.context import BrowserContext
from browser_use.dom.service import DomService
from pydantic import BaseModel, Field
from rpyc.utils.server import ThreadedServer
from typing_extensions import Annotated

from .tool import TOOLS, CLITool

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


_DEFAULT_PORT = 8888


class BrowserResponse(BaseModel):
  output: str = Field(default="")
  error: str | None = Field(default=None)

  def __str__(self):
    return f"output: {self.output}\nerror: {self.error}"


class BrowserAction(Enum):
  GO_TO_URL = "go_to_url"
  GET_STATES = "get_states"
  CLICK_ELEMENT = "click_element"
  INPUT_TEXT = "input_text"
  REFRESH = "refresh"
  SCROLL_DOWN = "scroll_down"
  SCROLL_UP = "scroll_up"
  SCROLL_TO_TEXT = "scroll_to_text"
  SEND_KEYS = "send_keys"
  GET_DROPDOWN_OPTIONS = "get_dropdown_options"
  SELECT_DROPDOWN_OPTION = "select_dropdown_option"
  GO_BACK = "go_back"
  WAIT = "wait"
  SWITCH_TAB = "switch_tab"
  OPEN_TAB = "open_tab"
  CLOSE_TAB = "close_tab"
  CLOSE_BROWSER = "close_browser"


class ServiceStates:
  def __init__(self) -> None:
    self.browser: Optional[Browser] = None
    self.dom_service: Optional[DomService] = None
    self.context: Optional[BrowserContext] = None
    self.loop = asyncio.new_event_loop()


@rpyc.service
class BrowserService(rpyc.Service):
  states = ServiceStates()

  async def _create_browser(self):
    self.states.browser = Browser()
    return self.states.browser

  async def _create_context(self):
    assert self.states.browser is not None, "Browser is not initialized"
    new_context = await self.states.browser.new_context()
    self.states.context = new_context
    self.states.dom_service = DomService(await new_context.get_current_page())
    return new_context

  async def _prepare_context(self):
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    if self.states.browser is None:
      await self._create_browser()

    if self.states.context is None:
      await self._create_context()
    return self.states.context

  async def cleanup(self):
    if self.states.context:
      await self.states.context.close()
      self.states.context = None
      self.states.dom_service = None
    if self.states.browser:
      await self.states.browser.close()
      self.states.browser = None

  async def _dispatch(self, action: str, **kwargs):
    await self._prepare_context()

    match action:
      case BrowserAction.GO_TO_URL.value:
        return await self.go_to_url(**kwargs)
      case BrowserAction.GET_STATES.value:
        return await self.get_browser_states()
      case BrowserAction.GO_BACK.value:
        return await self.go_back()
      case BrowserAction.REFRESH.value:
        return await self.refresh()
      case BrowserAction.CLICK_ELEMENT.value:
        return await self.click_element(**kwargs)
      case BrowserAction.INPUT_TEXT.value:
        return await self.input_text(**kwargs)
      case BrowserAction.SCROLL_DOWN.value:
        return await self.scroll_down(**kwargs)
      case BrowserAction.SCROLL_UP.value:
        return await self.scroll_up(**kwargs)
      case BrowserAction.SCROLL_TO_TEXT.value:
        return await self.scroll_to_text(**kwargs)
      case BrowserAction.SEND_KEYS.value:
        return await self.send_keys(**kwargs)
      case BrowserAction.GET_DROPDOWN_OPTIONS.value:
        return await self.get_dropdown_options(**kwargs)
      case BrowserAction.SELECT_DROPDOWN_OPTION.value:
        return await self.select_dropdown_option(**kwargs)
      case BrowserAction.SWITCH_TAB.value:
        return await self.switch_tab(**kwargs)
      case BrowserAction.OPEN_TAB.value:
        return await self.open_tab(**kwargs)
      case BrowserAction.CLOSE_TAB.value:
        return await self.close_tab()
      case BrowserAction.WAIT.value:
        return await self.wait(**kwargs)
      case BrowserAction.CLOSE_BROWSER.value:
        return await self.close_browser()
      case _:
        pass

  @rpyc.exposed
  def dispatch(self, action: str, **kwargs):
    out = self.states.loop.run_until_complete(self._dispatch(action, **kwargs))
    return out

  async def go_to_url(self, url: str):
    # Navigation actions
    if not url:
      return BrowserResponse(error="URL is required for 'go_to_url' action")

    assert self.states.context is not None, "Browser context is not initialized"
    page = await self.states.context.get_current_page()
    await page.goto(url)
    await page.wait_for_load_state()
    return BrowserResponse(output=f"Navigated to {url}")

  async def go_back(self):
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.go_back()
    return BrowserResponse(output="Navigated back")

  async def refresh(self):
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.refresh_page()
    return BrowserResponse(output="Refreshed current page")

  async def click_element(self, index: int):
    if index is None:
      return BrowserResponse(
        error="Index is required for 'click_element' action"
      )
    assert self.states.context is not None, "Browser context is not initialized"
    element = await self.states.context.get_dom_element_by_index(index)
    if not element:
      return BrowserResponse(error=f"Element with index {index} not found")
    download_path = await self.states.context._click_element_node(element)
    output = f"Clicked element at index {index}"
    if download_path:
      output += f" - Downloaded file to {download_path}"
    return BrowserResponse(output=output)

  async def input_text(self, index: int, text: str):
    if index is None or not text:
      return BrowserResponse(
        error="Index and text are required for 'input_text' action"
      )
    assert self.states.context is not None, "Browser context is not initialized"
    element = await self.states.context.get_dom_element_by_index(index)
    if not element:
      return BrowserResponse(error=f"Element with index {index} not found")
    await self.states.context._input_text_element_node(element, text)
    return BrowserResponse(
      output=f"Input '{text}' into element at index {index}"
    )

  async def _scroll(self, scroll_amount: int, direction: Literal["up", "down"]):
    direction_sign = 1 if direction == "down" else -1
    amount = (
      scroll_amount
      if scroll_amount is not None
      else self.states.context.config.browser_window_size["height"]
    )
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.execute_javascript(
      f"window.scrollBy(0, {direction_sign * amount});"
    )
    return BrowserResponse(
      output=f"Scrolled {'down' if direction_sign > 0 else 'up'} by {amount} pixels"
    )

  async def scroll_down(self, scroll_amount: int):
    return await self._scroll(scroll_amount, "down")

  async def scroll_up(self, scroll_amount: int):
    return await self._scroll(scroll_amount, "up")

  async def scroll_to_text(self, text: str):
    if not text:
      return BrowserResponse(
        error="Text is required for 'scroll_to_text' action"
      )
    assert self.states.context is not None, "Browser context is not initialized"
    page = await self.states.context.get_current_page()
    try:
      locator = page.get_by_text(text, exact=False)
      await locator.scroll_into_view_if_needed()
      return BrowserResponse(output=f"Scrolled to text: '{text}'")
    except Exception as e:
      return BrowserResponse(error=f"Failed to scroll to text: {str(e)}")

  async def send_keys(self, keys: str):
    if not keys:
      return BrowserResponse(error="Keys are required for 'send_keys' action")
    assert self.states.context is not None, "Browser context is not initialized"
    page = await self.states.context.get_current_page()
    await page.keyboard.press(keys)
    return BrowserResponse(output=f"Sent keys: {keys}")

  async def get_dropdown_options(self, index: int):
    if index is None:
      return BrowserResponse(
        error="Index is required for 'get_dropdown_options' action"
      )
    assert self.states.context is not None, "Browser context is not initialized"
    element = await self.states.context.get_dom_element_by_index(index)
    if not element:
      return BrowserResponse(error=f"Element with index {index} not found")
    page = await self.states.context.get_current_page()
    options = await page.evaluate(
      """
            (xpath) => {
                const select = document.evaluate(xpath, document, null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (!select) return null;
                return Array.from(select.options).map(opt => ({
                    text: opt.text,
                    value: opt.value,
                    index: opt.index
                }));
            }
        """,
      element.xpath,
    )
    return BrowserResponse(output=f"Dropdown options: {options}")

  async def select_dropdown_option(self, index: int, text: str):
    if index is None or not text:
      return BrowserResponse(
        error="Index and text are required for 'select_dropdown_option' action"
      )
    assert self.states.context is not None, "Browser context is not initialized"
    element = await self.states.context.get_dom_element_by_index(index)
    if not element:
      return BrowserResponse(error=f"Element with index {index} not found")
    page = await self.states.context.get_current_page()
    await page.select_option(element.xpath, label=text)
    return BrowserResponse(
      output=f"Selected option '{text}' from dropdown at index {index}"
    )

  async def switch_tab(self, tab_id: int):
    if tab_id is None:
      return BrowserResponse(error="Tab ID is required for 'switch_tab' action")
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.switch_to_tab(tab_id)
    return BrowserResponse(output=f"Switched to tab {tab_id}")

  async def open_tab(self, url: str):
    if not url:
      return BrowserResponse(error="URL is required for 'open_tab' action")
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.create_new_tab(url)
    return BrowserResponse(output=f"Opened new tab with {url}")

  async def close_tab(self):
    assert self.states.context is not None, "Browser context is not initialized"
    await self.states.context.close_current_tab()
    return BrowserResponse(output="Closed current tab")

  async def wait(self, seconds: int):
    await asyncio.sleep(seconds)
    return BrowserResponse(output=f"Waited for {seconds} seconds")

  async def close_browser(self):
    await self.cleanup()
    return BrowserResponse(output="Browser closed")

  async def get_browser_states(self) -> BrowserResponse:
    """
    Get the current browser state as a ToolResult.
    If context is not provided, uses self.context.
    """
    # Use provided context or fall back to self.context
    assert self.states.context is not None, (
      "The browser context is not initialized and the the states are queried."
    )
    try:
      # Try to call get_state_summary if available, otherwise fallback to get_state (deprecated)
      if hasattr(self.states.context, "get_state_summary"):
        state = await self.states.context.get_state_summary(
          cache_clickable_elements_hashes=False
        )
      else:
        state = await self.states.context.get_state(
          cache_clickable_elements_hashes=False
        )

      # Create a viewport_info dictionary if it doesn't exist
      viewport_height = 0

      if hasattr(state, "page_info") and state.page_info is not None:
        viewport_height = state.page_info.viewport_height
      elif hasattr(state, "viewport_info") and state.viewport_info is not None:
        # This should be a deprecated version
        viewport_height = state.viewport_info.height
      elif (
        hasattr(self.states.context, "browser_profile")
        and hasattr(self.states.context.browser_profile, "window_size")
        and self.states.context.browser_profile.window_size is not None
      ):
        viewport_height = self.states.context.browser_profile.window_size.get(
          "height", 0
        )
      elif hasattr(self.states.context, "config") and hasattr(
        self.states.context.config, "browser_window_size"
      ):
        # This should be a deprecated version
        viewport_height = self.states.context.config.browser_window_size.get(
          "height", 0
        )

      # Take a screenshot for the state
      logger.info("get current page")
      page = await self.states.context.get_current_page()
      logger.info("get current page done")

      logger.info("bring to front")
      await page.bring_to_front()
      await page.wait_for_load_state()
      logger.info("wait for load state done")

      logger.info("build state info")
      # Build the state info with all required fields
      state_info = {
        "url": state.url,
        "title": state.title,
        "tabs": [tab.model_dump() for tab in state.tabs],
        "help": "[0], [1], [2], etc., represent clickable indices corresponding to the elements listed. Clicking on these indices will navigate to or interact with the respective content behind them.",
        "interactive_elements": (
          state.element_tree.clickable_elements_to_string()
          if state.element_tree
          else ""
        ),
        "scroll_info": {
          "pixels_above": getattr(state, "pixels_above", 0),
          "pixels_below": getattr(state, "pixels_below", 0),
          "total_height": getattr(state, "pixels_above", 0)
          + getattr(state, "pixels_below", 0)
          + viewport_height,
        },
        "viewport_height": viewport_height,
      }

      return BrowserResponse(
        output=json.dumps(state_info, indent=4, ensure_ascii=False),
      )
    except Exception as e:
      return BrowserResponse(error=f"Failed to get browser state: {str(e)}")


def ensure_connection_established(func):
  @wraps(func)
  def wrapper(self, *args, **kwargs):
    """A wrapper function"""

    # Extend some capabilities of func
    self._ensure_connection_established()
    return func(self, *args, **kwargs)

  return wrapper


class BrowserUseClient:
  def __init__(self, port=_DEFAULT_PORT):
    self.port = port
    self.conn = None
    self.dispatch = None
    os.environ["ANONYMIZED_TELEMETRY"] = "false"

  def _ensure_connection_established(self):
    if self.conn is None:
      self.conn = rpyc.connect("localhost", self.port)

  def get_states(self):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.GET_STATES.value))  # type: ignore[union-attr]

  def go_to_url(
    self, url: Annotated[str, typer.Option(help="The URL to navigate to")]
  ):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.GO_TO_URL.value, url=url))  # type: ignore[union-attr]

  def click_element(
    self,
    index: Annotated[
      int, typer.Option(help="The index of the element to click")
    ],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(BrowserAction.CLICK_ELEMENT.value, index=index)  # type: ignore[union-attr]
    )

  def input_text(
    self,
    index: Annotated[
      int, typer.Option(help="The index of the element to input text into")
    ],
    text: Annotated[
      str, typer.Option(help="The text to input into the element")
    ],
  ):
    print(
      self.conn.root.dispatch(  # type: ignore[union-attr]
        BrowserAction.INPUT_TEXT.value, index=index, text=text
      )
    )

  def scroll_down(
    self,
    scroll_amount: Annotated[
      int, typer.Option(help="The amount to scroll down")
    ],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(  # type: ignore[union-attr]
        BrowserAction.SCROLL_DOWN.value, scroll_amount=scroll_amount
      )
    )

  def scroll_up(
    self,
    scroll_amount: Annotated[int, typer.Option(help="The amount to scroll up")],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(  # type: ignore[union-attr]
        BrowserAction.SCROLL_UP.value, scroll_amount=scroll_amount
      )
    )

  def scroll_to_text(
    self, text: Annotated[str, typer.Option(help="The text to scroll to")]
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(BrowserAction.SCROLL_TO_TEXT.value, text=text)  # type: ignore[union-attr]
    )

  def send_keys(
    self, keys: Annotated[str, typer.Option(help="The keys to send")]
  ):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.SEND_KEYS.value, keys=keys))  # type: ignore[union-attr]

  def get_dropdown_options(
    self,
    index: Annotated[
      int, typer.Option(help="The index of the dropdown to get options from")
    ],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(  # type: ignore[union-attr]
        BrowserAction.GET_DROPDOWN_OPTIONS.value, index=index
      )
    )

  def select_dropdown_option(
    self,
    index: Annotated[
      int,
      typer.Option(help="The index of the dropdown to select an option from"),
    ],
    text: Annotated[str, typer.Option(help="The text of the option to select")],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(  # type: ignore[union-attr]
        BrowserAction.SELECT_DROPDOWN_OPTION.value, index=index, text=text
      )
    )

  def go_back(self):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.GO_BACK.value))  # type: ignore[union-attr]

  def wait(
    self, seconds: Annotated[int, typer.Option(help="The seconds to wait")]
  ):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.WAIT.value, seconds=seconds))  # type: ignore[union-attr]

  def switch_tab(
    self,
    tab_id: Annotated[int, typer.Option(help="The id of the tab to switch to")],
  ):
    self._ensure_connection_established()
    print(
      self.conn.root.dispatch(BrowserAction.SWITCH_TAB.value, tab_id=tab_id)  # type: ignore[union-attr]
    )

  def open_tab(self, url: Annotated[str, typer.Option(help="The URL to open")]):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.OPEN_TAB.value, url=url))  # type: ignore[union-attr]

  def close_tab(self):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.CLOSE_TAB.value))  # type: ignore[union-attr]

  def close_browser(self):
    self._ensure_connection_established()
    print(self.conn.root.dispatch(BrowserAction.CLOSE_BROWSER.value))  # type: ignore[union-attr]


# @TOOLS.register
class BrowserUseCLI(CLITool):
  name = "browser"
  description = """
  Use the browser to navigate to a URL, click on an element, type text, etc.
  For more information:

  ```sh
  browser --help
  ```
  """
  client: BrowserUseClient = BrowserUseClient()

  def register(self):
    self.app.command("launch_server", help="Start a browser")(
      self.launch_server
    )
    self.app.command(
      "launch_daemon_server", help="Start a browser in the daemon mode"
    )(self.launch_daemon_server)
    self.app.command("describe", help="Describe the current browser states")(
      self.client.get_states
    )
    self.app.command("go_to_url", help="Navigate to a URL")(
      self.client.go_to_url
    )
    self.app.command("click_element", help="Click on an element")(
      self.client.click_element
    )
    self.app.command("input_text", help="Input text into an element")(
      self.client.input_text
    )
    self.app.command("scroll_down", help="Scroll down")(self.client.scroll_down)
    self.app.command("scroll_up", help="Scroll up")(self.client.scroll_up)
    self.app.command("scroll_to_text", help="Scroll to text")(
      self.client.scroll_to_text
    )
    self.app.command("send_keys", help="Send keys to the current page")(
      self.client.send_keys
    )
    self.app.command("get_dropdown_options", help="Get dropdown options")(
      self.client.get_dropdown_options
    )
    self.app.command("select_dropdown_option", help="Select a dropdown option")(
      self.client.select_dropdown_option
    )
    self.app.command("go_back", help="Go back")(self.client.go_back)
    self.app.command("wait", help="Wait for a number of seconds")(
      self.client.wait
    )
    self.app.command("switch_tab", help="Switch to a tab")(
      self.client.switch_tab
    )
    self.app.command("open_tab", help="Open a tab")(self.client.open_tab)
    self.app.command("close_tab", help="Close the current tab")(
      self.client.close_tab
    )
    self.app.command("close_browser", help="Close the browser")(
      self.client.close_browser
    )

  def launch_server(self):
    try:
      server = ThreadedServer(BrowserService, port=_DEFAULT_PORT)
      server.start()
      print("Browser daemon launched")
    except Exception as e:
      print(f"Browser daemon failed to launch: {e}")
      raise e

  def launch_daemon_server(self):
    subprocess.Popen(
      ["browseruse", "launch_server"],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      preexec_fn=os.setsid,  # Detach from parent process group
    )
