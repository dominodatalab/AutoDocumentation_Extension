SHELL := /bin/bash

VENV_DIR := auto_model_docs/autodoc-env
ACTIVATE := $(VENV_DIR)/bin/activate

.PHONY: test test-all

test: test-all

test-all:
	@set -euo pipefail; \
	if [ ! -f "$(ACTIVATE)" ]; then \
		echo "Missing venv activate script: $(ACTIVATE)"; \
		exit 1; \
	fi; \
	source "$(ACTIVATE)"; \
	python -m pytest ./tests && \
	python -m pytest auto_model_docs/tests
