from datetime import timedelta

import pytest

from unstructured_client import UnstructuredClient

FAKE_API_KEY = "91pmLBeETAbXCpNylRsLq11FdiZPTk"

@pytest.fixture(scope="module")
def client(platform_api_url) -> UnstructuredClient:
    _client = UnstructuredClient(
        api_key_auth=FAKE_API_KEY,
        server_url=platform_api_url,
    )
    yield _client

@pytest.fixture(autouse=True)
def mock_sleep(mocker, freezer):
    sleep_mock = mocker.patch("time.sleep")
    sleep_mock.side_effect = lambda seconds: freezer.tick(timedelta(seconds=seconds))
    yield sleep_mock