PACKAGE_NAME := unstructured-python-client
CURRENT_DIR := $(shell pwd)
ARCH := $(shell uname -m)

###########
# Install #
###########

test-install:
	pip install requests_mock

#################
# Test and Lint #
#################

.PHONY: test
test:
	PYTHONPATH=. pytest \
		tests