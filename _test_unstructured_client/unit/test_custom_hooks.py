import logging
import re

import pytest
import requests
import httpx
from httpx import Response, ConnectError

from _test_unstructured_client.unit_utils import FixtureRequest, Mock, method_mock
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError
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

    # List to track the number of requests
    # (Use a list so we can pass a reference into mock_post)
    request_count = [0]

    def mock_post(request):
        request_count[0] += 1
        if request.url == "https://api.unstructuredapp.io/general/v0/general" and request.method == "POST":
            return Response(502, request=request)

    transport = httpx.MockTransport(mock_post)
    client = httpx.Client(transport=transport)
    session = UnstructuredClient(api_key_auth=FAKE_KEY, client=client)

    with open(filename, "rb") as f:
        files = shared.Files(content=f.read(), file_name=filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files)
    )

    with pytest.raises(Exception) as excinfo:
        resp = session.general.partition(request=req, retries=retries)
        assert resp.status_code == 502
        assert "API error occurred" in str(excinfo.value)

    # the number of retries varies
    assert request_count[0] > 1


@pytest.mark.parametrize("status_code", [500, 503])
def test_unit_backoff_strategy_logs_retries_5XX(status_code: int, caplog):
    caplog.set_level(logging.INFO)
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=10, max_interval=100, exponent=1.5, max_elapsed_time=300
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )

    def mock_post(request):
        if request.url == "https://api.unstructuredapp.io/general/v0/general" and request.method == "POST":
            return Response(status_code, request=request)

    transport = httpx.MockTransport(mock_post)
    client = httpx.Client(transport=transport)
    session = UnstructuredClient(api_key_auth=FAKE_KEY, client=client)

    with open(filename, "rb") as f:
        files = shared.Files(content=f.read(), file_name=filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files)
    )

    with pytest.raises(Exception):
        session.general.partition(request=req, retries=retries)

    pattern = re.compile(f"Failed to process a request due to API server error with status code {status_code}. "
                        "Attempting retry number 1 after sleep.")
    assert bool(pattern.search(caplog.text))


@pytest.mark.parametrize(
    ("status_code", "expect_retry"),
    [
        [500, False],
        [502, True],
        [503, True],
        [504, True],
    ]
)
def test_unit_number_of_retries_in_5xx(status_code: int, expect_retry: bool):
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=1, max_interval=10, exponent=1.5, max_elapsed_time=300
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )

    number_of_requests = [0]
    def mock_post(request):
        if request.url == "https://api.unstructuredapp.io/general/v0/general" and request.method == "POST":
            number_of_requests[0] += 1
            return Response(status_code, request=request)


    transport = httpx.MockTransport(mock_post)
    client = httpx.Client(transport=transport)
    session = UnstructuredClient(api_key_auth=FAKE_KEY, client=client)


    with open(filename, "rb") as f:
        files = shared.Files(content=f.read(), file_name=filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files)
    )

    with pytest.raises(Exception, match=f"Status {status_code}"):
        session.general.partition(request=req, retries=retries)

    if expect_retry:
        assert number_of_requests[0] > 1
    else:
        assert number_of_requests[0] == 1


def test_unit_backoff_strategy_logs_retries_connection_error(caplog):
    caplog.set_level(logging.INFO)
    filename = "README.md"
    backoff_strategy = BackoffStrategy(
        initial_interval=10, max_interval=100, exponent=1.5, max_elapsed_time=300
    )
    retries = RetryConfig(
        strategy="backoff", backoff=backoff_strategy, retry_connection_errors=True
    )

    def mock_post(request):
        raise ConnectError("Mocked connection error", request=request)

    transport = httpx.MockTransport(mock_post)
    client = httpx.Client(transport=transport)
    session = UnstructuredClient(api_key_auth=FAKE_KEY, client=client)

    with open(filename, "rb") as f:
        files = shared.Files(content=f.read(), file_name=filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files)
    )

    with pytest.raises(Exception):
        session.general.partition(request=req, retries=retries)

    pattern = re.compile(f"Failed to process a request due to connection error .*? "
                         "Attempting retry number 1 after sleep.")
    assert bool(pattern.search(caplog.text))


@pytest.mark.parametrize(
    "server_url",
    [
        # -- well-formed url --
        "https://unstructured-000mock.api.unstructuredapp.io",
        # -- common malformed urls --
        "unstructured-000mock.api.unstructuredapp.io",
        "http://unstructured-000mock.api.unstructuredapp.io/general/v0/general",
        "https://unstructured-000mock.api.unstructuredapp.io/general/v0/general",
        "unstructured-000mock.api.unstructuredapp.io/general/v0/general",
    ],
)
def test_unit_clean_server_url_fixes_malformed_paid_api_url(server_url: str):
    client = UnstructuredClient(
        server_url=server_url,
        api_key_auth=FAKE_KEY,
    )
    assert (
        client.general.sdk_configuration.server_url
        == "https://unstructured-000mock.api.unstructuredapp.io"
    )


@pytest.mark.parametrize(
    "server_url",
    [
        # -- well-formed url --
        "http://localhost:8000",
        # -- common malformed urls --
        "localhost:8000",
        "localhost:8000/general/v0/general",
        "http://localhost:8000/general/v0/general",
    ],
)
def test_unit_clean_server_url_fixes_malformed_localhost_url(server_url: str):
    client = UnstructuredClient(
        server_url=server_url,
        api_key_auth=FAKE_KEY,
    )
    assert client.general.sdk_configuration.server_url == "http://localhost:8000"


def test_unit_clean_server_url_returns_empty_string_given_empty_string():
    client = UnstructuredClient(server_url="", api_key_auth=FAKE_KEY)
    assert client.general.sdk_configuration.server_url == ""


def test_unit_clean_server_url_returns_None_given_no_server_url():
    client = UnstructuredClient(api_key_auth=FAKE_KEY)
    assert client.general.sdk_configuration.server_url == None


@pytest.mark.parametrize(
    "server_url",
    [
        # -- well-formed url --
        "https://unstructured-000mock.api.unstructuredapp.io",
        # -- malformed url --
        "unstructured-000mock.api.unstructuredapp.io/general/v0/general",
    ],
)
def test_unit_clean_server_url_fixes_malformed_urls_with_positional_arguments(server_url: str):
    client = UnstructuredClient(FAKE_KEY, "", server_url)
    assert (
        client.general.sdk_configuration.server_url
        == "https://unstructured-000mock.api.unstructuredapp.io"
    )


def test_unit_issues_warning_on_a_401(caplog, session_: Mock, response_: requests.Session):
    def mock_post(request):
        return Response(401, request=request)

    transport = httpx.MockTransport(mock_post)
    client = httpx.Client(transport=transport)
    session = UnstructuredClient(api_key_auth=FAKE_KEY, client=client)

    filename = "_sample_docs/layout-parser-paper-fast.pdf"
    with open(filename, "rb") as f:
        files = shared.Files(content=f.read(), file_name=filename)

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(files=files)
    )

    with pytest.raises(SDKError, match="API error occurred: Status 401"):
        with caplog.at_level(logging.WARNING):
            session.general.partition(request=req)

        assert any(
            "This API key is invalid against the paid API. If intending to use the free API, please initialize UnstructuredClient with `server='free-api'`."
            in message for message in caplog.messages
        )


# -- fixtures --------------------------------------------------------------------------------


@pytest.fixture()
def session_(request: FixtureRequest):
    return method_mock(request, requests.Session, "send")


@pytest.fixture()
def response_(*args, **kwargs):
    response = requests.Response()
    response.status_code = 401
    return response
