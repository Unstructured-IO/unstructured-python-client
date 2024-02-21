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
	sudo apt-get install jq

## install:					installs all test, dev, and experimental requirements
.PHONY: install
install: install-test install-dev

#################
# Test and Lint #
#################

# Assumes you have unstructured-api running on localhost:8000
.PHONY: test
test:
	PYTHONPATH=. pytest _test_unstructured_client -v


# Runs the unstructured-api in docker for tests
.PHONY: test-docker
test-docker:
	docker run --name unstructured-api -p 8000:8000 -d --rm ${DOCKER_IMAGE} --host 0.0.0.0 && \
	curl -s -o /dev/null --retry 10 --retry-delay 5 --retry-all-errors http://localhost:8000/general/docs && \
	PYTHONPATH=. pytest _test_unstructured_client -v && \
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
