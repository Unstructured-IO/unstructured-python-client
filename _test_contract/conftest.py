import os
from datetime import timedelta
from pathlib import Path

from freezegun import freeze_time
import pytest

from unstructured_client import UnstructuredClient, utils

# Python 3.9 workaround: eagerly import retries to avoid lazy import race condition
# This prevents a KeyError in module lock when templates.py triggers lazy import of utils.retries
from unstructured_client.utils import retries  # noqa: F401

FAKE_API_KEY = "91pmLBeETAbXCpNylRsLq11FdiZPTk"


@pytest.fixture(scope="module")
def platform_client(platform_api_url) -> UnstructuredClient:
    # settings the retry config to always try 3 times after a fail = 4 requests sent
    _client = UnstructuredClient(
        api_key_auth=FAKE_API_KEY,
        server_url=platform_api_url,
        retry_config=utils.RetryConfig(
            "backoff", utils.BackoffStrategy(
                initial_interval=3000,
                max_interval=3000,
                exponent=1.0,
                max_elapsed_time=8000
            ),
            retry_connection_errors=True
        )
    )
    yield _client


@pytest.fixture(scope="module")
def serverless_client(serverless_api_url) -> UnstructuredClient:
    # settings the retry config to always try 3 times after a fail = 4 requests sent
    _client = UnstructuredClient(
        api_key_auth=FAKE_API_KEY,
        server_url=serverless_api_url,
        retry_config = utils.RetryConfig(
        "backoff", utils.BackoffStrategy(
            initial_interval=3000,
            max_interval=3000,
            exponent=1.0,
            max_elapsed_time=8000
        ),
        retry_connection_errors=True
    )
    )
    yield _client


@pytest.fixture()
def freezer():
    ignore = ['_pytest.terminal', '_pytest.runner']
    freezer = freeze_time(ignore=ignore)
    frozen_time = freezer.start()
    yield frozen_time
    freezer.stop()

@pytest.fixture(autouse=True)
def mock_sleep(mocker, freezer):
    sleep_mock = mocker.patch("time.sleep")
    sleep_mock.side_effect = lambda seconds: freezer.tick(timedelta(seconds=seconds))
    yield sleep_mock


@pytest.fixture(scope="module")
def platform_api_url():
    return "https://platform.unstructuredapp.io"


@pytest.fixture(scope="module")
def serverless_api_url():
    return "https://api.unstructuredapp.io"


@pytest.fixture(scope="module")
def dummy_partitioned_text():
    return """[
  {
    "type": "NarrativeText",
    "element_id": "b7dca0363a83468b9e7326c0c1caf93e",
    "text": "March 17, 2022",
    "metadata": {
      "detection_class_prob": 0.35799261927604675,
      "coordinates": {
        "points": [
          [
            1447.871337890625,
            301.74810791015625
          ],
          [
            1447.871337890625,
            326.5603332519531
          ],
          [
            1616.6922607421875,
            326.5603332519531
          ],
          [
            1616.6922607421875,
            301.74810791015625
          ]
        ],
        "system": "PixelSpace",
        "layout_width": 1700,
        "layout_height": 2200
      },
      "last_modified": "2024-02-07T14:23:29",
      "filetype": "application/pdf",
      "languages": [
        "eng"
      ],
      "page_number": 1,
      "file_directory": "data",
      "filename": "MyDocument.pdf"
    }
  }
]"""


@pytest.fixture(scope="module")
def doc_path() -> Path:
    samples_path = Path(__file__).resolve().parents[1] / "_sample_docs"
    assert samples_path.exists()
    return samples_path
