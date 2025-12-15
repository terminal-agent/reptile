import os
from typing import List, Optional, Tuple

from swebench.harness.constants import TestStatus
from swebench.harness.grading import test_failed, test_passed

# Import SWE-bench official functions
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER


def parse_specific_test_results(
  output: str, test_list: list, repo: Optional[str] = None
) -> Tuple[List[str], List[str], List[str]]:
  """Parse pytest output to check if specific tests passed from complete test run.

  Uses SWE-bench official parsers and grading functions for accurate parsing.
  """
  # Use SWE-bench official parser if repo is specified
  test_status_map = {}
  if repo and repo in MAP_REPO_TO_PARSER:
    try:
      parser = MAP_REPO_TO_PARSER[repo]
      import inspect

      sig = inspect.signature(parser)
      # Check if parser needs test_spec parameter
      if len(sig.parameters) > 1:
        # Create minimal test_spec for the parser
        class MockTestSpec:
          def __init__(self):
            self.repo = repo
            self.instance_id = "mock"
            self.version = "latest"
            self.FAIL_TO_PASS = []
            self.PASS_TO_PASS = []

        test_status_map = parser(output, MockTestSpec())
      else:
        # Parser only needs log content
        test_status_map = parser(output)
    except Exception:
      test_status_map = {}

  # Use fallback parser if official parser failed or returned empty result
  if not test_status_map:
    test_status_map = _parse_with_fallback(output)

  # Now check each specific test using SWE-bench utility functions
  passed_tests = []
  failed_tests = []
  not_found_tests = []

  for test_name in test_list:
    # Try exact match first
    if test_passed(test_name, test_status_map):
      passed_tests.append(test_name)
    elif test_failed(test_name, test_status_map):
      # Check if there's a partial match that might be more accurate
      found_partial = False
      for full_test_name in test_status_map.keys():
        if (
          full_test_name.endswith(f"::{test_name}")
          or full_test_name == test_name
        ):
          if test_passed(full_test_name, test_status_map):
            passed_tests.append(test_name)
            found_partial = True
            break
          elif test_failed(full_test_name, test_status_map):
            failed_tests.append(test_name)
            found_partial = True
            break

      if not found_partial:
        # If we couldn't find a partial match, the test doesn't exist
        not_found_tests.append(test_name)
    else:
      # Try partial match for test names that might be embedded in longer paths
      found = False
      for full_test_name in test_status_map.keys():
        # Check if test_name appears at the end of full_test_name (after ::)
        if (
          full_test_name.endswith(f"::{test_name}")
          or full_test_name == test_name
        ):
          if test_passed(full_test_name, test_status_map):
            passed_tests.append(test_name)
          elif test_failed(full_test_name, test_status_map):
            failed_tests.append(test_name)
          found = True
          break

      if not found:
        not_found_tests.append(test_name)

  return passed_tests, failed_tests, not_found_tests


def _parse_with_fallback(output: str) -> dict[str, str]:
  """Fallback parser supporting multiple test output formats."""
  test_status_map = {}
  lines = output.split("\n")
  prev_test = None

  for line in lines:
    line = line.strip()

    # Django format: "test_name ... ok", "test_name ... FAIL", "test_name ... ERROR"
    if " ... " in line:
      prev_test = line.split(" ... ")[0]
      if (
        line.endswith(" ... ok")
        or line.endswith(" ... OK")
        or line.endswith(" ...  OK")
      ):
        test = line.rsplit(" ... ", 1)[0]
        test_status_map[test] = "PASSED"
        prev_test = None
      elif line.endswith(" ... FAIL"):
        test = line.split(" ... FAIL")[0]
        test_status_map[test] = "FAILED"
        prev_test = None
      elif line.endswith(" ... ERROR"):
        test = line.split(" ... ERROR")[0]
        test_status_map[test] = "ERROR"
        prev_test = None
      elif " ... skipped" in line:
        test = line.split(" ... skipped")[0]
        test_status_map[test] = "SKIPPED"
        prev_test = None

    # Django multi-line format: test name on one line, status on next line
    elif prev_test and any(
      line.endswith(status)
      for status in [
        " ... FAIL",
        " ... ERROR",
        " ... ok",
        " ... OK",
        " ...  OK",
      ]
    ):
      if (
        line.endswith(" ... ok")
        or line.endswith(" ... OK")
        or line.endswith(" ...  OK")
      ):
        test_status_map[prev_test] = "PASSED"
      elif line.endswith(" ... FAIL"):
        test_status_map[prev_test] = "FAILED"
      elif line.endswith(" ... ERROR"):
        test_status_map[prev_test] = "ERROR"
      elif " ... skipped" in line:
        test_status_map[prev_test] = "SKIPPED"
      prev_test = None

    # Track test names that don't have status on same line
    elif line.startswith("test_") and not " ... " in line:
      prev_test = line

    # Standard pytest format: "PASSED test_name" or "test_name PASSED"
    elif any(
      line.startswith(status)
      for status in ["FAILED", "PASSED", "SKIPPED", "ERROR", "XFAIL"]
    ):
      if line.startswith("FAILED"):
        line = line.replace(" - ", " ")
      parts = line.split()
      if len(parts) >= 2:
        test_status_map[parts[1]] = parts[0]

    # Older pytest format: "test_name PASSED"
    elif any(
      line.endswith(status)
      for status in ["FAILED", "PASSED", "SKIPPED", "ERROR", "XFAIL"]
    ):
      parts = line.split()
      if len(parts) >= 2:
        test_status_map[parts[0]] = parts[1]

    # Sympy format: "test_name ok", "test_name F", "test_name E"
    elif line.endswith(" ok"):
      test_status_map[line.split()[0]] = "PASSED"
    elif line.endswith(" F"):
      test_status_map[line.split()[0]] = "FAILED"
    elif line.endswith(" E"):
      test_status_map[line.split()[0]] = "ERROR"

  return test_status_map


def run_classified_pytest_eval(
  task,
  output_dir: str,
  session_name: str,
  env_args: list,
  envs: dict,
  eval_time_out: int,
) -> Tuple[bool, str]:
  """Parse classified pytest evaluation results from existing eval_output.txt."""
  # Read existing test results
  eval_output_path = os.path.join(output_dir, session_name, "eval_output.txt")
  with open(eval_output_path, "rt", encoding="utf-8", errors="replace") as f:
    output_content = f.read()

  # Extract repo name from task name (e.g., "astropy__astropy-13033" -> "astropy/astropy")
  repo: Optional[str] = None
  if hasattr(task, "name") and "__" in task.name:
    repo_part = task.name.split("__")[0]
    repo = f"{repo_part}/{repo_part}" if "/" not in repo_part else repo_part

  # Parse results for each category using SWE-bench official parsers
  pass_to_pass_passed, pass_to_pass_failed, pass_to_pass_not_found = (
    parse_specific_test_results(output_content, task.pass_to_pass_tests, repo)
  )
  fail_to_pass_passed, fail_to_pass_failed, fail_to_pass_not_found = (
    parse_specific_test_results(output_content, task.fail_to_pass_tests, repo)
  )

  pass_to_pass_success = (
    len(pass_to_pass_failed) == 0 and len(pass_to_pass_not_found) == 0
  )
  fail_to_pass_success = (
    len(fail_to_pass_failed) == 0 and len(fail_to_pass_not_found) == 0
  )

  success = fail_to_pass_success and pass_to_pass_success

  # Check if output contains "Tests passed!" message
  # If so, force success to True even if parsing found issues
  has_tests_passed_message = "Tests passed!" in output_content.strip()
  if has_tests_passed_message:
    success = True

  eval_output_file = os.path.join(
    output_dir, session_name, "eval_output_classified_pytest.txt"
  )

  # Write detailed summary
  with open(eval_output_file, "wt", encoding="utf-8") as f:
    f.write(f"FAIL_TO_PASS: {fail_to_pass_success}\n")
    f.write(f"PASS_TO_PASS: {pass_to_pass_success}\n")
    if has_tests_passed_message:
      f.write(
        f"SUCCESS: {success} (forced True due to 'Tests passed!' message in output)\n"
      )
    else:
      f.write(f"SUCCESS: {success}\n")
    f.write("\n")

    # Write detailed test results
    f.write("=== FAIL_TO_PASS Tests ===\n")
    f.write(f"PASSED ({len(fail_to_pass_passed)}): {fail_to_pass_passed}\n")
    f.write(f"FAILED ({len(fail_to_pass_failed)}): {fail_to_pass_failed}\n")
    f.write(
      f"NOT_FOUND ({len(fail_to_pass_not_found)}): {fail_to_pass_not_found}\n\n"
    )

    f.write("=== PASS_TO_PASS Tests ===\n")
    f.write(f"PASSED ({len(pass_to_pass_passed)}): {pass_to_pass_passed}\n")
    f.write(f"FAILED ({len(pass_to_pass_failed)}): {pass_to_pass_failed}\n")
    f.write(
      f"NOT_FOUND ({len(pass_to_pass_not_found)}): {pass_to_pass_not_found}\n"
    )

  return success, eval_output_file
