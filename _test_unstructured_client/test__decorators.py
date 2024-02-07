import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import SDKError


FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


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
def test_clean_server_url_fixes_malformed_paid_api_url(server_url: str):
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
def test_clean_server_url_fixes_malformed_localhost_url(server_url: str):
    client = UnstructuredClient(
        server_url=server_url,
        api_key_auth=FAKE_KEY,
    )
    assert client.general.sdk_configuration.server_url == "http://localhost:8000"


def test_clean_server_url_returns_empty_string_given_empty_string():
    client = UnstructuredClient( server_url="", api_key_auth=FAKE_KEY)
    assert client.general.sdk_configuration.server_url == ""


def test_clean_server_url_returns_None_given_no_server_url():
    client = UnstructuredClient(
        api_key_auth=FAKE_KEY,
    )
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
def test_clean_server_url_fixes_malformed_urls_with_positional_arguments(
    server_url: str,
):
    client = UnstructuredClient(
        FAKE_KEY,
        "",
        server_url,
    )
    assert (
        client.general.sdk_configuration.server_url
        == "https://unstructured-000mock.api.unstructuredapp.io"
    )


def test_suggest_defining_url_issues_a_warning_on_a_401():
    client = UnstructuredClient(
        api_key_auth=FAKE_KEY,
    )

    filename = "_sample_docs/layout-parser-paper-fast.pdf"

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = shared.PartitionParameters(
        files=files,
    )
    
    with pytest.raises(SDKError, match="API error occurred: Status 401"):
        with pytest.warns(
            UserWarning,
            match="If intending to use the paid API, please define `server_url` in your request.",
        ):
            client.general.partition(req)
