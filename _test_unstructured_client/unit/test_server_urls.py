from dataclasses import dataclass

import pytest

from unstructured_client import UnstructuredClient, utils


# Raise one of these from our mock to return to the test code
class BaseUrlCorrect(Exception):
    pass


class BaseUrlIncorrect(Exception):
    pass


def get_client_method_with_mock(
    sdk_endpoint_name, client_instance, mocked_server_url, monkeypatch
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
    # expected url when actually making the HTTP request in build_request
    expected_url: str
    # url when you init the client (global for all endpoints)
    client_url: str | None = None
    # url when you init the SDK endpoint (vary per endpoint)
    endpoint_url: str | None = None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        URLTestCase(
            description="custom client-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url="http://localhost:8000/",
            endpoint_url=None,
            expected_url="http://localhost:8000",
        ),
        URLTestCase(
            description="custom client-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url="http://localhost:8000/my/endpoint/",
            endpoint_url=None,
            expected_url="http://localhost:8000/my/endpoint",
        ),
        URLTestCase(
            description="custom endpoint-level URL, no path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="http://localhost:8000/",
            expected_url="http://localhost:8000",
        ),
        URLTestCase(
            description="custom endpoint-level URL, with path",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url="http://localhost:8000/my/endpoint/",
            expected_url="http://localhost:8000/my/endpoint",
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="general.partition_async",
            client_url=None,
            endpoint_url=None,
            expected_url="https://api.unstructuredapp.io",
        ),
    ],
)
async def test_async_endpoint_uses_correct_url(monkeypatch, case: URLTestCase):
    if case.client_url:
        s = UnstructuredClient(server_url=case.client_url)
    else:
        s = UnstructuredClient()

    client_method = get_client_method_with_mock(
        case.sdk_endpoint_name, s, case.expected_url, monkeypatch
    )

    try:
        if case.endpoint_url:
            await client_method(request={}, server_url=case.endpoint_url)
        else:
            await client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"{case.description}: Expected {case.expected_url}, got {e}")


@pytest.mark.parametrize(
    "case",
    [
        URLTestCase(
            description="custom client-level URL, no path",
            sdk_endpoint_name="destinations.create_destination",
            client_url="http://localhost:8000/",
            endpoint_url=None,
            expected_url="http://localhost:8000",
        ),
        URLTestCase(
            description="custom client-level URL, with path",
            sdk_endpoint_name="sources.create_source",
            client_url="http://localhost:8000/my/endpoint/",
            endpoint_url=None,
            expected_url="http://localhost:8000/my/endpoint",
        ),
        URLTestCase(
            description="custom endpoint-level URL, no path",
            sdk_endpoint_name="jobs.get_job",
            client_url=None,
            endpoint_url="http://localhost:8000",
            expected_url="http://localhost:8000",
        ),
        URLTestCase(
            description="custom endpoint-level URL, with path",
            sdk_endpoint_name="workflows.create_workflow",
            client_url=None,
            endpoint_url="http://localhost:8000/my/endpoint",
            expected_url="http://localhost:8000/my/endpoint",
        ),
        URLTestCase(
            description="transform platform client-level URL with the app's /api/v1 suffix",
            sdk_endpoint_name="jobs.list_jobs",
            client_url="https://platform-api.transform.unstructured.io/api/v1",
            endpoint_url=None,
            expected_url="https://platform-api.transform.unstructured.io",
        ),
        URLTestCase(
            description="partition client level with path",
            sdk_endpoint_name="general.partition",
            client_url="https://api.unstructuredapp.io/general/v0/general",
            endpoint_url=None,
            expected_url="https://api.unstructuredapp.io",
        ),
        URLTestCase(
            description="partition endpoint level with path",
            sdk_endpoint_name="general.partition",
            client_url=None,
            endpoint_url="https://api.unstructuredapp.io/general/v0/general",
            expected_url="https://api.unstructuredapp.io",
        ),
        URLTestCase(
            description="partition default url",
            sdk_endpoint_name="general.partition",
            client_url=None,
            endpoint_url=None,
            expected_url="https://api.unstructuredapp.io",
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="destinations.create_destination",
            client_url=None,
            endpoint_url=None,
            expected_url="https://platform.unstructuredapp.io",
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="sources.create_source",
            client_url=None,
            endpoint_url=None,
            expected_url="https://platform.unstructuredapp.io",
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="jobs.get_job",
            client_url=None,
            endpoint_url=None,
            expected_url="https://platform.unstructuredapp.io",
        ),
        URLTestCase(
            description="default URL fallback",
            sdk_endpoint_name="workflows.create_workflow",
            client_url=None,
            endpoint_url=None,
            expected_url="https://platform.unstructuredapp.io",
        ),
    ],
)
def test_endpoint_uses_correct_url(monkeypatch, case: URLTestCase):
    if case.client_url:
        s = UnstructuredClient(server_url=case.client_url)
    else:
        s = UnstructuredClient()

    client_method = get_client_method_with_mock(
        case.sdk_endpoint_name, s, case.expected_url, monkeypatch
    )

    try:
        if case.endpoint_url:
            client_method(request={}, server_url=case.endpoint_url)
        else:
            client_method(request={})
    except BaseUrlCorrect:
        pass
    except BaseUrlIncorrect as e:
        pytest.fail(f"{case.description}: Expected {case.expected_url}, got {e}")


@pytest.mark.parametrize(
    "client_url,endpoint_url",
    [
        # -- the value the Transform Platform's API Keys page hands you, passed at the
        # -- client level and at the operation level --
        ("https://platform-api.transform.unstructured.io/api/v1", None),
        (None, "https://platform-api.transform.unstructured.io/api/v1"),
        # -- and the bare host, which must not regress --
        ("https://platform-api.transform.unstructured.io", None),
        (None, "https://platform-api.transform.unstructured.io"),
    ],
)
def test_platform_request_url_has_a_single_api_prefix(client_url, endpoint_url):
    """The operation path already carries /api/v1, so the base URL must not repeat it.

    A doubled /api/v1/api/v1/jobs/ matches no route on the Platform API and 404s.
    """
    import httpx

    sent = []

    def capture(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        return httpx.Response(200, json=[])

    client = UnstructuredClient(
        api_key_auth="fake-key",
        server_url=client_url,
        client=httpx.Client(transport=httpx.MockTransport(capture)),
    )

    if endpoint_url:
        client.jobs.list_jobs(request={}, server_url=endpoint_url)
    else:
        client.jobs.list_jobs(request={})

    assert sent == ["https://platform-api.transform.unstructured.io/api/v1/jobs/"]


@pytest.mark.parametrize(
    "client_url,endpoint_url,expected_url",
    [
        # -- a self-hosted deployment at the root --
        (
            "http://localhost:8000",
            None,
            "http://localhost:8000/api/v1/jobs/",
        ),
        (
            None,
            "http://localhost:8000",
            "http://localhost:8000/api/v1/jobs/",
        ),
        # -- and one behind a subpath, whose path must survive --
        (
            "http://localhost:8000/my/endpoint",
            None,
            "http://localhost:8000/my/endpoint/api/v1/jobs/",
        ),
        (
            None,
            "http://localhost:8000/my/endpoint",
            "http://localhost:8000/my/endpoint/api/v1/jobs/",
        ),
    ],
)
def test_non_unstructured_host_keeps_its_path(client_url, endpoint_url, expected_url):
    """A host that is not ours may legitimately serve the API beneath a subpath."""
    import httpx

    sent = []

    def capture(request: httpx.Request) -> httpx.Response:
        sent.append(str(request.url))
        return httpx.Response(200, json=[])

    client = UnstructuredClient(
        api_key_auth="fake-key",
        server_url=client_url,
        client=httpx.Client(transport=httpx.MockTransport(capture)),
    )

    if endpoint_url:
        client.jobs.list_jobs(request={}, server_url=endpoint_url)
    else:
        client.jobs.list_jobs(request={})

    assert sent == [expected_url]
