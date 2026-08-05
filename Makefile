PACKAGE_NAME := unstructured-python-client
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)
DOCKER_IMAGE ?= downloads.unstructured.io/unstructured-io/unstructured-api:latest
INTEGRATION_IGNORE_ARGS := --ignore=_test_unstructured_client/integration/test_platform_workflow_lifecycle.py
INTEGRATION_PYTEST_ARGS := _test_unstructured_client -vv -k integration $(INTEGRATION_IGNORE_ARGS) -o log_cli=true -o log_cli_level=INFO -o log_cli_format="%(asctime)s %(levelname)s %(message)s" --capture=tee-sys --durations=20 --tb=long
PLATFORM_INTEGRATION_PYTEST_ARGS := _test_unstructured_client/integration/test_platform_workflow_lifecycle.py -v -o log_cli=true -o log_cli_level=INFO --durations=20 --tb=long

###########
# Install #
###########

## install:					installs all test, dev, and experimental requirements
.PHONY: install
install:
	python scripts/prepare_readme.py
	uv sync --locked

#################
# Test and Lint #
#################

.PHONY: test
test: test-unit test-integration-docker

.PHONY: test-unit
test-unit:
	PYTHONPATH=. uv run pytest -n auto _test_unstructured_client -v -k "unit"

.PHONY: test-contract
test-contract:
	PYTHONPATH=. uv run pytest -n auto _test_contract -v

# Assumes you have unstructured-api running on localhost:8000
.PHONY: test-integration
test-integration:
	PYTHONPATH=. uv run pytest $(INTEGRATION_PYTEST_ARGS)

# Runs the unstructured-api in docker for tests
.PHONY: test-integration-docker
test-integration-docker:
	@bash -lc 'set -euo pipefail; \
	container_name=unstructured-api; \
	image="${DOCKER_IMAGE}"; \
	cleanup() { \
		status=$$?; \
		if [ $$status -ne 0 ]; then \
			echo "integration diagnostics image=$$image container=$$container_name"; \
			docker logs "$$container_name" --tail 200 || true; \
		fi; \
		docker kill "$$container_name" >/dev/null 2>&1 || true; \
		exit $$status; \
	}; \
	trap cleanup EXIT; \
	docker stop "$$container_name" >/dev/null 2>&1 || true; \
	docker kill "$$container_name" >/dev/null 2>&1 || true; \
	echo "starting integration api image=$$image"; \
	docker run --name "$$container_name" -p 8000:8000 -d --rm "$$image" --host 0.0.0.0; \
	curl -s -o /dev/null --retry 10 --retry-delay 5 --retry-all-errors http://localhost:8000/general/docs; \
	PYTHONPATH=. uv run pytest $(INTEGRATION_PYTEST_ARGS)'

.PHONY: test-integration-platform
test-integration-platform:
	PYTHONPATH=. uv run pytest $(PLATFORM_INTEGRATION_PYTEST_ARGS)

.PHONY: lint
lint:
	uv run pylint --rcfile=pylintrc src
	uv run mypy src

.PHONY: publish
publish:
	./scripts/publish.sh