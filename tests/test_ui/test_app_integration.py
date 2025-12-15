"""
Usage:
python test_app_integration.py --headless --port 8005 --zmq-port 8006
"""

import argparse
import subprocess
import time

import requests
from playwright.sync_api import Playwright, sync_playwright


def test_annotator_launch_workflow(
  headless: bool = True, port: int = 8005, zmq_port: int = 8006
):
  # start a subprocess to run the annotator app
  print("Starting annotator process")
  gradio_process = subprocess.Popen(
    [
      "autopilot",
      "gradio",
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
      raise TimeoutError("Gradio process did not start in time")
    time.sleep(1)
  print(f"Gradio process started after {count} seconds")

  with sync_playwright() as playwright:
    chromium = playwright.chromium  # or "firefox" or "webkit".
    browser = chromium.launch(headless=headless)
    page = browser.new_page()
    page.goto(f"http://localhost:{port}/")

    # wait for 5 seconds to load the page
    time.sleep(5)

    # type "hello" into the message input
    print("Typing an instruction")
    page.locator("#msg").locator("textarea").fill(
      "can you help me search for weather in Singapore today?"
    )
    page.locator("#send_button").click()
    time.sleep(10)

    # get the number of elements with class message-row
    print("Checking number of message rows")
    msg_count = page.locator(".message-row").count()
    assert msg_count == 3, f"Expected 3 message rows, got {msg_count}"

    # test the reset button
    print("Testing the reset button")
    page.locator("#reset_button").click()
    time.sleep(30)
    msg_count = page.locator(".message-row").count()
    assert msg_count == 0, f"Expected 0 message rows, got {msg_count}"

    # type "hello" into the message input
    print("Typing an instruction")
    page.locator("#msg").locator("textarea").fill(
      "hi, can you help me search for weather in Singapore today?"
    )
    page.locator("#send_button").click()
    time.sleep(10)

    # get the number of elements with class message-row
    print("Checking number of message rows")
    msg_count = page.locator(".message-row").count()
    assert msg_count == 3

  # kill the gradio process
  gradio_process.terminate()
  gradio_process.wait(timeout=10)


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--headless",
    action="store_true",
    default=True,
    help="Run the test in headless mode (do not show browser)",
  )
  parser.add_argument("--port", type=int, default=8005, help="The port to use")
  parser.add_argument(
    "--zmq-port", type=int, default=8006, help="The zmq port to use"
  )
  return parser.parse_args()


if __name__ == "__main__":
  # you can set headless to False for debug
  args = parse_args()
  test_annotator_launch_workflow(
    headless=args.headless, port=args.port, zmq_port=args.zmq_port
  )
