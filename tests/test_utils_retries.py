import os
import pytest

import requests_mock

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig


def get_api_key():
    api_key = os.getenv("UNS_API_KEY")
    if api_key is None:
        raise ValueError("""UNS_API_KEY environment variable not set. 
Set it in your current shell session with `export UNS_API_KEY=<api_key>`""")
    return api_key

# this test requires UNS_API_KEY be set in your shell session. Ex: `export UNS_API_KEY=<api_key>`
def test_backoff_strategy():
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=100, max_interval=1000, exponent=1.5, max_elapsed_time=3000
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )
    
    with requests_mock.Mocker() as mock:
        # mock a 500 status code for POST requests to the api 
        mock.post("https://api.unstructured.io/general/v0/general", status_code=500)
        session = UnstructuredClient(api_key_auth=get_api_key())

        with open(filename, "rb") as f:
            files=shared.Files(
                content=f.read(),
                file_name=filename,
            )

        req = shared.PartitionParameters(files=files)

        with pytest.raises(Exception) as excinfo:
            resp = session.general.partition(req, retries=retries)    
            assert resp.status_code == 500
            assert "API error occurred" in str(excinfo.value)

        # the number of retries varies
        assert len(mock.request_history) > 1 
