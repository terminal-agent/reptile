DOCKERFILE_BASE = r"""FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt update && apt install -y \
wget \
git \
build-essential \
libffi-dev \
libtiff-dev \
python3 \
python3-pip \
python-is-python3 \
jq \
curl \
locales \
locales-all \
tzdata \
tmux \
vim \
&& rm -rf /var/lib/apt/lists/*

# Use python3.9 as default python
RUN apt-get update && \
    apt-get install -y software-properties-common curl && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.9 python3.9-venv python3.9-dev python3.9-distutils && \
    curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.9 get-pip.py && \
    rm get-pip.py && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment with Python 3.9
RUN python3.9 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

RUN adduser --disabled-password --gecos 'dog' nonroot

COPY ./setup_env.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_env.sh
RUN chmod +x /root/setup_env.sh
RUN /bin/bash /root/setup_env.sh

RUN mkdir -p /root/.config/terminal-agent /tmp/autopilot

RUN mkdir -p /app/testbed

# Automatically activate the virtual environment
RUN echo "source /opt/venv/bin/activate" > /root/.bashrc

WORKDIR /app/testbed/
"""

DOCKERFILE_INSTANCE = r"""FROM {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /app/testbed/
"""

ENV_SCRIPT = r"""
\#!/bin/bash
set -euxo pipefail
source /opt/venv/bin/activate
python -m pip install --no-cache-dir pytest openai rich prompt_toolkit absl-py pyyaml
cat <<'EOF_59812759871' > $HOME/requirements.txt
asgiref ~= 3.2
argon2-cffi >= 16.1.0
bcrypt
docutils
geoip2
jinja2 >= 2.9.2
numpy
Pillow != 5.4.0
pylibmc; sys.platform != 'win32'
python-memcached >= 1.59
pytz
pywatchman; sys.platform != 'win32'
PyYAML
selenium
sqlparse >= 0.2.2
tblib >= 1.5.0
openai
rich
prompt_toolkit
absl-py
pyyaml

EOF_59812759871
python -m pip install -r $HOME/requirements.txt
rm $HOME/requirements.txt
"""

PROMPT_TEMPLATE = """
<uploaded_files>
/testbed
</uploaded_files>
I've uploaded a python code repository in the directory /testbed. Consider the following PR description:

<pr_description>
{problem_statement}
</pr_description>

<instructions>
# Task Instructions

## Overview
You're a software engineer interacting continuously with a computer by submitting commands.
You'll be helping implement necessary changes to meet requirements in the PR description.
Your task is specifically to make changes to non-test files in the current directory in order to fix the issue described in the PR description in a way that is general and consistent with the codebase.

IMPORTANT: This is an interactive process where you will think and issue ONE command, see its result, then think and issue your next command.

For each response:
1. Include a THOUGHT section explaining your reasoning and what you're trying to accomplish
2. Provide exactly ONE bash command to execute

## Important Boundaries
- MODIFY: Regular source code files in /testbed (this is the working directory for all your subsequent commands)
- DO NOT MODIFY: Tests, configuration files (pyproject.toml, setup.cfg, etc.)

## Recommended Workflow
1. Analyze the codebase by finding and reading relevant files
2. Create a script to reproduce the issue
3. Edit the source code to resolve the issue
4. Verify your fix works by running your script again
5. Test edge cases to ensure your fix is robust
6. Submit your work by issuing the following command:
```bash
git add -A && git diff --cached > /tmp/tasks/patch.txt
```

## Command Execution Rules
You are operating in an environment where
1. You write a single command
2. The system executes that command in a subshell
3. You see the result
4. You write your next command

Each response should include:
1. A **THOUGHT** section where you explain your reasoning and plan
2. A single bash code block with your command

Format your responses like this:

<format_example>
THOUGHT: Here I explain my reasoning process, analysis of the current situation,
and what I'm trying to accomplish with the command below.

```bash
your_command_here
```
</format_example>

Commands must be specified in a single bash code block:

```bash
your_command_here
```

**CRITICAL REQUIREMENTS:**
- Your response SHOULD include a THOUGHT section explaining your reasoning
- Your response MUST include EXACTLY ONE bash code block
- This bash block MUST contain EXACTLY ONE command (or a set of commands connected with && or ||)
- If you include zero or multiple bash blocks, or no command at all, YOUR RESPONSE WILL FAIL
- Do NOT try to run multiple independent commands in separate blocks in one response
- Directory or environment variable changes are not persistent. Every action is executed in a new subshell.
- However, you can prefix any action with `MY_ENV_VAR=MY_VALUE cd /path/to/working/dir && ...` or write/load environment variables from files

Example of a CORRECT response:
<example_response>
THOUGHT: I need to understand the structure of the repository first. Let me check what files are in the current directory to get a better understanding of the codebase.

```bash
ls -la
```
</example_response>

Example of an INCORRECT response:
<example_response>
THOUGHT: I need to examine the codebase and then look at a specific file. I'll run multiple commands to do this.

```bash
ls -la
```

Now I'll read the file:

```bash
cat file.txt
```
</example_response>

If you need to run multiple commands, either:
1. Combine them in one block using && or ||
```bash
command1 && command2 || echo "Error occurred"
```

2. Wait for the first command to complete, see its output, then issue the next command in your following response.

## Environment Details
- You have a full Linux shell environment
- Always use non-interactive flags (-y, -f) for commands
- Avoid interactive tools like vi, nano, or any that require user input
- If a command isn't available, you can install it

## Useful Command Examples

### Create a new file:
```bash
cat <<'EOF' > newfile.py
import numpy as np
hello = "world"
print(hello)
EOF
```

### Edit files with sed:
```bash
# Replace all occurrences
sed -i 's/old_string/new_string/g' filename.py

# Replace only first occurrence
sed -i 's/old_string/new_string/' filename.py

# Replace first occurrence on line 1
sed -i '1s/old_string/new_string/' filename.py

# Replace all occurrences in lines 1-10
sed -i '1,10s/old_string/new_string/g' filename.py
```

### View file content:
```bash
# View specific lines with numbers
nl -ba filename.py | sed -n '10,20p'
```

### Any other command you want to run
```bash
anything
```

## Submission
When you've completed your work (reading, editing, testing), and cannot make further progress
issue exactly the following command:

```bash
git add -A && git diff --cached > /tmp/tasks/patch.txt
```

This command will submit your work.

## Exit
If you checked you submission and need to exit the task, just say "the task is all done" and don't print any code block:

I have checked my submission and it's correct. The task is all done.

You cannot continue working (reading, editing, testing) in any way on this task after exiting.
</instructions>
"""
