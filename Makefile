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

## install-speakeasy-cli:			download the speakeasy cli tool
.PHONY: install-speakeasy-cli
install-speakeasy-cli:
	curl -fsSL https://raw.githubusercontent.com/speakeasy-api/speakeasy/main/install.sh | sh

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

#############
# Speakeasy #
#############

## download-openapi-specs:			         Download the openapi specs from the Serverless and Platform APIs
.PHONY: download-openapi-specs
download-openapi-specs:
	wget -nv -q -O openapi_serverless.json https://api.unstructuredapp.io/general/openapi.json
	wget -nv -q -O openapi_platform_api.json https://platform.unstructuredapp.io/openapi.json

## client-merge-serverless-platform:		Merge the Serverless and Platform APIs specs into a single schema
.PHONY: client-merge-serverless-platform
client-merge-serverless-platform:
	speakeasy merge -s ./openapi_platform_api.json -s ./openapi_serverless.json -o ./openapi_merged.yaml

## client-apply-overlay:		            Apply overlay on the merged schema
.PHONY: client-apply-overlay
client-apply-overlay:
	speakeasy overlay validate -o ./overlay_client.yaml
	speakeasy overlay apply -s ./openapi_merged.yaml -o ./overlay_client.yaml > ./openapi_platform_serverless_client.yaml

## client-generate-unified-sdk-local:		Generate the SDK from the merged schema
.PHONY: client-generate-unified-sdk-local
client-generate-unified-sdk-local:
	speakeasy generate sdk -s ./openapi_platform_serverless_client.yaml -o ./ -l python

## client-generate-sdk:			             Do all the steps to generate the SDK
.PHONY: client-generate-sdk
client-generate-sdk: download-openapi-specs client-merge-serverless-platform client-apply-overlay client-generate-unified-sdk-local


.PHONY: publish
publish:
	./scripts/publish.sh

###########
# Jupyter #
###########

## run-jupyter:				starts jupyter notebook
.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''