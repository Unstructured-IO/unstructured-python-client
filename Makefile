PACKAGE_NAME := unstructured-python-client
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)

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
test:
	PYTHONPATH=. pytest \
		_test_unstructured_client

.PHONY: lint
lint:
	pylint --rcfile=pylintrc src

###########
# Jupyter #
###########

## run-jupyter:				starts jupyter notebook
.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''
