import httpx
import pytest

from unstructured_client.models import operations
from unstructured_client import UnstructuredClient, basesdk, utils


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


@pytest.mark.parametrize(
    "sdk_endpoint_name",
    [
        ("general.partition"),
    ],
)
def test_endpoint_uses_correct_url(monkeypatch, sdk_endpoint_name):
    # Test 1
    # Pass server_url to the client, no path
    s = UnstructuredClient(server_url="http://localhost:8000")
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to client and ignored, got {e}")

    # Test 2
    # Pass server_url to the client, with path
    s = UnstructuredClient(server_url="http://localhost:8000/my/endpoint")
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to client and was not stripped, got {e}")

    # Test 3
    # Pass server_url to the endpoint, no path
    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        client_method(request={}, server_url="http://localhost:8000")
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to endpoint and ignored, got {e}")

    # Test 4
    # Pass server_url to the endpoint, with path
    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        client_method(request={}, server_url="http://localhost:8000/my/endpoint")
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to endpoint and ignored, got {e}")


    # Test 5
    # No server_url, should take the default
    server_url = "https://api.unstructuredapp.io" if "partition" in sdk_endpoint_name else "https://platform.unstructuredapp.io"

    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        server_url,
        monkeypatch
    )

    try:
        client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"Default url not used, got {e}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sdk_endpoint_name",
    [
        ("general.partition_async"),
    ],
)
async def test_async_endpoint_uses_correct_url(monkeypatch, sdk_endpoint_name):
    # Test 1
    # Pass server_url to the client, no path
    s = UnstructuredClient(server_url="http://localhost:8000")
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        await client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to client and ignored, got {e}")

    # Test 2
    # Pass server_url to the client, with path
    s = UnstructuredClient(server_url="http://localhost:8000/my/endpoint")
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        await client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to client and was not stripped, got {e}")

    # Test 3
    # Pass server_url to the endpoint, no path
    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        await client_method(request={}, server_url="http://localhost:8000")
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to endpoint and ignored, got {e}")

    # Test 4
    # Pass server_url to the endpoint, with path
    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        "http://localhost:8000",
        monkeypatch
    )

    try:
        await client_method(request={}, server_url="http://localhost:8000/my/endpoint")
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"server_url was passed to endpoint and ignored, got {e}")


    # Test 5
    # No server_url, should take the default
    server_url = "https://api.unstructuredapp.io" if "partition" in sdk_endpoint_name else "https://platform.unstructuredapp.io"

    s = UnstructuredClient()
    client_method = get_client_method_with_mock(
        sdk_endpoint_name,
        s,
        server_url,
        monkeypatch
    )

    try:
        await client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"Default url not used, got {e}")
