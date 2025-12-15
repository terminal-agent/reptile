WHEEL_DIR := /tmp/autopilot_tools_$(USER)
WHEEL_FILE := $(WHEEL_DIR)/autopilot_tools-0.0.0-py3-none-any.whl
PYTHON := python3

SOURCE_FILES := $(shell find . -name "*.py")

$(WHEEL_FILE): $(SOURCE_FILES)
	@mkdir -p $(WHEEL_DIR)
	$(PYTHON) setup.py bdist_wheel --dist-dir $(WHEEL_DIR)

wheel: $(WHEEL_FILE)

clean:
	rm -rf build dist *.egg-info
	rm -rf $(WHEEL_DIR)
	rm -rf ../autopilot_tools.egg-info

.PHONY: wheel clean
