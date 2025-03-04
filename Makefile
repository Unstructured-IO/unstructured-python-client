PACKAGE_NAME := unstructured-python-client
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)
DOCKER_IMAGE ?= downloads.unstructured.io/unstructured-io/unstructured-api:latest

###########
# Install #
###########

## install:					installs all test, dev, and experimental requirements
.PHONY: install
install:
	pip install -U poetry
	python scripts/prepare-readme.py
	poetry install

## install-speakeasy-cli:			download the speakeasy cli tool
.PHONY: install-speakeasy-cli
install-speakeasy-cli:
	curl -fsSL https://raw.githubusercontent.com/speakeasy-api/speakeasy/main/install.sh | sh

## install-test:				install test requirements as they cannot be put into pyproject.toml due to python version requirements mismatch
.PHONY: install-test-contract
install-test-contract:
	pip install unstructured pytest-httpx

#################
# Test and Lint #
#################

.PHONY: test
test: test-unit test-integration-docker

.PHONY: test-unit
test-unit:
	PYTHONPATH=. pytest _test_unstructured_client -v -k "unit"

.PHONY: test-contract
test-contract:
	PYTHONPATH=. pytest _test_contract -v

# Assumes you have unstructured-api running on localhost:8000
.PHONY: test-integration
test-integration:
	PYTHONPATH=. pytest _test_unstructured_client -v -k "integration"

# Runs the unstructured-api in docker for tests
.PHONY: test-integration-docker
test-integration-docker:
	-docker stop unstructured-api && docker kill unstructured-api
	docker run --name unstructured-api -p 8000:8000 -d --rm ${DOCKER_IMAGE} --host 0.0.0.0 && \
	curl -s -o /dev/null --retry 10 --retry-delay 5 --retry-all-errors http://localhost:8000/general/docs && \
	PYTHONPATH=. pytest _test_unstructured_client -v -k "integration" && \
	docker kill unstructured-api

.PHONY: lint
lint:
	pylint --rcfile=pylintrc src
	mypy src

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