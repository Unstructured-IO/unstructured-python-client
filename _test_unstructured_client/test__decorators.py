import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import SDKError


FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


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
        api_key_auth=FAKE_KEY,
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
        api_key_auth=FAKE_KEY,
    )
    assert client.general.sdk_configuration.server_url == "http://localhost:8000"


def test_clean_server_url_on_empty_string():
    client = UnstructuredClient(
        server_url="",
        api_key_auth=FAKE_KEY,
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
        FAKE_KEY,
        "",
        server_url,
    )
    assert client.general.sdk_configuration.server_url == "https://unstructured-000mock.api.unstructuredapp.io"


def test_suggest_defining_url_if_401():
    with pytest.warns(UserWarning):

        client = UnstructuredClient(
            api_key_auth=FAKE_KEY,
        )
        
        filename = "_sample_docs/layout-parser-paper-fast.pdf"
        
        with open(filename, "rb") as f:
            files=shared.Files(
                content=f.read(),
                file_name=filename,
            )

        req = shared.PartitionParameters(
            files=files,
        )

        try:
            client.general.partition(req)
        except SDKError as e:
            print(e)
