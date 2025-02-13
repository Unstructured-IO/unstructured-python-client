from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

import httpx
import json
import pytest
import requests
from deepdiff import DeepDiff
from httpx import Response

from requests_toolbelt.multipart.decoder import MultipartDecoder  # type: ignore

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import HTTPValidationError
from unstructured_client.models.shared.partition_parameters import Strategy
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig
from unstructured_client._hooks.custom import form_utils
from unstructured_client._hooks.custom import split_pdf_hook

FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.mark.parametrize("concurrency_level", [1, 2, 5])
@pytest.mark.parametrize(
    ("filename", "expected_ok", "strategy"),
    [
        ("_sample_docs/list-item-example-1.pdf", True, "fast"),  # 1 page
        ("_sample_docs/layout-parser-paper-fast.pdf", True, "fast"),  # 2 pages
        # NOTE(mike): using "fast" strategy fails on this file for unknown reasons
        ("_sample_docs/layout-parser-paper.pdf", True, "hi_res"),  # 16 pages
        ("_sample_docs/fake.doc", False, "fast"),
        ("_sample_docs/emoji.xlsx", True, "fast"),
        ("_sample_docs/csv-with-long-lines.csv", False, "fast"),
        ("_sample_docs/ideas-page.html", False, "fast"),
    ],
)
def test_integration_split_pdf_has_same_output_as_non_split(
    concurrency_level: int, filename: str, expected_ok: bool, strategy: str
):
    """
    Tests that output that we get from the split-by-page pdf is the same as from non-split.

    Requires unstructured-api running in bg. See Makefile for how to run it.
    Doesn't check for raw_response as there's no clear patter for how it changes with the number of pages / concurrency_level.
    """
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    if not expected_ok:
        # This will append .pdf to filename to fool first line of filetype detection, to simulate decoding error
        files.file_name += ".pdf"

    parameters = shared.PartitionParameters(
        files=files,
        strategy=strategy,
        languages=["eng"],
        split_pdf_page=True,
        split_pdf_concurrency_level=concurrency_level,
    )

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    try:
        resp_split = client.general.partition(
            server_url="http://localhost:8000",
            request=req
        )
    except (HTTPValidationError, AttributeError) as exc:
        if not expected_ok:
            assert "File does not appear to be a valid PDF" in str(exc)
            return
        else:
            assert exc is None

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = client.general.partition(
        server_url="http://localhost:8000",
        request=req,
    )

    assert len(resp_split.elements) == len(resp_single.elements)
    assert resp_split.content_type == resp_single.content_type
    assert resp_split.status_code == resp_single.status_code

    diff = DeepDiff(
        t1=resp_split.elements,
        t2=resp_single.elements,
        exclude_regex_paths=[
            r"root\[\d+\]\['metadata'\]\['parent_id'\]",
        ],
    )
    assert len(diff) == 0


@pytest.mark.parametrize(("filename", "expected_ok", "strategy"), [
    ("_sample_docs/layout-parser-paper.pdf", True, shared.Strategy.HI_RES),  # 16 pages
])
@pytest.mark.parametrize(("use_caching", "cache_dir"), [
    (True, None),  # Use default cache dir
    (True, Path(tempfile.gettempdir()) / "test_integration_unstructured_client1"),  # Use custom cache dir
    (False, None),  # Don't use caching
    (False, Path(tempfile.gettempdir()) / "test_integration_unstructured_client2"),  # Don't use caching, use custom cache dir
])
def test_integration_split_pdf_with_caching(
    filename: str,
    expected_ok: bool,
    strategy: Literal[Strategy.HI_RES],
    use_caching: bool,
    cache_dir: Path | None,
):
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    if not expected_ok:
        # This will append .pdf to filename to fool first line of filetype detection, to simulate decoding error
        files.file_name += ".pdf"

    parameters = shared.PartitionParameters(
        files=files,
        strategy=strategy,
        split_pdf_page=True,
        split_pdf_cache_tmp_data=use_caching,
        split_pdf_cache_tmp_data_dir=str(cache_dir),
    )

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    try:
        resp_split = client.general.partition(
            server_url="http://localhost:8000",
            request=req
        )
    except (HTTPValidationError, AttributeError) as exc:
        if not expected_ok:
            assert "File does not appear to be a valid PDF" in str(exc)
            return
        else:
            assert exc is None

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = client.general.partition(
        server_url="http://localhost:8000",
        request=req
    )

    assert len(resp_split.elements) == len(resp_single.elements)
    assert resp_split.content_type == resp_single.content_type
    assert resp_split.status_code == resp_single.status_code

    diff = DeepDiff(
        t1=resp_split.elements,
        t2=resp_single.elements,
        exclude_regex_paths=[
            r"root\[\d+\]\['metadata'\]\['parent_id'\]",
            r"root\[\d+\]\['element_id'\]",
        ],
    )
    assert len(diff) == 0

    # make sure the cache dir was cleaned if passed explicitly
    if cache_dir:
        assert not Path(cache_dir).exists()


@pytest.mark.parametrize("filename", ["_sample_docs/super_long_pages.pdf"])
def test_long_pages_hi_res(filename):
    req = operations.PartitionRequest(partition_parameters=shared.PartitionParameters(
        files=shared.Files(content=open(filename, "rb"), file_name=filename, ),
        strategy=shared.Strategy.HI_RES,
        split_pdf_page=True,
        split_pdf_allow_failed=True,
        split_pdf_concurrency_level=15
    ), )

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    response = client.general.partition(
        request=req,
        server_url="http://localhost:8000",
    )
    assert response.status_code == 200
    assert len(response.elements)

def test_integration_split_pdf_for_file_with_no_name():
    """
    Tests that the client raises an error when the file_name is empty.
    """
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    with open("_sample_docs/layout-parser-paper-fast.pdf", "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name="    ",
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy="fast",
            languages=["eng"],
            split_pdf_page=True,
        )
    )

    pytest.raises(ValueError, client.general.partition, request=req, server_url="http://localhost:8000")


@pytest.mark.parametrize("starting_page_number", [1, 100])
@pytest.mark.parametrize(
    "page_range, expected_ok, expected_pages",
    [
        (["1", "14"], True, (1, 14)), # Valid range, start on boundary
        (["4", "16"], True, (4, 16)), # Valid range, end on boundary
        (["2", "5"], True, (2, 5)),  # Valid range within boundary
        # A 1 page doc wouldn't normally be split,
        # but this code still needs to return the page range
        (["6", "6"], True, (6, 6)),
        (["2", "100"], False, None), # End page too high
        (["50", "100"], False, None), # Range too high
        (["-50", "5"], False, None), # Start page too low
        (["-50", "-2"], False, None), # Range too low
        (["10", "2"], False, None), # Backwards range
    ],
)
def test_integration_split_pdf_with_page_range(
    starting_page_number: int,
    page_range: list[int],
    expected_ok: bool,
    expected_pages: tuple[int, int],
    caplog,
):
    """
    Test that we can split pdfs with an arbitrary page range. Send the selected range to the API and assert that the metadata page numbers are correct.
    We should also be able to offset the metadata with starting_page_number.

    Requires unstructured-api running in bg. See Makefile for how to run it.
    """
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    filename = "_sample_docs/layout-parser-paper.pdf"
    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy="fast",
            split_pdf_page=True,
            split_pdf_page_range=page_range,
            starting_page_number=starting_page_number,
        )
    )

    try:
        resp = client.general.partition(
            server_url="http://localhost:8000",
            request=req
        )
    except ValueError as exc:
        assert not expected_ok
        assert "is out of bounds." in caplog.text
        assert "is out of bounds." in str(exc)
        return

    page_numbers = set([e["metadata"]["page_number"] for e in resp.elements])

    min_page_number = expected_pages[0] + starting_page_number - 1
    max_page_number = expected_pages[1] + starting_page_number - 1

    assert min(page_numbers) == min_page_number, f"Result should start at page {min_page_number}"
    assert max(page_numbers) == max_page_number, f"Result should end at page {max_page_number}"


@pytest.mark.parametrize("concurrency_level", [2, 3])
@pytest.mark.parametrize("allow_failed", [True, False])
@pytest.mark.parametrize(
    ("filename", "expected_ok", "strategy"),
    [
        ("_sample_docs/list-item-example-1.pdf", True, "fast"),  # 1 page
        ("_sample_docs/layout-parser-paper-fast.pdf", True, "fast"),  # 2 pages
        ("_sample_docs/layout-parser-paper.pdf", True, shared.Strategy.HI_RES),  # 16 pages
    ],
)
def test_integration_split_pdf_strict_mode(
    concurrency_level: int,
    allow_failed: bool,
    filename: str,
    expected_ok: bool,
    strategy: shared.Strategy,
    caplog
):
    """Test strict mode (allow failed = False) for split_pdf."""
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY)

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    if not expected_ok:
        # This will append .pdf to filename to fool first line of filetype detection, to simulate decoding error
        files.file_name += ".pdf"

    parameters = shared.PartitionParameters(
        files=files,
        strategy=strategy,
        languages=["eng"],
        split_pdf_page=True,
        split_pdf_concurrency_level=concurrency_level,
        split_pdf_allow_failed=allow_failed,
    )

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    try:
        resp_split = client.general.partition(
            server_url="http://localhost:8000",
            request=req
        )
    except (HTTPValidationError, AttributeError) as exc:
        if not expected_ok:
            assert "The file does not appear to be a valid PDF." in caplog.text
            assert "File does not appear to be a valid PDF" in str(exc)
            return
        else:
            assert exc is None

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = client.general.partition(
        request=req,
        server_url="http://localhost:8000",
    )

    assert len(resp_split.elements) == len(resp_single.elements)
    assert resp_split.content_type == resp_single.content_type
    assert resp_split.status_code == resp_single.status_code

    diff = DeepDiff(
        t1=resp_split.elements,
        t2=resp_single.elements,
        exclude_regex_paths=[
            r"root\[\d+\]\['metadata'\]\['parent_id'\]",
        ],
    )
    assert len(diff) == 0


@pytest.mark.asyncio
async def test_split_pdf_requests_do_retry(monkeypatch):
    """
    Test that when we split a pdf, the split requests will honor retryable errors.
    """
    mock_endpoint_called = False
    number_of_split_502s = 2
    number_of_last_page_502s = 2

    async def mock_send(_, request: httpx.Request, **kwargs):
        """
        Return a predefined number of 502s for requests with certain starting_page_number values.

        This is to make sure specific portions of the doc are retried properly.

        We want to make sure both code paths are retried.
        """
        # Assert that the SDK issues our dummy request
        # returned by the BeforeRequestHook
        nonlocal mock_endpoint_called
        if request.url.host == "localhost" and "docs" in request.url.path:
            mock_endpoint_called = True
            return Response(200, request=request)
        elif "docs" in request.url.path:
            assert False, "The server URL was not set in the dummy request"

        request_body = request.read()

        decoded_body = MultipartDecoder(request_body, request.headers.get("Content-Type"))
        form_data = form_utils.parse_form_data(decoded_body)

        nonlocal number_of_split_502s
        nonlocal number_of_last_page_502s

        if number_of_split_502s > 0:
            if "starting_page_number" in form_data and int(form_data["starting_page_number"]) < 3:
                number_of_split_502s -= 1
                return Response(502, request=request)

        if number_of_last_page_502s > 0:
            if "starting_page_number" in form_data and int(form_data["starting_page_number"]) > 12:
                number_of_last_page_502s -= 1
                return Response(502, request=request)

        mock_return_data = [{
            "type": "Title",
            "text": "Hello",
        }]

        return Response(
            200,
            request=request,
            content=json.dumps(mock_return_data),
            headers={"Content-Type": "application/json"},
        )

    monkeypatch.setattr(split_pdf_hook.httpx.AsyncClient, "send", mock_send)

    sdk = UnstructuredClient(
        api_key_auth=FAKE_KEY,
        retry_config=RetryConfig("backoff", BackoffStrategy(200, 1000, 1.5, 10000), False),
    )

    filename = "_sample_docs/layout-parser-paper.pdf"
    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            split_pdf_page=True,
            split_pdf_allow_failed=False,
            strategy="fast",
        )
    )

    res = await sdk.general.partition_async(
        server_url="http://localhost:8000",
        request=req
    )

    assert number_of_split_502s == 0
    assert number_of_last_page_502s == 0
    assert mock_endpoint_called

    assert res.status_code == 200
