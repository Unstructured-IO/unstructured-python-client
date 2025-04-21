import pytest
from dataclasses import dataclass
from unstructured_client import UnstructuredClient, utils


# Raise one of these from our mock to return to the test code
class BaseUrlCorrect(Exception):
    pass


class BaseUrlIncorrect(Exception):
    pass


def get_client_method_with_mock(
        sdk_endpoint_name,
        client_instance,
        mocked_server_url,
        monkeypatch
):
    """
    Given an endpoint name, e.g. "general.partition", return a reference
    to that method off of the given client instance.

    The client's _build_request will have the following mock:
        Assert that the provided server_url is passed into _build_request.
        Raise a custom exception to get back to the test.
    """
    # Mock this to get past param validation
    def mock_unmarshal(*args, **kwargs):
        return {}

    monkeypatch.setattr(utils, "unmarshal", mock_unmarshal)

    # Assert that the correct base_url makes it to here
    def mock_build_request(*args, base_url, **kwargs):
        if base_url == mocked_server_url:
            raise BaseUrlCorrect
        else:
            raise BaseUrlIncorrect(base_url)

    # Find the method from the given string
    class_name, method_name = sdk_endpoint_name.split(".")
    endpoint_class = getattr(client_instance, class_name)
    endpoint_method = getattr(endpoint_class, method_name)

    if "async" in method_name:
        monkeypatch.setattr(endpoint_class, "_build_request_async", mock_build_request)
    else:
        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)

    return endpoint_method

@dataclass
class URLTestCase:
    description: str
    sdk_endpoint_name: str
    # url when you init the client (global for all endpoints)
    client_url: str | None
    # url when you init the SDK endpoint (vary per endpoint)
    endpoint_url: str | None
    # expected url when actually making the HTTP request in build_request
    expected_url: str

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        URLTestCase(
            description="non UNST domain client-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url="http://localhost:8000",
            endpoint_url=None,
            expected_url="http://localhost:8000"
        ),
        URLTestCase(
            description="non UNST domain client-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url="http://localhost:8000/my/endpoint",
            endpoint_url=None,
            expected_url="http://localhost:8000/my/endpoint"
        ),
        URLTestCase(
            description="non UNST domain endpoint-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="http://localhost:8000",
            expected_url="http://localhost:8000"
        ),
        URLTestCase(
            description="non UNST domain endpoint-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="http://localhost:8000/my/endpoint",
            expected_url="http://localhost:8000/my/endpoint"
        ),
        URLTestCase(
            description="UNST domain client-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url="https://unstructured-000mock.api.unstructuredapp.io",
            endpoint_url=None,
            expected_url="https://unstructured-000mock.api.unstructuredapp.io"
        ),
        URLTestCase(
            description="UNST domain client-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url="https://unstructured-000mock.api.unstructuredapp.io/my/endpoint/",
            endpoint_url=None,
            expected_url="https://unstructured-000mock.api.unstructuredapp.io"
        ),
        URLTestCase(
            description="UNST domain endpoint-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="https://unstructured-000mock.api.unstructuredapp.io",
            expected_url="https://unstructured-000mock.api.unstructuredapp.io"
        ),
        URLTestCase(
            description="UNST domain endpoint-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="https://unstructured-000mock.api.unstructuredapp.io/my/endpoint/",
            expected_url="https://unstructured-000mock.api.unstructuredapp.io"
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url=None,
            expected_url="https://api.unstructuredapp.io"
        ),
    ]
)
async def test_async_endpoint_uses_correct_url(monkeypatch, case: URLTestCase):
    if case.client_url:
        s = UnstructuredClient(server_url=case.client_url)
    else:
        s = UnstructuredClient()

    client_method = get_client_method_with_mock(
        case.sdk_endpoint_name,
        s,
        case.expected_url,
        monkeypatch
    )

    try:
        if case.endpoint_url:
            await client_method(request={}, server_url=case.endpoint_url)
        else:
            await client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(
            f"{case.description}: Expected {case.expected_url}, got {e}"
        )
