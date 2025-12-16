# Contribution Guide

## Overview

This document outlines the essential development workflow for the `autopilot` project. If you are interested in contributing to the project, please follow the steps below.

**Table of Contents:**
- [Development Environment Setup](#environment-setup)
- [Development Pipeline](#development-pipeline)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Getting Help](#getting-help)

## Environment Setup

### Prerequisites

- Python 3.11 or higher
- Git with LFS support (`git lfs install`)
- [uv](https://github.com/astral-sh/uv) or pip

### Setup Steps

**1. Configure the repository**

First visit our official repository [Terminal-Agents](https://github.com/terminal-agent/reptile) and fork it with your own GitHub account (Check the `fork` button in the upper-right corner).

Then you can clone your forked repository into your local. Note that `--recurse-submodules` automatically initializes and updates all its submodules.
```bash
git clone https://github.com/{YOUR-GITHUB-USERNAME}/Terminal-Agents.git --recurse-submodules
cd Terminal-Agents
```

To set the official repository as your upstream:
```bash
cd Terminal-Agents
git remote add upstream https://github.com/terminal-agent/reptile.git

# Check if the remote has been set
git remote -v
```

After setting up the remotes successfully, you will see two remote repositories have been set:

`origin https://github.com/{YOUR-GITHUB-USERNAME}/Terminal-Agents.git`
This is the default remote pointing to your forked repository. You have write access and can push your changes here.

`upstream https://github.com/terminal-agent/reptile.git`
The upstream points to the official repository, and is used to sync the latest updates from it.


**2. Create a virtual environment**

We recommend using a `.venv` directory inside the repo:

```shell
# Using uv (recommended)
uv venv .venv --python 3.11

# Or using standard venv
python3.11 -m venv .venv
```

And then activate the virtual environment:

```shell
source .venv/bin/activate

# Or on Windows
.venv\Scripts\activate
```

**3. Install the repository in development mode**

The following installation command will install both `requirements.txt` and `requirements-dev.txt`:

```bash
uv pip install -v -e .[dev]
```

**Note for Zsh users:** If you encounter `zsh: no matches found: .[dev]`, use:
```bash
uv pip install -v -e '.[dev]'
```

**4. Install Pre-commit Hooks**

```bash
uv pip install pre-commit
pre-commit install
```

This will enable pre-commit hooks to run automatically before you commit. Some existing pre-commit hooks are:

1. Code formatting: `ruff format .` passes
2. Linting: `ruff check .` passes
3. Tests pass: `pytest` passes
4. Pre-commit hooks: `pre-commit run --all-files` passes
5. Documentation: All public APIs have docstrings
6. Type annotations: All functions have proper type hints

You can manually run pre-commit hooks at any time as well:

```bash
pre-commit run --files module_0.py module_1.py
```

### Verify Installation

After installation, you may check autopilot is successfully installed by
```bash
autopilot --help
```


## Development Pipeline

You can follow the following pipeline to develop your feature:

### Synchronize Updates

Typical workflow:

```bash
# 1) Fetch latest changes from upstream
git fetch upstream

# 2) Rebase frequently to merge updates into your local branch, for example
git checkout main
git rebase upstream/main

# 3) Make your changes and commit locally
...

# 4) Push to your forked repository
git push origin main

# 5) Create a Pull Request from your fork to the official repository
...
```

If conflicts occur, resolve the conflict and then continue the rebase
```bash
git add .
git rebase --continue
```


### Create a Branch

Use descriptive branch names that follow this pattern:

```bash
# For documentation
git checkout -b docs/what-you-are-documenting

# For new features
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b fix/bug-description
```

Example types:
- **feature**: A new feature
- **fix**: A bug fix
- **test**: Adding or updating tests
- **refactor**: Code refactoring without changing functionality
- **docs**: Documentation only changes
- **chore**: Maintenance tasks, dependency updates, etc.


### Test Your Changes

Build and run tests during development:

```bash
# Run specific test file with displaying prints and loggings
pytest -s tests/test_tools/test_calculator.py
```

### Commit and Push
```bash
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature-name
```

Pre-commit hooks will run automatically when you commit. If you want to run the pre-commit hooks manually, you can run:

```bash
pre-commit run --files module_0.py module_1.py
```

### Create a Pull Request

Before you create a pull request, you need to write a detailed PR description. The description should explain the motivation, problem, changes, or outcomes, etc.

The PR description template can be found at `.github/pull_request_template.md`.

## Code Standards

See [Code Standards](./code_standards.md) for detailed documentation and type annotation requirements.

## Testing

### Writing Tests

All code changes must include tests. We use `pytest` and `pytest-mock` at this moment. If the tests you're adding require, you may want to add extra dependencies in `requirements-dev.txt` and re-install the repository.

Tests should be placed in the `tests/` directory, ideally mirroring the structure of the `autopilot/` directory:

```
autopilot/
  tools/
  workflow/
tests/
  test_tools/
  test_workflow/
```

### Mocking in Tests

You might want to use `pytest` fixtures and mocking when needed. Refer to the following example of the basic usage (The `pytest-mock` plugin is included as part of the repository's development installation).

```python
import pytest

@pytest.fixture
def mock_api(mocker):
    """Reusable mocked API client created via pytest-mock."""
    api = mocker.Mock()
    api.generate.return_value = "test response"
    return api

def test_with_fixture_and_mocker(mock_api):
    from app.api import call_api
    result = call_api(mock_api, "test prompt")
    assert result == "test response"
    mock_api.generate.assert_called_once_with("test prompt")
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test function
pytest tests/test_tools/test_calculator.py::test_calculator_tool
```


## Getting Help

### Getting Unstuck

If you're stuck on a problem, we recommend to review documentation and browse existing issues first. If the issue still exists, please report it with relatively clear descriptions.

- **Documentation**: Browse the `docs/` directory for guides and references
- **GitHub Issues**: [Report bugs or request features](https://github.com/terminal-agent/reptile/issues)

### Reporting Issues

When reporting bugs, it's good to have:

1. **Description**: Clear description of the issue. What are expected to happen and what actually happened.
2. **Reproduction steps**: Minimal steps to reproduce.
3. **Environment**: Python version, OS, relevant dependencies.
4. **Logs**: Any error messages, stack traces, or screenshots, if applicable.
