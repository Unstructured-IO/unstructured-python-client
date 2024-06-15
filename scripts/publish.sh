#!/usr/bin/env bash

export TWINE_USERNAME=__token__
export TWINE_PASSWORD=${PYPI_TOKEN}

python -m pip install --upgrade pip
pip install setuptools wheel twine
python setup.py sdist bdist_wheel
twine upload dist/*
