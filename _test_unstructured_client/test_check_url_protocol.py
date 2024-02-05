import os
import pytest

from unstructured_client import UnstructuredClient


def get_api_key():
    api_key = os.getenv("UNS_API_KEY")
    if api_key is None:
        raise ValueError("""UNS_API_KEY environment variable not set. 
Set it in your current shell session with `export UNS_API_KEY=<api_key>`""")
    return api_key


@pytest.mark.parametrize(
    ("server_url"),
    [
        ("https://unstructured-000mock.api.unstructuredapp.io"), # correct url
        ("unstructured-000mock.api.unstructuredapp.io"),
        ("http://unstructured-000mock.api.unstructuredapp.io/general/v0/general"),
        ("https://unstructured-000mock.api.unstructuredapp.io/general/v0/general"),
        ("unstructured-000mock.api.unstructuredapp.io/general/v0/general"),
    ]
)
def test_clean_server_url_on_paid_api_url(server_url: str):
    client = UnstructuredClient(
        server_url=server_url,
        api_key_auth=get_api_key(),
    )
    assert client.general.sdk_configuration.server_url == "https://unstructured-000mock.api.unstructuredapp.io"


@pytest.mark.parametrize(
    ("server_url"),
    [
        ("http://localhost:8000"), # correct url
        ("localhost:8000"),
        ("localhost:8000/general/v0/general"),
        ("http://localhost:8000/general/v0/general"),
    ]
)
def test_clean_server_url_on_localhost(server_url: str):
    client = UnstructuredClient(
        server_url=server_url,
        api_key_auth=get_api_key(),
    )
    assert client.general.sdk_configuration.server_url == "http://localhost:8000"


def test_clean_server_url_on_empty_string():
    client = UnstructuredClient(
        server_url="",
        api_key_auth=get_api_key(),
    )
    assert client.general.sdk_configuration.server_url == ""

@pytest.mark.parametrize(
    ("server_url"),
    [
        ("https://unstructured-000mock.api.unstructuredapp.io"),
        ("unstructured-000mock.api.unstructuredapp.io/general/v0/general"),
    ]
)
def test_clean_server_url_with_positional_arguments(server_url: str):
    client = UnstructuredClient(
        get_api_key(),
        "",
        server_url,
    )
    assert client.general.sdk_configuration.server_url == "https://unstructured-000mock.api.unstructuredapp.io"
