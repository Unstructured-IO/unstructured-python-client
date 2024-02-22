import os
import pypdf
import pytest
import requests
from deepdiff import DeepDiff

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
    client = UnstructuredClient( server_url="", api_key_auth=FAKE_KEY)
    assert client.general.sdk_configuration.server_url == ""


def test_unit_clean_server_url_returns_None_given_no_server_url():
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
def test_unit_clean_server_url_fixes_malformed_urls_with_positional_arguments(
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


def test_unit_suggest_defining_url_issues_a_warning_on_a_401():
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


# Requires unstructured-api running in bg. See Makefile for how to run it.
@pytest.mark.parametrize("call_threads", [1, 2, 5])
@pytest.mark.parametrize(
    "filename, expected_ok",
    [
        ("_sample_docs/list-item-example-1.pdf", True),       # 1 page
        ("_sample_docs/layout-parser-paper-fast.pdf", True),  # 2 pages
        ("_sample_docs/layout-parser-paper.pdf", True),       # 16 pages
        ("_sample_docs/fake.doc", False),
    ],
)
def test_integration_split_pdf(
    call_threads: int,
    filename: str,
    expected_ok: bool,
):
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(
        api_key_auth=FAKE_KEY,
        server_url="localhost:8000"
    )

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = shared.PartitionParameters(
        files=files,
        strategy='fast',
        languages=["eng"],
        split_pdf_page=True,
    )

    os.environ["UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS"] = str(call_threads)

    try:
        resp_split = client.general.partition(req)
    except pypdf.errors.PdfStreamError as exc:
        if expected_ok:
            raise exc
        else:
            # Parsing fake.doc will cause this error and we don't want to proceed.
            return

    req.split_pdf_page = False
    resp_single = client.general.partition(req)

    assert len(resp_split.elements) == len(resp_single.elements)
    assert resp_split.content_type == resp_single.content_type
    assert resp_split.status_code == resp_single.status_code

    # Difference in the parent_id is expected, because parent_ids are assigned when element crosses page boundary
    diff = DeepDiff(t1=resp_split.elements, t2=resp_single.elements,
                    exclude_regex_paths=r"root\[\d+\]\['metadata'\]\['parent_id'\]")
    assert len(diff) == 0
