import pytest
import logging
import re

import requests_mock

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig


FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_unit_retry_with_backoff_does_retry(caplog):
    caplog.set_level(logging.INFO)
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=10, max_interval=100, exponent=1.5, max_elapsed_time=300
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )
    
    with requests_mock.Mocker() as mock:
        # mock a 500 status code for POST requests to the api 
        mock.post("https://api.unstructured.io/general/v0/general", status_code=500)
        session = UnstructuredClient(api_key_auth=FAKE_KEY)

        with open(filename, "rb") as f:
            files=shared.Files(content=f.read(), file_name=filename)

        req = shared.PartitionParameters(files=files)

        with pytest.raises(Exception) as excinfo:
            resp = session.general.partition(req, retries=retries)    
            assert resp.status_code == 500
            assert "API error occurred" in str(excinfo.value)

        # the number of retries varies
        assert len(mock.request_history) > 1 


def test_unit_backoff_strategy_logs_retries(caplog):
    caplog.set_level(logging.INFO)
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=10, max_interval=100, exponent=1.5, max_elapsed_time=300
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )
    
    with requests_mock.Mocker() as mock:
        # mock a 500 status code for POST requests to the api 
        mock.post("https://api.unstructured.io/general/v0/general", status_code=500)
        session = UnstructuredClient(api_key_auth=FAKE_KEY)

        with open(filename, "rb") as f:
            files=shared.Files(content=f.read(), file_name=filename)

        req = shared.PartitionParameters(files=files)
        with pytest.raises(Exception):
            session.general.partition(req, retries=retries)    
    pattern = re.compile("Response status code: 500. Sleeping before retry.")
    assert bool(pattern.search(caplog.text))
