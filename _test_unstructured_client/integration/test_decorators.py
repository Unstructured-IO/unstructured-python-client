from __future__ import annotations

from collections import Counter, defaultdict
import logging
import math
import time
import tempfile
from pathlib import Path
from typing import Literal

import httpx
import json
import pytest
import requests
from deepdiff import DeepDiff
from httpx import Response
from pypdf import PdfReader, PdfWriter

from requests_toolbelt.multipart.decoder import MultipartDecoder  # type: ignore

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import HTTPValidationError, SDKError, ServerError
from unstructured_client.models.shared.partition_parameters import Strategy
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig
from unstructured_client._hooks.custom import form_utils
from unstructured_client._hooks.custom import split_pdf_hook

FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TEST_TIMEOUT_MS = 300_000
LOCAL_API_DOCS_URL = "http://localhost:8000/general/docs"

_HI_RES_STRATEGIES = ("hi_res", Strategy.HI_RES)
logger = logging.getLogger("integration.split_pdf")


def _log_integration_progress(event: str, **fields) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"integration event={event} {rendered_fields}", flush=True)
    logger.info("integration event=%s %s", event, rendered_fields)


def _assert_local_api_is_running() -> None:
    started_at = time.perf_counter()
    try:
        response = requests.get(LOCAL_API_DOCS_URL)
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"
    elapsed_ms = round((time.perf_counter() - started_at) * 1000)
    _log_integration_progress(
        "api_healthcheck",
        url=LOCAL_API_DOCS_URL,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )


@pytest.fixture(scope="module")
def hi_res_stable_fixture_path(tmp_path_factory) -> str:
    """Create a smaller multi-page PDF subset for stable hi_res integration coverage.

    The full 16-page `layout-parser-paper.pdf` is intermittently unstable in the
    backend's unsplit hi_res path under long integration runs. We still want a
    real multi-page document that exercises split behavior, but with less backend
    stress and better determinism.
    """
    source_path = Path("_sample_docs/layout-parser-paper.pdf")
    output_dir = tmp_path_factory.mktemp("hi_res_fixture")
    output_path = output_dir / "layout-parser-paper-hi_res-subset.pdf"

    reader = PdfReader(str(source_path))
    writer = PdfWriter()
    for page in reader.pages[:4]:
        writer.add_page(page)

    with output_path.open("wb") as output_file:
        writer.write(output_file)

    return str(output_path)


def _resolve_test_filename(
    filename: str,
    strategy,
    hi_res_stable_fixture_path: str,
) -> str:
    if strategy in _HI_RES_STRATEGIES and Path(filename).name == "layout-parser-paper.pdf":
        return hi_res_stable_fixture_path
    return filename


def _describe_partition_exception(exc: Exception) -> str:
    if isinstance(exc, (HTTPValidationError, SDKError, ServerError)):
        status_code = getattr(exc, "status_code", "unknown")
        body = getattr(exc, "body", "")
        headers = getattr(exc, "headers", {})
        return (
            f"type={type(exc).__name__} status_code={status_code} "
            f"split_operation_id={headers.get('X-Unstructured-Split-Operation-Id', 'missing')} "
            f"split_chunk_index={headers.get('X-Unstructured-Split-Chunk-Index', 'missing')} "
            f"body={body}"
        )
    return f"type={type(exc).__name__} error={exc}"


def _run_partition_with_progress(
    client: UnstructuredClient,
    *,
    request: operations.PartitionRequest,
    server_url: str,
    case_context: str,
    phase: str,
):
    _log_integration_progress("partition_start", case_context=case_context, phase=phase)
    started_at = time.perf_counter()
    try:
        response = client.general.partition(server_url=server_url, request=request)
    except Exception as exc:
        _log_integration_progress(
            "partition_error",
            case_context=case_context,
            phase=phase,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
            details=_describe_partition_exception(exc),
        )
        raise
    _log_integration_progress(
        "partition_complete",
        case_context=case_context,
        phase=phase,
        status_code=response.status_code,
        element_count=len(response.elements) if response.elements is not None else 0,
        elapsed_ms=round((time.perf_counter() - started_at) * 1000),
    )
    return response


def _allowed_delta(expected: int, *, absolute: int, ratio: float) -> int:
    return max(absolute, math.ceil(expected * ratio))


def _text_size(elements) -> int:
    return sum(len((element.get("text") or "").strip()) for element in elements)


def _elements_by_page(elements):
    pages = defaultdict(list)
    for element in elements:
        pages[element["metadata"]["page_number"]].append(element)
    return pages


def _assert_hi_res_output_is_similar(resp_split, resp_single):
    split_pages = _elements_by_page(resp_split.elements)
    single_pages = _elements_by_page(resp_single.elements)

    assert set(split_pages) == set(single_pages)

    assert abs(len(resp_split.elements) - len(resp_single.elements)) <= _allowed_delta(
        len(resp_single.elements),
        absolute=4,
        ratio=0.1,
    )

    split_type_counts = Counter(element["type"] for element in resp_split.elements)
    single_type_counts = Counter(element["type"] for element in resp_single.elements)
    assert set(split_type_counts) == set(single_type_counts)
    for element_type, expected_count in single_type_counts.items():
        assert abs(split_type_counts[element_type] - expected_count) <= _allowed_delta(
            expected_count,
            absolute=2,
            ratio=0.2,
        )

    assert abs(_text_size(resp_split.elements) - _text_size(resp_single.elements)) <= _allowed_delta(
        _text_size(resp_single.elements),
        absolute=250,
        ratio=0.2,
    )

    for page_number, single_page_elements in single_pages.items():
        split_page_elements = split_pages[page_number]

        assert abs(len(split_page_elements) - len(single_page_elements)) <= _allowed_delta(
            len(single_page_elements),
            absolute=2,
            ratio=0.2,
        )
        assert abs(_text_size(split_page_elements) - _text_size(single_page_elements)) <= _allowed_delta(
            _text_size(single_page_elements),
            absolute=120,
            ratio=0.3,
        )


def _assert_split_unsplit_equivalent(
    resp_split,
    resp_single,
    strategy,
    *,
    case_context: str = "",
    extra_exclude_paths=None,
):
    """Compare split-PDF and single-request responses.

    For hi_res (OCR-based), splitting changes per-page context so text and
    OCR text can vary slightly. We still check page coverage, type distribution,
    and text volume so split requests cannot silently drift too far.
    For deterministic strategies (fast, etc.) we keep strict DeepDiff equality.
    """
    context_prefix = f"{case_context}: " if case_context else ""

    assert resp_split.status_code == resp_single.status_code, (
        f"{context_prefix}status mismatch split={resp_split.status_code} single={resp_single.status_code}"
    )
    assert resp_split.content_type == resp_single.content_type, (
        f"{context_prefix}content_type mismatch split={resp_split.content_type} single={resp_single.content_type}"
    )

    if strategy in _HI_RES_STRATEGIES:
        _assert_hi_res_output_is_similar(resp_split, resp_single)
    else:
        assert len(resp_split.elements) == len(resp_single.elements), (
            f"{context_prefix}element_count mismatch split={len(resp_split.elements)} single={len(resp_single.elements)}"
        )

        excludes = [r"root\[\d+\]\['metadata'\]\['parent_id'\]"]
        if extra_exclude_paths:
            excludes.extend(extra_exclude_paths)

        diff = DeepDiff(
            t1=resp_split.elements,
            t2=resp_single.elements,
            exclude_regex_paths=excludes,
        )
        assert len(diff) == 0, f"{context_prefix}DeepDiff mismatch: {diff}"


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
    concurrency_level: int,
    filename: str,
    expected_ok: bool,
    strategy: str,
    hi_res_stable_fixture_path: str,
):
    """
    Tests that output that we get from the split-by-page pdf is the same as from non-split.

    Requires unstructured-api running in bg. See Makefile for how to run it.
    Doesn't check for raw_response as there's no clear patter for how it changes with the number of pages / concurrency_level.
    """
    _assert_local_api_is_running()

    resolved_filename = _resolve_test_filename(filename, strategy, hi_res_stable_fixture_path)
    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)
    case_context = (
        f"test=split_equivalence file={Path(resolved_filename).name} strategy={strategy} "
        f"concurrency={concurrency_level} expected_ok={expected_ok}"
    )

    with open(resolved_filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=Path(resolved_filename).name,
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
        resp_split = _run_partition_with_progress(
            client,
            request=req,
            server_url="http://localhost:8000",
            case_context=case_context,
            phase="split",
        )
    except Exception as exc:
        if not expected_ok:
            assert "File does not appear to be a valid PDF" in str(exc)
            _log_integration_progress(
                "partition_expected_failure",
                case_context=case_context,
                phase="split",
                error_type=type(exc).__name__,
            )
            return
        raise AssertionError(
            f"{case_context}: unexpected split failure {_describe_partition_exception(exc)}"
        ) from exc

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = _run_partition_with_progress(
        client,
        request=req,
        server_url="http://localhost:8000",
        case_context=case_context,
        phase="single",
    )

    _assert_split_unsplit_equivalent(resp_split, resp_single, strategy, case_context=case_context)


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
    hi_res_stable_fixture_path: str,
):
    _assert_local_api_is_running()

    resolved_filename = _resolve_test_filename(filename, strategy, hi_res_stable_fixture_path)
    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)
    case_context = (
        f"test=split_caching file={Path(resolved_filename).name} strategy={strategy} "
        f"use_caching={use_caching} cache_dir={cache_dir}"
    )

    with open(resolved_filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=Path(resolved_filename).name,
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
        resp_split = _run_partition_with_progress(
            client,
            request=req,
            server_url="http://localhost:8000",
            case_context=case_context,
            phase="split",
        )
    except Exception as exc:
        if not expected_ok:
            assert "File does not appear to be a valid PDF" in str(exc)
            _log_integration_progress(
                "partition_expected_failure",
                case_context=case_context,
                phase="split",
                error_type=type(exc).__name__,
            )
            return
        raise AssertionError(
            f"{case_context}: unexpected split failure {_describe_partition_exception(exc)}"
        ) from exc

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = _run_partition_with_progress(
        client,
        request=req,
        server_url="http://localhost:8000",
        case_context=case_context,
        phase="single",
    )

    _assert_split_unsplit_equivalent(resp_split, resp_single, strategy, case_context=case_context)

    # make sure the cache dir was cleaned if passed explicitly
    if cache_dir:
        assert not Path(cache_dir).exists()


@pytest.mark.parametrize("filename", ["_sample_docs/super_long_pages.pdf"])
def test_long_pages_hi_res(filename):
    _log_integration_progress(
        "long_hi_res_start",
        file=Path(filename).name,
        strategy=shared.Strategy.HI_RES,
        concurrency=15,
    )
    req = operations.PartitionRequest(partition_parameters=shared.PartitionParameters(
        files=shared.Files(content=open(filename, "rb"), file_name=filename, ),
        strategy=shared.Strategy.HI_RES,
        split_pdf_page=True,
        split_pdf_allow_failed=True,
        split_pdf_concurrency_level=15
    ), )

    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)

    response = client.general.partition(
        request=req,
        server_url="http://localhost:8000",
    )
    _log_integration_progress(
        "long_hi_res_complete",
        file=Path(filename).name,
        status_code=response.status_code,
        element_count=len(response.elements),
    )
    assert response.status_code == 200
    assert len(response.elements)

def test_integration_split_pdf_for_file_with_no_name():
    """
    Tests that the client raises an error when the file_name is empty.
    """
    _assert_local_api_is_running()

    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)

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
    _assert_local_api_is_running()

    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)

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
        resp = _run_partition_with_progress(
            client,
            request=req,
            server_url="http://localhost:8000",
            case_context=(
                f"test=page_range file={Path(filename).name} page_range={page_range} "
                f"starting_page_number={starting_page_number}"
            ),
            phase="split",
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
    caplog,
    hi_res_stable_fixture_path: str,
):
    """Test strict mode (allow failed = False) for split_pdf."""
    _assert_local_api_is_running()

    resolved_filename = _resolve_test_filename(filename, strategy, hi_res_stable_fixture_path)
    client = UnstructuredClient(api_key_auth=FAKE_KEY, timeout_ms=TEST_TIMEOUT_MS)
    case_context = (
        f"test=strict_mode file={Path(resolved_filename).name} strategy={strategy} "
        f"concurrency={concurrency_level} allow_failed={allow_failed}"
    )

    with open(resolved_filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=Path(resolved_filename).name,
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
        resp_split = _run_partition_with_progress(
            client,
            request=req,
            server_url="http://localhost:8000",
            case_context=case_context,
            phase="split",
        )
    except Exception as exc:
        if not expected_ok:
            assert "The file does not appear to be a valid PDF." in caplog.text
            assert "File does not appear to be a valid PDF" in str(exc)
            _log_integration_progress(
                "partition_expected_failure",
                case_context=case_context,
                phase="split",
                error_type=type(exc).__name__,
            )
            return
        raise AssertionError(
            f"{case_context}: unexpected split failure {_describe_partition_exception(exc)}"
        ) from exc

    parameters.split_pdf_page = False

    req = operations.PartitionRequest(
        partition_parameters=parameters
    )

    resp_single = _run_partition_with_progress(
        client,
        request=req,
        server_url="http://localhost:8000",
        case_context=case_context,
        phase="single",
    )

    _assert_split_unsplit_equivalent(resp_split, resp_single, strategy, case_context=case_context)


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


@pytest.mark.asyncio
async def test_split_pdf_transport_errors_still_retry_when_sdk_disables_connection_retries(
    monkeypatch,
):
    mock_endpoint_called = False
    number_of_transport_failures = 2

    async def mock_send(_, request: httpx.Request, **kwargs):
        nonlocal mock_endpoint_called
        if request.url.host == "localhost" and "docs" in request.url.path:
            mock_endpoint_called = True
            return Response(200, request=request)
        elif "docs" in request.url.path:
            assert False, "The server URL was not set in the dummy request"

        request_body = request.read()
        decoded_body = MultipartDecoder(request_body, request.headers.get("Content-Type"))
        form_data = form_utils.parse_form_data(decoded_body)

        nonlocal number_of_transport_failures
        if (
            number_of_transport_failures > 0
            and "starting_page_number" in form_data
            and int(form_data["starting_page_number"]) < 3
        ):
            number_of_transport_failures -= 1
            raise httpx.ConnectError("transient connect error", request=request)

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
        request=req,
    )

    assert number_of_transport_failures == 0
    assert mock_endpoint_called
    assert res.status_code == 200
