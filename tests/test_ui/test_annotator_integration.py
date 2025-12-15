"""
Usage:
python test_annotator_integration.py --headless --port 8200 --zmq-port 8201
"""

import argparse
import subprocess
import time

import requests
from playwright.sync_api import Playwright, sync_playwright


def test_annotator_launch_workflow(
  headless: bool = True, port: int = 8200, zmq_port: int = 8201
):
  # start a subprocess to run the annotator app
  print("Starting annotator process")
  annotator_process = subprocess.Popen(
    [
      "autopilot",
      "annotate",
      "--no-log-to-mongodb",
      "--no-log-to-github",
      "--port",
      str(port),
      "--zmq-port",
      str(zmq_port),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
  )

  timeout = 20
  count = 0
  while True:
    # check if localhost:8003 is reachable
    try:
      response = requests.get(f"http://localhost:{port}")
      if response.status_code == 200:
        break
    except requests.exceptions.RequestException:
      pass
    count += 1
    if count > timeout:
      raise TimeoutError("Annotator process did not start in time")
    time.sleep(1)
  print(f"Annotator process started after {count} seconds")

  with sync_playwright() as playwright:
    chromium = playwright.chromium  # or "firefox" or "webkit".
    browser = chromium.launch(headless=headless)
    page = browser.new_page()
    page.goto(f"http://localhost:{port}/")

    # wait for 5 seconds to load the page
    time.sleep(1)

    # select the benchmark from the dropdown via ID
    # simulate press enter after typing
    print("Selecting benchmark")
    page.locator("#benchmark_dropdown").get_by_role("listbox").type(
      "terminal_bench"
    )
    page.keyboard.press("Enter")
    time.sleep(1)
    page.locator("#task_dropdown").get_by_role("listbox").type("hello-world")
    page.keyboard.press("Enter")
    time.sleep(1)

    # starting workflow
    print("Starting workflow")
    page.locator("#start_workflow_button").click()

    timeout = 60
    count = 0
    while True:
      msg_count = page.locator(".message-row").count()
      count += 1
      if msg_count < 3:
        time.sleep(1)
      elif count > timeout:
        raise TimeoutError("Workflow did not start in time")
      else:
        break
    # wait for the last message to finish
    time.sleep(5)

    # type "hello" into the message input
    print("Typing 'hello' into the message input")
    page.locator("#msg").locator("textarea").fill("hello")
    page.locator("#send_button").click()
    time.sleep(10)

    # get the number of elements with class message-row
    print("Checking number of message rows")
    msg_count = page.locator(".message-row").count()
    assert msg_count == 5

  # kill the annotator process
  annotator_process.terminate()
  annotator_process.wait(timeout=10)


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--headless",
    action="store_true",
    default=True,
    help="Run the test in headless mode (do not show browser)",
  )
  parser.add_argument("--port", type=int, default=8200, help="The port to use")
  parser.add_argument(
    "--zmq-port", type=int, default=8201, help="The zmq port to use"
  )
  return parser.parse_args()


if __name__ == "__main__":
  # you can set headless to False for debug
  args = parse_args()
  test_annotator_launch_workflow(
    headless=args.headless, port=args.port, zmq_port=args.zmq_port
  )
