import httpx
import pytest

from unstructured_client.models import operations
from unstructured_client import UnstructuredClient, basesdk, utils


# Raise from our mock so we can get out of the client code
class StopClientException(Exception):
    pass


@pytest.mark.parametrize(
    "method_name",
    [
        ("general.partition"),
        ("destinations.create_destination"),
        ("destinations.delete_destination"),
        ("destinations.get_destination"),
        ("destinations.list_destinations"),
        ("destinations.update_destination"),
        ("jobs.cancel_job"),
        ("jobs.get_job"),
        ("jobs.list_jobs"),
        ("sources.create_source"),
        ("sources.delete_source"),
        ("sources.get_source"),
        ("sources.list_sources"),
        ("sources.update_source"),
        ("workflows.create_workflow"),
        ("workflows.delete_workflow"),
        ("workflows.get_workflow"),
        ("workflows.list_workflows"),
        ("workflows.run_workflow"),
        ("workflows.update_workflow"),
    ],
)
def test_endpoint_uses_correct_url(monkeypatch, method_name):
    # Mock this to get past param validation
    def mock_unmarshal(*args, **kwargs):
        return {}

    monkeypatch.setattr(utils, "unmarshal", mock_unmarshal)

    print(method_name)
    # Use these in the mock
    server_url = "http://localhost:8000"
    assertion_message = ""

    # Assert that the correct base_url makes it to here
    def mock_build_request(*args, base_url, **kwargs):
        nonlocal assertion_message
        nonlocal server_url

        assert base_url == server_url, assertion_message
        raise StopClientException  # We're good, let's bail

    endpoint_class_name, endpoint_method_name = method_name.split(".")

    # Test 1
    # Pass server_url to the client, no path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to client and ignored"
        s = UnstructuredClient(server_url="http://localhost:8000")

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        endpoint_method(request={})

    # Test 2
    # Pass server_url to the client, with path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to client and was not stripped"
        s = UnstructuredClient(server_url="http://localhost:8000/my/endpoint")

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        endpoint_method(request={})

    # Test 3
    # Pass server_url to the endpoint, no path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to endpoint and ignored"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        endpoint_method(
            request={},
            server_url="http://localhost:8000",
        )

    # Test 4
    # Pass server_url to the endpoint, with path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to endpoint and was not stripped"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        endpoint_method(
            request={},
            server_url="http://localhost:8000/my/endpoint",
        )

    # Test 5
    # No server_url, should take the default
    with pytest.raises(StopClientException):
        assertion_message = "Default url was not used"
        server_url = "https://api.unstructuredapp.io" if method_name == "general.partition" else "https://platform.unstructuredapp.io"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        endpoint_method(
            request={},
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name",
    [
        ("general.partition_async"),
        ("destinations.create_destination_async"),
        ("destinations.delete_destination_async"),
        ("destinations.get_destination_async"),
        ("destinations.list_destinations_async"),
        ("destinations.update_destination_async"),
        ("jobs.cancel_job_async"),
        ("jobs.get_job_async"),
        ("jobs.list_jobs_async"),
        ("sources.create_source_async"),
        ("sources.delete_source_async"),
        ("sources.get_source_async"),
        ("sources.list_sources_async"),
        ("sources.update_source_async"),
        ("workflows.create_workflow_async"),
        ("workflows.delete_workflow_async"),
        ("workflows.get_workflow_async"),
        ("workflows.list_workflows_async"),
        ("workflows.run_workflow_async"),
        ("workflows.update_workflow_async"),
    ],
)
async def test_async_endpoint_uses_correct_url(monkeypatch, method_name):
    # Mock this to get past param validation
    def mock_unmarshal(*args, **kwargs):
        return {}

    monkeypatch.setattr(utils, "unmarshal", mock_unmarshal)

    print(method_name)
    # Use these in the mock
    server_url = "http://localhost:8000"
    assertion_message = ""

    # Assert that the correct base_url makes it to here
    def mock_build_request(*args, base_url, **kwargs):
        nonlocal assertion_message
        nonlocal server_url

        assert base_url == server_url, assertion_message
        raise StopClientException  # We're good, let's bail

    endpoint_class_name, endpoint_method_name = method_name.split(".")

    # Test 1
    # Pass server_url to the client, no path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to client and ignored"
        s = UnstructuredClient(server_url="http://localhost:8000")

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        await endpoint_method(request={})

    # Test 2
    # Pass server_url to the client, with path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to client and was not stripped"
        s = UnstructuredClient(server_url="http://localhost:8000/my/endpoint")

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        await endpoint_method(request={})

    # Test 3
    # Pass server_url to the endpoint, no path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to endpoint and ignored"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        await endpoint_method(
            request={},
            server_url="http://localhost:8000",
        )

    # Test 4
    # Pass server_url to the endpoint, with path
    with pytest.raises(StopClientException):
        assertion_message = "server_url was passed to endpoint and was not stripped"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        await endpoint_method(
            request={},
            server_url="http://localhost:8000/my/endpoint",
        )

    # Test 5
    # No server_url, should take the default
    with pytest.raises(StopClientException):
        assertion_message = "Default url was not used"
        server_url = "https://api.unstructuredapp.io" if method_name == "general.partition" else "https://platform.unstructuredapp.io"
        s = UnstructuredClient()

        endpoint_class = getattr(s, endpoint_class_name)
        endpoint_method = getattr(endpoint_class, endpoint_method_name)

        monkeypatch.setattr(endpoint_class, "_build_request", mock_build_request)
        await endpoint_method(
            request={},
            )
