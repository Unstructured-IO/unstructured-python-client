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
	pip install poetry
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

## client-generate:			Pull the openapi spec from the free hosted API and generate the SDK
.PHONY: client-generate
client-generate:
	wget -nv -q -O openapi.json https://api.unstructured.io/general/openapi.json
	speakeasy overlay validate -o ./overlay_client.yaml
	speakeasy overlay apply -s ./openapi.json -o ./overlay_client.yaml > ./openapi_client.json
	speakeasy generate sdk -s ./openapi_client.json -o ./ -l python

## client-generate-local:			Generate the SDK using a local copy of openapi.json
.PHONY: client-generate-local
client-generate-local:
	speakeasy overlay validate -o ./overlay_client.yaml
	speakeasy overlay apply -s ./openapi.json -o ./overlay_client.yaml > ./openapi_client.json
	speakeasy generate sdk -s ./openapi_client.json -o ./ -l python

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
