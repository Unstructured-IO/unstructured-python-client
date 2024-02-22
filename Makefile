PACKAGE_NAME := unstructured-python-client
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)
DOCKER_IMAGE ?= downloads.unstructured.io/unstructured-io/unstructured-api:latest

###########
# Install #
###########

.PHONY: install-test
install-test:
	pip install pytest
	pip install requests_mock

.PHONY: install-dev
install-dev:
	pip install jupyter
	pip install pylint

## install:					installs all test, dev, and experimental requirements
.PHONY: install
install: install-test install-dev

#################
# Test and Lint #
#################

.PHONY: test
test: test-unit test-integration-docker

.PHONY: test-unit
test-unit:
	PYTHONPATH=. pytest _test_unstructured_client -v -k "unit"

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

#############
# Speakeasy #
#############

.PHONY: client-generate
client-generate:
	speakeasy generate sdk -s ./openapi.json -o ./ -l python

diff-openapi:
	speakeasy overlay compare --schemas=./openapi.json --schemas=./openapi_backend.json > ./overlay.yaml


###########
# Jupyter #
###########

## run-jupyter:				starts jupyter notebook
.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''
