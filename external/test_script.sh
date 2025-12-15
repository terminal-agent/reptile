#!/bin/bash

if [ -f "$TASK_DIR/run-tests.sh" ]; then
    export DEBIAN_FRONTEND=noninteractive
    yes y | bash "$TASK_DIR/run-tests.sh"
    exit_code=$?
else
    if [ -f "/tmp/tasks/shared_scripts/run-uv-pytest.sh" ]; then
        uv init
        uv add pytest
        bash "/tmp/tasks/shared_scripts/run-uv-pytest.sh"
        exit_code=$?
    else
        echo "Error: run-tests.sh not found in $TASK_DIR and no shared script for pytest found."
        exit_code=1
    fi
fi

if [ $exit_code -ne 0 ]; then
    echo "Tests failed with exit code $exit_code"
    exit $exit_code
else
    echo "Tests passed!"
fi
