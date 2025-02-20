import os

import pytest

from unstructured_client import UnstructuredClient, RetryConfig
from unstructured_client.utils import BackoffStrategy

FAKE_API_KEY = "91pmLBeETAbXCpNylRsLq11FdiZPTk"


@pytest.fixture(scope="module")
def platform_api_url():
    return "https://platform.unstructuredapp.io"


@pytest.fixture(scope="module")
def client(platform_api_url) -> UnstructuredClient:
    _client = UnstructuredClient(
        api_key_auth=FAKE_API_KEY,
        server_url=platform_api_url,
        retry_config=RetryConfig(
            strategy="backoff",
            retry_connection_errors=False,
            backoff=BackoffStrategy(
                max_elapsed_time=0, max_interval=0, exponent=0, initial_interval=0
            ),
        ),
    )
    yield _client
