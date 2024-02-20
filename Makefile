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
	sudo apt-get install jq

## install:					installs all test, dev, and experimental requirements
.PHONY: install
install: install-test install-dev

#################
# Test and Lint #
#################

.PHONY: test
test:
	PYTHONPATH=. pytest \
		_test_unstructured_client -v

.PHONY: lint
lint:
	pylint --rcfile=pylintrc src

#############
# Speakeasy #
#############

.PHONY: sdk-generate
sdk-generate:
	speakeasy generate sdk -s ./_dev/openapi_client.json -o ./ -l python

sdk-overlay-create:
	speakeasy overlay compare --schemas=./_dev/openapi.json --schemas=./_dev/openapi_client.json > ./_dev/overlay.yaml
	sed -i '/^extends:/d' ./_dev/overlay.yaml

sdk-overlay-apply:
	speakeasy overlay validate -o ./_dev/overlay.yaml
	speakeasy overlay apply -s=./_dev/openapi.json -o=./_dev/overlay.yaml > ./_dev/openapi_client_preview.json
	@cd _dev && jq . ./openapi_client_preview.json > ./openapi_client_preview.json.tmp \
		&& cp ./openapi_client_preview.json.tmp ./openapi_client_preview.json && rm ./openapi_client_preview.json.tmp


###########
# Jupyter #
###########

## run-jupyter:				starts jupyter notebook
.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''
