from __future__ import annotations

import asyncio
import io
import logging
import threading
from asyncio import Task
from collections import Counter
from concurrent import futures
from functools import partial
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import requests
from requests_toolbelt import MultipartDecoder

from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.form_utils import (
    FormData,
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
)
from unstructured_client._hooks.custom.split_pdf_hook import (
    DEFAULT_CACHE_TMP_DATA_DIR,
    DEFAULT_CONCURRENCY_LEVEL,
    DEFAULT_STARTING_PAGE_NUMBER,
    MAX_CONCURRENCY_LEVEL,
    MAX_PAGES_PER_SPLIT,
    MIN_PAGES_PER_SPLIT,
    SPLIT_PDF_HEADER_PREFIX,
    SplitPdfHook,
    _get_request_timeout_seconds,
    get_optimal_split_size,
    run_tasks,
)
from unstructured_client._hooks.sdkhooks import SDKHooks
from unstructured_client._hooks.types import AfterErrorContext, AfterSuccessContext, BeforeRequestContext
from unstructured_client.basesdk import BaseSDK
from unstructured_client.models import shared
from unstructured_client.sdkconfiguration import SDKConfiguration
from unstructured_client.types import UNSET
from unstructured_client.utils import BackoffStrategy, RetryConfig


def test_unit_clear_operation():
    """Test clear operation method properly clears request/response data."""
    hook = SplitPdfHook()
    operation_id = "some_id"

    hook.coroutines_to_execute[operation_id] = [MagicMock(), MagicMock()]
    hook.api_successful_responses[operation_id] = [
        requests.Response(),
        requests.Response(),
    ]
    hook.api_failed_responses[operation_id] = [requests.Response()]
    hook.operation_timeouts[operation_id] = 30.0

    assert len(hook.coroutines_to_execute[operation_id]) == 2
    assert len(hook.api_successful_responses[operation_id]) == 2

    hook._clear_operation(operation_id)

    assert hook.coroutines_to_execute.get(operation_id) is None
    assert hook.api_successful_responses.get(operation_id) is None
    assert hook.api_failed_responses.get(operation_id) is None
    assert hook.operation_timeouts.get(operation_id) is None


def test_unit_clear_operation_closes_unconsumed_chunk_files(tmp_path: Path):
    hook = SplitPdfHook()
    operation_id = "cache-mode-clear"
    chunk_path = tmp_path / "chunk.pdf"
    chunk_path.write_bytes(b"%PDF")
    chunk_file = open(chunk_path, mode="rb")  # pylint: disable=consider-using-with
    tempdir = MagicMock()

    hook.coroutines_to_execute[operation_id] = [
        partial(hook.call_api_partial, pdf_chunk_file=chunk_file),
    ]
    hook.tempdirs[operation_id] = tempdir

    hook._clear_operation(operation_id)

    assert chunk_file.closed
    tempdir.cleanup.assert_called_once()


def test_unit_get_request_timeout_seconds_uses_request_timeout_extension():
    request = httpx.Request(
        "POST",
        "http://localhost",
        extensions={"timeout": {"connect": 10.0, "read": 30.0, "write": 20.0, "pool": 5.0}},
    )

    assert _get_request_timeout_seconds(request) == 30.0


def test_unit_prepare_request_headers():
    """Test prepare request headers method properly removes Content-Type and Content-Length headers."""
    test_headers = {
        "Content-Type": "application/json",
        "Content-Length": "100",
        "Authorization": "Bearer token",
    }
    expected_headers = {
        "Authorization": "Bearer token",
    }

    headers = request_utils.prepare_request_headers(test_headers)

    assert headers != test_headers
    assert dict(headers) == expected_headers


def test_unit_create_response():
    """Test create response method properly overrides body elements and Content-Length header."""
    test_elements = [{"key": "value"}, {"key_2": "value"}]

    expected_status_code = 200
    expected_content = b'[{"key": "value"}, {"key_2": "value"}]'
    expected_content_length = "38"

    response = request_utils.create_response(test_elements)

    assert response.status_code == expected_status_code
    assert response._content == expected_content
    assert response.headers.get("Content-Length") == expected_content_length


def test_unit_decode_content_disposition():
    """Test decode content disposition method properly decodes Content-Disposition header."""

    # Test case 1: Single parameter
    content_disposition = b'attachment; filename="test_file.pdf"'
    expected_result = {"filename": "test_file.pdf"}
    result = form_utils.decode_content_disposition(content_disposition)
    assert result == expected_result

    # Test case 2: Multiple parameters
    content_disposition = b'attachment; filename="test_file.pdf"; size=100; version="1.0"'
    expected_result = {"filename": "test_file.pdf", "size": "100", "version": "1.0"}
    result = form_utils.decode_content_disposition(content_disposition)
    assert result == expected_result

    # Test case 3: No parameters
    content_disposition = b"attachment"
    expected_result = {}
    result = form_utils.decode_content_disposition(content_disposition)
    assert result == expected_result


def test_unit_parse_form_data():
    """Test parse form data method properly parses the form data and returns dictionary.
    Parameters with the same key should be consolidated to a list."""

    # Prepare test data
    test_form_data = (
        b"--boundary\r\n"
        b"Content-Disposition: form-data; name=\"files\"; filename=\"test_file.pdf\"\r\n"
        b"\r\n"
        b"file_content\r\n"
        b"--boundary\r\n"
        b"Content-Disposition: form-data; name=\"parameter_1\"\r\n"
        b"\r\n"
        b"value_1\r\n"
        b"--boundary\r\n"
        b"Content-Disposition: form-data; name=\"parameter_2\"\r\n"
        b"\r\n"
        b"value_2\r\n"
        b"--boundary\r\n"
        b"Content-Disposition: form-data; name=\"list_parameter\"\r\n"
        b"\r\n"
        b"value_1\r\n"
        b"--boundary\r\n"
        b"Content-Disposition: form-data; name=\"list_parameter\"\r\n"
        b"\r\n"
        b"value_2\r\n"
        b"--boundary--\r\n"
    )

    decoded_data = MultipartDecoder(
        test_form_data,
        "multipart/form-data; boundary=boundary",
    )

    # Expected results
    expected_form_data = {
        "files": shared.Files(content=b"file_content", file_name="test_file.pdf"),
        "parameter_1": "value_1",
        "parameter_2": "value_2",
        "list_parameter": ["value_1", "value_2"],
    }

    # Parse form data
    form_data = form_utils.parse_form_data(decoded_data)

    # Assert the parsed form data
    assert form_data.get("parameter_1") == expected_form_data.get("parameter_1")
    assert form_data.get("parameter_2") == expected_form_data.get("parameter_2")
    assert form_data.get("list_parameter") == expected_form_data.get("list_parameter")
    assert form_data.get("files").file_name == expected_form_data.get("files").file_name

    assert form_data.get("files").content == expected_form_data.get("files").content


def test_unit_parse_form_data_error():
    """Test parse form data method raises RuntimeError when the form data is invalid (no Content-Disposition header)."""

    # Prepare test data
    decoded_data = MultipartDecoder(
        b'--boundary\r\nContent: form-data; name="files"; filename="test_file.pdf"\r\n\r\nfile_content\r\n--boundary--\r\n',
        "multipart/form-data; boundary=boundary",
    )

    # Assert RuntimeError
    with pytest.raises(RuntimeError):
        form_utils.parse_form_data(decoded_data)


def test_unit_parse_form_data_empty_filename_error():
    """Test parse form data method raises ValueError when the form data has empty filename."""

    # Prepare test data
    decoded_data = MultipartDecoder(
        b'--boundary\r\nContent-Disposition: form-data; name="files"; filename=""\r\n\r\nfile_content\r\n--boundary--\r\n',
        "multipart/form-data; boundary=boundary",
    )

    with pytest.raises(ValueError):
        form_utils.parse_form_data(decoded_data)


def test_unit_parse_form_data_none_filename_error():
    """Test parse form data method raises ValueError when the form data has no filename (None)."""

    # Prepare test data
    decoded_data = MultipartDecoder(
        b'--boundary\r\nContent-Disposition: form-data; name="files"\r\n\r\nfile_content\r\n--boundary--\r\n',
        "multipart/form-data; boundary=boundary",
    )

    with pytest.raises(ValueError):
        form_utils.parse_form_data(decoded_data)


def test_unit_is_pdf_valid_pdf_when_passing_file_object():
    """Test is pdf method returns pdf object for valid pdf file with filename."""
    filename = "_sample_docs/layout-parser-paper-fast.pdf"

    with open(filename, "rb") as f:
        result = pdf_utils.read_pdf(f)

    assert result is not None


def test_unit_is_pdf_valid_pdf_when_passing_binary_content():
    """Test is pdf method returns pdf object for file with valid pdf content"""
    filename = "_sample_docs/layout-parser-paper-fast.pdf"
    
    with open(filename, "rb") as f:
        result = pdf_utils.read_pdf(f.read())

    assert result is not None


def test_unit_is_pdf_invalid_pdf():
    """Test is pdf method returns False for file with invalid extension."""
    result = pdf_utils.read_pdf(b"txt_content")

    assert result is None
    

def test_unit_get_starting_page_number_missing_key():
    """Test _get_starting_page_number method with missing key."""
    form_data = {}

    result = form_utils.get_starting_page_number(
        form_data,
        key=PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
        fallback_value=DEFAULT_STARTING_PAGE_NUMBER,
    )

    assert result == 1


@pytest.mark.parametrize(
    ("num_pages", "concurrency_level", "expected_split_size"),
    [
        (5, 3, 2),  # "1st worker gets 2 pages, 2nd worker gets 2 pages, 3rd worker gets 1 page"
        (100, 3, MAX_PAGES_PER_SPLIT),  # large PDF, each worker gets 20 pages
        (1, 5, MIN_PAGES_PER_SPLIT),  # small PDF, one worker with MIN_PAGES_PER_WORKER size
        (60, 4, 15),  # exact multiple of no. workers
        (3, 10, MIN_PAGES_PER_SPLIT),  # more workers than pages
    ],
)
def test_get_optimal_split_size(num_pages, concurrency_level, expected_split_size):
    split_size = get_optimal_split_size(num_pages, concurrency_level)
    assert split_size == expected_split_size


@pytest.mark.parametrize(
    ("form_data", "expected_result"),
    [
        ({}, DEFAULT_CONCURRENCY_LEVEL),  # no value
        ({"split_pdf_concurrency_level": "10"}, 10),  # valid number
        (
                # exceeds max value
                {"split_pdf_concurrency_level": f"{MAX_CONCURRENCY_LEVEL + 1}"},
                MAX_CONCURRENCY_LEVEL,
        ),
        ({"split_pdf_concurrency_level": "-3"}, DEFAULT_CONCURRENCY_LEVEL),  # negative value
    ],
)
def test_unit_get_split_pdf_concurrency_level_returns_valid_number(form_data, expected_result):
    assert (
            form_utils.get_split_pdf_concurrency_level_param(
                form_data,
                key=PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
                fallback_value=DEFAULT_CONCURRENCY_LEVEL,
                max_allowed=MAX_CONCURRENCY_LEVEL,
            )
            == expected_result
    )


@pytest.mark.parametrize(
    "starting_page_number, expected_result",
    [
        ("5", 5),  # Valid integer
        ("abc", 1),  # Invalid integer
        ("0", 1),  # Value less than 1
        ("", 1),  # Empty string
        (None, 1),  # None value
    ],
)
def test_unit_get_starting_page_number(starting_page_number, expected_result):
    """Test _get_starting_page_number method with different inputs."""
    form_data = {"starting_page_number": starting_page_number}
    result = form_utils.get_starting_page_number(
        form_data,
        key=PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
        fallback_value=DEFAULT_STARTING_PAGE_NUMBER,
    )
    assert result == expected_result


@pytest.mark.parametrize(
    "page_range, expected_result",
    [
        (["1", "14"], (1, 14)),  # Valid range, start on boundary
        (["4", "16"], (4, 16)),  # Valid range, end on boundary
        (None, (1, 20)),  # Range not specified, defaults to full range
        (["2", "5"], (2, 5)),  # Valid range within boundary
        (["2", "100"], None),  # End page too high
        (["50", "100"], None),  # Range too high
        (["-50", "5"], None),  # Start page too low
        (["-50", "-2"], None),  # Range too low
        (["10", "2"], None),  # Backwards range
        (["foo", "foo"], None),  # Parse error
    ],
)
def test_unit_get_page_range_returns_valid_range(page_range, expected_result):
    """Test get_page_range method with different inputs.
    Ranges that are out of bounds for a 20 page doc will throw a ValueError."""
    form_data = {"split_pdf_page_range[]": page_range}
    try:
        result = form_utils.get_page_range(
            form_data,
            key=PARTITION_FORM_PAGE_RANGE_KEY,
            max_pages=20,
        )
    except ValueError as exc:
        assert not expected_result
        assert "is out of bounds." in str(exc) or "is not a valid page range." in str(exc)
        return

    assert result == expected_result


async def _request_mock(
        async_client: httpx.AsyncClient, # not used by mock
        limiter: asyncio.Semaphore, # not used by mock
        fails: bool,
        content: str) -> requests.Response:
    response = requests.Response()
    response.status_code = 500 if fails else 200
    response._content = content.encode()
    return response


@pytest.mark.parametrize(
    ("allow_failed", "tasks", "expected_responses"), [
        pytest.param(
            True, [
                partial(_request_mock, fails=False, content="1"),
                partial(_request_mock,  fails=False, content="2"),
                partial(_request_mock,  fails=False, content="3"),
                partial(_request_mock,  fails=False, content="4"),
            ],
            ["1", "2", "3", "4"],
            id="no failures, fails allower"
        ),
        pytest.param(
            True, [
                partial(_request_mock,  fails=False, content="1"),
                partial(_request_mock,  fails=True, content="2"),
                partial(_request_mock,  fails=False, content="3"),
                partial(_request_mock,  fails=True, content="4"),
            ],
            ["1", "2", "3", "4"],
            id="failures, fails allowed"
        ),
        pytest.param(
            False, [
                partial(_request_mock,  fails=True, content="failure"),
                partial(_request_mock,  fails=False, content="2"),
                partial(_request_mock,  fails=True, content="failure"),
                partial(_request_mock,  fails=False, content="4"),
            ],
            ["failure"],
            id="failures, fails disallowed"
        ),
        pytest.param(
            False, [
                partial(_request_mock,  fails=False, content="1"),
                partial(_request_mock,  fails=False, content="2"),
                partial(_request_mock,  fails=False, content="3"),
                partial(_request_mock,  fails=False, content="4"),
            ],
            ["1", "2", "3", "4"],
            id="no failures, fails disallowed"
        ),
    ]
)
@pytest.mark.asyncio
async def test_unit_disallow_failed_coroutines(
        allow_failed: bool,
        tasks: list[Task],
        expected_responses: list[str],
):
    """Test disallow failed coroutines method properly sets the flag to False."""
    responses = await run_tasks(tasks, allow_failed=allow_failed)
    response_contents = [response[1].content.decode() for response in responses]
    assert response_contents == expected_responses


async def _fetch_canceller_error(
        async_client: httpx.AsyncClient, # not used by mock
        limiter: asyncio.Semaphore, # not used by mock
        fails: bool,
        content: str,
        cancelled_counter: Counter):
    try:
        if not fails:
            await asyncio.sleep(0.01)
            print("Doesn't fail")
        else:
            print("Fails")
        return await _request_mock(async_client=async_client, limiter=limiter, fails=fails, content=content)
    except asyncio.CancelledError:
        cancelled_counter.update(["cancelled"])
        print(cancelled_counter["cancelled"])
        print("Cancelled")


@pytest.mark.asyncio
async def test_remaining_tasks_cancelled_when_fails_disallowed():
    cancelled_counter = Counter()
    tasks = [
        partial(_fetch_canceller_error, fails=True, content="1", cancelled_counter=cancelled_counter),
        *[partial(_fetch_canceller_error, fails=False, content=f"{i}", cancelled_counter=cancelled_counter)
          for i in range(2, 200)],
    ]

    await run_tasks(tasks, allow_failed=False)
    # give some time to actually cancel the tasks in background
    await asyncio.sleep(1)
    print("Cancelled amount: ", cancelled_counter["cancelled"])
    assert len(tasks) > cancelled_counter["cancelled"] > 0


@patch("unstructured_client._hooks.custom.form_utils.Path")
def test_unit_get_split_pdf_cache_tmp_data_dir_uses_dir_from_form_data(mock_path: MagicMock):
    """Test get_split_pdf_cache_tmp_data_dir uses the directory from the form data."""
    # -- Create the form_data
    dir_key = form_utils.PARTITION_FORM_SPLIT_CACHE_TMP_DATA_DIR_KEY # -- "split_pdf_cache_tmp_data_dir"
    mock_dir = "/mock/dir"
    form_data: FormData = {dir_key: mock_dir}  

    # -- Mock the Path object in form_utils
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.exists.return_value = True
    mock_path_instance.resolve.return_value = Path(mock_dir)

    result = form_utils.get_split_pdf_cache_tmp_data_dir(
        form_data = form_data,
        key=dir_key,
        fallback_value=DEFAULT_CACHE_TMP_DATA_DIR  # -- tempfile.gettempdir()
    )
    
    assert dir_key == "split_pdf_cache_tmp_data_dir"
    assert form_data.get(dir_key) == "/mock/dir"
    mock_path.assert_called_once_with(mock_dir)
    mock_path_instance.exists.assert_called_once()
    assert result == str(Path(mock_dir).resolve())


def test_before_request_raises_pdf_validation_error_when_pdf_check_fails():
    """Test that before_request raises PDFValidationError when pdf_utils.check_pdf throws PDFValidationError."""
    hook = SplitPdfHook()
    
    # Initialize the hook with a mock client
    mock_client = MagicMock()
    hook.sdk_init(base_url="http://localhost:8888", client=mock_client)
    
    # Create a mock request context
    mock_hook_ctx = MagicMock()
    mock_hook_ctx.operation_id = "partition"
    
    # Create a mock request with proper headers and content
    mock_request = MagicMock()
    mock_request.headers = {"Content-Type": "multipart/form-data"}
    mock_request.url.host = "localhost"
    
    # Mock the form data to include the necessary fields for PDF splitting
    mock_pdf_file = MagicMock()
    mock_pdf_file.read.return_value = b"mock_pdf_content"
    
    mock_form_data = {
        "split_pdf_page": "true",
        "files": {
            "filename": "test.pdf",
            "content_type": "application/pdf",
            "file": mock_pdf_file
        }
    }
    
    # Mock the PDF reader object
    mock_pdf_reader = MagicMock()
    
    # Define the error message that will be raised
    error_message = "File does not appear to be a valid PDF."
    
    with patch("unstructured_client._hooks.custom.request_utils.get_multipart_stream_fields") as mock_get_fields, \
         patch("unstructured_client._hooks.custom.pdf_utils.read_pdf") as mock_read_pdf, \
         patch("unstructured_client._hooks.custom.pdf_utils.check_pdf") as mock_check_pdf, \
         patch("unstructured_client._hooks.custom.request_utils.get_base_url") as mock_get_base_url:
        
        # Set up the mocks
        mock_get_fields.return_value = mock_form_data
        mock_read_pdf.return_value = mock_pdf_reader
        mock_check_pdf.side_effect = pdf_utils.PDFValidationError(error_message)
        mock_get_base_url.return_value = "http://localhost:8888"
        
        # Call the method under test and verify it raises PDFValidationError
        with pytest.raises(pdf_utils.PDFValidationError) as exc_info:
            hook.before_request(mock_hook_ctx, mock_request)
        
        # Verify the exception has the correct message
        assert str(exc_info.value) == error_message
        
        # Verify that the mocked functions were called as expected
        mock_get_fields.assert_called_once_with(mock_request)
        mock_read_pdf.assert_called_once_with(mock_pdf_file)
        mock_check_pdf.assert_called_once_with(mock_pdf_reader)


_MISSING = object()


def _httpx_response(content: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=content.encode(),
        request=httpx.Request("POST", "http://localhost:8888/general/v0/general"),
    )


def _httpx_json_response(payload: list[dict], status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("POST", "http://localhost:8888/general/v0/general"),
    )


async def _transport_error_request(
    async_client: httpx.AsyncClient,  # pragma: no cover - signature compatibility
    limiter: asyncio.Semaphore,  # pragma: no cover - signature compatibility
    error_cls: type[httpx.TransportError],
    request_id: str,
):
    raise error_cls(
        f"transport failure for {request_id}",
        request=httpx.Request("POST", f"http://localhost:8888/chunk/{request_id}"),
    )


async def _slow_success_request(
    async_client: httpx.AsyncClient,  # pragma: no cover - signature compatibility
    limiter: asyncio.Semaphore,  # pragma: no cover - signature compatibility
    content: str,
) -> httpx.Response:
    await asyncio.sleep(0.05)
    return _httpx_response(content)


async def _cancelled_request(
    async_client: httpx.AsyncClient,  # pragma: no cover - signature compatibility
    limiter: asyncio.Semaphore,  # pragma: no cover - signature compatibility
) -> httpx.Response:
    raise asyncio.CancelledError()


def _make_hook_with_split_request(
    hook: SplitPdfHook | None = None,
    *,
    timeout_extension: object = _MISSING,
    config_timeout_ms: int | None = 12_000,
    retry_config: RetryConfig | object = UNSET,
    allow_failed: str | None = None,
    cache_tmp_data: str | None = None,
    pdf_chunks: list[tuple[io.BytesIO, int]] | None = None,
):
    """Helper: run before_request with mocked PDF parsing so it returns a dummy request."""
    hook = hook or SplitPdfHook()
    if hook.client is None:
        hook.sdk_init(base_url="http://localhost:8888", client=httpx.Client())

    hook_ctx = MagicMock(spec=BeforeRequestContext)
    hook_ctx.operation_id = "partition"
    hook_ctx.config = MagicMock()
    hook_ctx.config.timeout_ms = config_timeout_ms
    hook_ctx.config.retry_config = retry_config

    request_extensions: dict[str, object] = {}
    if timeout_extension is not _MISSING and timeout_extension is not None:
        request_extensions["timeout"] = timeout_extension
    elif config_timeout_ms is not None:
        timeout_seconds = config_timeout_ms / 1000
        request_extensions["timeout"] = {
            "connect": timeout_seconds,
            "read": timeout_seconds,
            "write": timeout_seconds,
            "pool": timeout_seconds,
        }

    request = httpx.Request(
        "POST",
        "http://localhost:8888/general/v0/general",
        headers={"Content-Type": "multipart/form-data"},
        extensions=request_extensions,
    )

    mock_pdf_file = MagicMock()
    form_data = {
        "split_pdf_page": "true",
        "strategy": "fast",
        "files": {
            "filename": "test.pdf",
            "content_type": "application/pdf",
            "file": mock_pdf_file,
        },
    }
    if allow_failed is not None:
        form_data["split_pdf_allow_failed"] = allow_failed
    if cache_tmp_data is not None:
        form_data["split_pdf_cache_tmp_data"] = cache_tmp_data

    mock_pdf_reader = MagicMock()
    mock_pdf_reader.get_num_pages.return_value = 100
    mock_pdf_reader.pages = [MagicMock()] * 100
    mock_pdf_reader.stream = io.BytesIO(b"fake-pdf-bytes")

    with patch("unstructured_client._hooks.custom.request_utils.get_multipart_stream_fields") as mock_get_fields, \
         patch("unstructured_client._hooks.custom.pdf_utils.read_pdf") as mock_read_pdf, \
         patch("unstructured_client._hooks.custom.pdf_utils.check_pdf") as mock_check_pdf, \
         patch("unstructured_client._hooks.custom.request_utils.get_base_url") as mock_get_base_url, \
         patch.object(hook, "_trim_large_pages", side_effect=lambda pdf, fd: pdf), \
         patch.object(hook, "_get_pdf_chunk_paths", return_value=[]), \
         patch.object(hook, "_get_pdf_chunks_in_memory", return_value=pdf_chunks or []):
        mock_get_fields.return_value = form_data
        mock_read_pdf.return_value = mock_pdf_reader
        mock_check_pdf.return_value = mock_pdf_reader
        mock_get_base_url.return_value = "http://localhost:8888"

        result = hook.before_request(hook_ctx, request)

    return hook, hook_ctx, result


def _make_sdk_hook_context():
    hook_ctx = MagicMock()
    hook_ctx.config = MagicMock()
    hook_ctx.base_url = "http://localhost:8888"
    hook_ctx.operation_id = "partition"
    hook_ctx.oauth2_scopes = None
    hook_ctx.security_source = None
    return hook_ctx


class _BlockingAsyncClient:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def send(self, request: httpx.Request, stream=False) -> httpx.Response:
        del stream
        self.started.set()
        await asyncio.Event().wait()
        return httpx.Response(status_code=200, request=request)


@pytest.mark.asyncio
async def test_unit_do_request_async_cancellation_after_before_request_cleans_split_state():
    operation_id = "cancelled-operation"
    split_hook = SplitPdfHook()
    split_hook.coroutines_to_execute[operation_id] = [MagicMock()]
    split_hook.pending_operation_ids[operation_id] = operation_id
    tempdir = MagicMock()
    split_hook.tempdirs[operation_id] = tempdir

    def _prepared_split_request(hook_ctx, request):
        del hook_ctx, request
        return httpx.Request(
            "GET",
            "http://localhost:8888/general/docs",
            headers={"operation_id": operation_id},
            extensions={"split_pdf_operation_id": operation_id},
        )

    split_hook.before_request = _prepared_split_request  # type: ignore[method-assign]
    hooks = SDKHooks()
    hooks.before_request_hooks = [split_hook]
    hooks.after_error_hooks = [split_hook]
    hooks.after_success_hooks = [split_hook]

    client = _BlockingAsyncClient()
    config = SDKConfiguration(
        client=None,
        client_supplied=False,
        async_client=client,  # type: ignore[arg-type]
        async_client_supplied=True,
        debug_logger=logging.getLogger("test"),
    )
    config.__dict__["_hooks"] = hooks
    sdk = BaseSDK(config)
    task = asyncio.create_task(
        sdk.do_request_async(
            _make_sdk_hook_context(),
            httpx.Request("POST", "http://localhost:8888/general/v0/general"),
            error_status_codes=[],
        )
    )

    await client.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert operation_id not in split_hook.coroutines_to_execute
    assert operation_id not in split_hook.pending_operation_ids
    assert operation_id not in split_hook.tempdirs
    tempdir.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_unit_do_request_async_cancellation_logs_cancelled_cleanup(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.DEBUG, logger="test")
    operation_id = "cancelled-cleanup"

    class PreparedRequestHook:
        def before_request(self, hook_ctx, request):
            del hook_ctx, request
            return httpx.Request(
                "GET",
                "http://localhost:8888/general/docs",
                headers={"operation_id": operation_id},
                extensions={"split_pdf_operation_id": operation_id},
            )

    class CancelledCleanupHook:
        async def after_error_async(self, hook_ctx, response, error):
            del hook_ctx, response, error
            raise asyncio.CancelledError()

        def after_error(self, hook_ctx, response, error):  # pragma: no cover - dispatch guard
            raise AssertionError("async hook should be awaited")

    hooks = SDKHooks()
    hooks.before_request_hooks = [PreparedRequestHook()]  # type: ignore[list-item]
    hooks.after_error_hooks = [CancelledCleanupHook()]  # type: ignore[list-item]

    client = _BlockingAsyncClient()
    config = SDKConfiguration(
        client=None,
        client_supplied=False,
        async_client=client,  # type: ignore[arg-type]
        async_client_supplied=True,
        debug_logger=logging.getLogger("test"),
    )
    config.__dict__["_hooks"] = hooks
    sdk = BaseSDK(config)
    task = asyncio.create_task(
        sdk.do_request_async(
            _make_sdk_hook_context(),
            httpx.Request("POST", "http://localhost:8888/general/v0/general"),
            error_status_codes=[],
        )
    )

    await client.started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert "Cancellation cleanup cancelled" in caplog.text


def test_before_request_returns_dummy_with_timeout_and_operation_id():
    hook, mock_hook_ctx, result = _make_hook_with_split_request()
    operation_id = result.headers["operation_id"]

    assert isinstance(result, httpx.Request)
    assert str(result.url) == "http://localhost:8888/general/docs"
    assert operation_id
    assert result.extensions["timeout"]["read"] == 12.0
    assert result.extensions["split_pdf_operation_id"] == operation_id
    assert operation_id in hook.pending_operation_ids


def test_before_request_logs_split_plan(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="unstructured-client")

    _, _, result = _make_hook_with_split_request(
        allow_failed="true",
        pdf_chunks=[(io.BytesIO(b"chunk-1"), 0), (io.BytesIO(b"chunk-2"), 2)],
    )

    operation_id = result.headers["operation_id"]
    assert f"event=plan_created operation_id={operation_id}" in caplog.text
    assert "chunk_count=2" in caplog.text
    assert "allow_failed=True" in caplog.text
    assert "cache_mode=disabled" in caplog.text


def test_after_error_cleans_up_split_state():
    """If the dummy request fails, after_error must release all per-operation state."""
    hook, mock_hook_ctx, result = _make_hook_with_split_request()
    operation_id = result.headers["operation_id"]

    assert operation_id not in hook.executors
    assert operation_id in hook.coroutines_to_execute

    error_ctx = MagicMock(spec=AfterErrorContext)
    error_ctx.operation_id = mock_hook_ctx.operation_id

    hook.after_error(error_ctx, None, httpx.ConnectError("DNS failed", request=result))

    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.operation_timeouts
    assert operation_id not in hook.pending_operation_ids


@pytest.mark.parametrize(
    ("extensions", "expected_timeout"),
    [
        ({}, None),
        ({"timeout": 42.0}, 42.0),
    ],
)
def test_unit_get_request_timeout_seconds_edge_cases(extensions, expected_timeout):
    request = httpx.Request("POST", "http://localhost", extensions=extensions)
    assert _get_request_timeout_seconds(request) == expected_timeout


@pytest.mark.asyncio
async def test_unit_run_tasks_allow_failed_transport_exception():
    tasks = [
        partial(_slow_success_request, content="1"),
        partial(_transport_error_request, error_cls=httpx.ReadError, request_id="2"),
        partial(_slow_success_request, content="3"),
    ]

    responses = await run_tasks(tasks, allow_failed=True)

    assert [response.status_code for _, response in responses] == [200, 500, 200]
    assert responses[1][1].extensions["transport_exception"].__class__ is httpx.ReadError


@pytest.mark.asyncio
async def test_unit_run_tasks_allow_failed_cancelled_error_becomes_failed_response():
    tasks = [
        partial(_slow_success_request, content="1"),
        partial(_cancelled_request),
        partial(_slow_success_request, content="3"),
    ]

    responses = await run_tasks(tasks, allow_failed=True)

    assert [response.status_code for _, response in responses] == [200, 500, 200]
    assert isinstance(responses[1][1].extensions["transport_exception"], asyncio.CancelledError)


@pytest.mark.asyncio
async def test_unit_run_tasks_caller_cancelled_logs_pending_task_count(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.WARNING, logger="unstructured-client")

    async def _wait_forever(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        del async_client, limiter
        await asyncio.Event().wait()
        return _httpx_response("unreachable")

    tasks = [partial(_wait_forever), partial(_wait_forever), partial(_wait_forever)]
    run_task = asyncio.create_task(
        run_tasks(tasks, allow_failed=False, operation_id="caller-cancelled")
    )
    await asyncio.sleep(0)

    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert "event=batch_cancel_remaining operation_id=caller-cancelled" in caplog.text
    assert "remaining_tasks=3" in caplog.text


@pytest.mark.asyncio
async def test_unit_run_tasks_disallow_failed_transport_exception_cancels_remaining():
    cancelled_counter = Counter()

    async def _raises_transport_error(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connect failed",
            request=httpx.Request("POST", "http://localhost:8888/chunk/failure"),
        )

    async def _cancelled_task(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
        content: str,
        cancelled_counter: Counter,
    ) -> httpx.Response:
        try:
            await asyncio.sleep(0.5)
            return _httpx_response(content)
        except asyncio.CancelledError:
            cancelled_counter.update(["cancelled"])
            raise

    tasks = [
        partial(_raises_transport_error),
        *[
            partial(_cancelled_task, content=f"{index}", cancelled_counter=cancelled_counter)
            for index in range(2, 20)
        ],
    ]

    with pytest.raises(httpx.ConnectError):
        await run_tasks(tasks, allow_failed=False)

    await asyncio.sleep(0)
    assert cancelled_counter["cancelled"] > 0


def test_unit_concurrent_operations_use_independent_state():
    hook = SplitPdfHook()
    hook.sdk_init(base_url="http://localhost:8888", client=httpx.Client())

    hook, _, first_result = _make_hook_with_split_request(
        hook=hook,
        allow_failed="true",
        cache_tmp_data="true",
    )
    hook, _, second_result = _make_hook_with_split_request(
        hook=hook,
        allow_failed="false",
        cache_tmp_data="false",
    )

    first_operation_id = first_result.headers["operation_id"]
    second_operation_id = second_result.headers["operation_id"]

    assert first_operation_id != second_operation_id
    assert hook.allow_failed[first_operation_id] is True
    assert hook.allow_failed[second_operation_id] is False
    assert hook.cache_tmp_data_feature[first_operation_id] is True
    assert hook.cache_tmp_data_feature[second_operation_id] is False


def test_unit_after_error_cleans_only_matching_operation_on_transport_failure():
    hook = SplitPdfHook()
    hook.sdk_init(base_url="http://localhost:8888", client=httpx.Client())

    hook, _, first_result = _make_hook_with_split_request(hook=hook, allow_failed="true")
    hook, _, second_result = _make_hook_with_split_request(hook=hook, allow_failed="false")

    first_operation_id = first_result.headers["operation_id"]
    second_operation_id = second_result.headers["operation_id"]

    error_ctx = MagicMock(spec=AfterErrorContext)
    error_ctx.operation_id = "partition"

    hook.after_error(
        error_ctx,
        None,
        httpx.ConnectError("DNS failed", request=first_result),
    )

    assert first_operation_id not in hook.executors
    assert first_operation_id not in hook.coroutines_to_execute
    assert first_operation_id not in hook.pending_operation_ids
    assert second_operation_id not in hook.executors
    assert second_operation_id in hook.coroutines_to_execute
    assert second_operation_id in hook.pending_operation_ids


@pytest.mark.asyncio
async def test_unit_sdk_hooks_after_success_async_uses_optional_async_hook():
    calls: list[str] = []

    class AsyncHook:
        async def after_success_async(self, hook_ctx, response):
            calls.append("async")
            response.headers["X-Async-Hook"] = "called"
            return response

    class SyncHook:
        def after_success(self, hook_ctx, response):
            calls.append("sync")
            response.headers["X-Sync-Hook"] = "called"
            return response

    hooks = SDKHooks()
    hooks.after_success_hooks = [AsyncHook(), SyncHook()]  # type: ignore[list-item]
    response = httpx.Response(status_code=200)

    returned_response = await hooks.after_success_async(MagicMock(spec=AfterSuccessContext), response)

    assert returned_response is response
    assert calls == ["async", "sync"]
    assert response.headers["X-Async-Hook"] == "called"
    assert response.headers["X-Sync-Hook"] == "called"


@pytest.mark.asyncio
async def test_unit_sdk_hooks_after_success_async_ignores_sync_method_with_async_name():
    calls: list[str] = []

    class SyncHook:
        def after_success_async(self, hook_ctx, response):
            calls.append("non-awaitable")
            return response

        def after_success(self, hook_ctx, response):
            calls.append("sync")
            response.headers["X-Sync-Hook"] = "called"
            return response

    hooks = SDKHooks()
    hooks.after_success_hooks = [SyncHook()]  # type: ignore[list-item]
    response = httpx.Response(status_code=200)

    returned_response = await hooks.after_success_async(MagicMock(spec=AfterSuccessContext), response)

    assert returned_response is response
    assert calls == ["sync"]
    assert response.headers["X-Sync-Hook"] == "called"


@pytest.mark.asyncio
async def test_unit_sdk_hooks_after_error_async_uses_optional_async_hook():
    calls: list[str] = []

    class AsyncHook:
        async def after_error_async(self, hook_ctx, response, error):
            calls.append("async")
            response.headers["X-Async-Error-Hook"] = "called"
            return response, error

    class SyncHook:
        def after_error(self, hook_ctx, response, error):
            calls.append("sync")
            response.headers["X-Sync-Error-Hook"] = "called"
            return response, error

    hooks = SDKHooks()
    hooks.after_error_hooks = [AsyncHook(), SyncHook()]  # type: ignore[list-item]
    response = httpx.Response(status_code=500)

    returned_response, returned_error = await hooks.after_error_async(
        MagicMock(spec=AfterErrorContext),
        response,
        None,
    )

    assert returned_response is response
    assert returned_error is None
    assert calls == ["async", "sync"]
    assert response.headers["X-Async-Error-Hook"] == "called"
    assert response.headers["X-Sync-Error-Hook"] == "called"


@pytest.mark.asyncio
async def test_unit_sdk_hooks_before_request_async_runs_sync_hooks_off_loop():
    loop_thread_id = threading.get_ident()
    hook_thread_id = None

    class SyncHook:
        def before_request(self, hook_ctx, request):
            nonlocal hook_thread_id
            hook_thread_id = threading.get_ident()
            request.headers["X-Sync-Before-Hook"] = "called"
            return request

    hooks = SDKHooks()
    hooks.before_request_hooks = [SyncHook()]  # type: ignore[list-item]
    request = httpx.Request("GET", "http://localhost")

    returned_request = await hooks.before_request_async(
        MagicMock(spec=BeforeRequestContext),
        request,
    )

    assert returned_request is request
    assert request.headers["X-Sync-Before-Hook"] == "called"
    assert hook_thread_id != loop_thread_id


@pytest.mark.asyncio
async def test_unit_sdk_hooks_before_request_async_serializes_same_sync_hook_instance():
    release_hooks = threading.Event()
    first_hook_started = threading.Event()
    active_lock = threading.Lock()
    active_hooks = 0
    max_active_hooks = 0

    class SyncHook:
        def before_request(self, hook_ctx, request):
            nonlocal active_hooks, max_active_hooks
            del hook_ctx
            with active_lock:
                active_hooks += 1
                max_active_hooks = max(max_active_hooks, active_hooks)
                if active_hooks == 1:
                    first_hook_started.set()
            try:
                release_hooks.wait(timeout=1)
                request.headers["X-Sync-Before-Hook"] = "called"
                return request
            finally:
                with active_lock:
                    active_hooks -= 1

    hooks = SDKHooks()
    hooks.before_request_hooks = [SyncHook()]  # type: ignore[list-item]
    hook_ctx = MagicMock(spec=BeforeRequestContext)
    first_request = httpx.Request("GET", "http://localhost/first")
    second_request = httpx.Request("GET", "http://localhost/second")

    first_task = asyncio.create_task(hooks.before_request_async(hook_ctx, first_request))
    await asyncio.to_thread(first_hook_started.wait, 1)
    second_task = asyncio.create_task(hooks.before_request_async(hook_ctx, second_request))
    await asyncio.sleep(0.01)
    assert max_active_hooks == 1
    release_hooks.set()

    returned_first, returned_second = await asyncio.gather(first_task, second_task)

    assert returned_first is first_request
    assert returned_second is second_request
    assert first_request.headers["X-Sync-Before-Hook"] == "called"
    assert second_request.headers["X-Sync-Before-Hook"] == "called"
    assert max_active_hooks == 1


@pytest.mark.asyncio
async def test_unit_split_pdf_before_request_async_serializes_setup():
    release_first_setup = threading.Event()
    first_setup_started = threading.Event()
    active_lock = threading.Lock()
    active_setups = 0
    max_active_setups = 0
    hook = SplitPdfHook()

    def slow_setup(hook_ctx, request):
        nonlocal active_setups, max_active_setups
        del hook_ctx
        with active_lock:
            active_setups += 1
            max_active_setups = max(max_active_setups, active_setups)
            if active_setups == 1:
                first_setup_started.set()
        try:
            release_first_setup.wait(timeout=1)
            return request
        finally:
            with active_lock:
                active_setups -= 1

    hook_ctx = MagicMock(spec=BeforeRequestContext)
    first_request = httpx.Request("GET", "http://localhost/first")
    second_request = httpx.Request("GET", "http://localhost/second")

    with patch.object(hook, "_before_request_unlocked", side_effect=slow_setup):
        first_task = asyncio.create_task(hook.before_request_async(hook_ctx, first_request))
        await asyncio.to_thread(first_setup_started.wait, 1)
        second_task = asyncio.create_task(hook.before_request_async(hook_ctx, second_request))
        await asyncio.sleep(0.01)
        release_first_setup.set()

        returned_first, returned_second = await asyncio.gather(first_task, second_task)

    assert returned_first is first_request
    assert returned_second is second_request
    assert max_active_setups == 1


def test_unit_pdfium_helpers_require_split_setup_lock(tmp_path: Path):
    hook = SplitPdfHook()

    with pytest.raises(RuntimeError, match="pypdfium split setup must run"):
        hook._get_pdf_chunks_in_memory(b"%PDF", split_size=1)

    with pytest.raises(RuntimeError, match="pypdfium split setup must run"):
        hook._get_pdf_chunk_paths(
            b"%PDF",
            operation_id="operation-id",
            cache_tmp_data_dir=str(tmp_path),
            split_size=1,
        )


def test_unit_pdfium_new_document_closes_when_in_memory_split_fails():
    hook = SplitPdfHook()
    new_pdf = MagicMock()
    new_pdf.import_pages.side_effect = RuntimeError("import failed")
    pdf_document = MagicMock()
    pdf_document.__enter__.return_value = [MagicMock()]
    pdf_document.__exit__.return_value = None
    pdf_document_factory = MagicMock(return_value=pdf_document)
    pdf_document_factory.new.return_value = new_pdf

    hook._split_pdf_setup_state.locked = True
    try:
        with patch(
            "unstructured_client._hooks.custom.split_pdf_hook.pdfium.PdfDocument",
            pdf_document_factory,
        ), pytest.raises(RuntimeError, match="import failed"):
            hook._get_pdf_chunks_in_memory(b"%PDF", split_size=1)
    finally:
        hook._split_pdf_setup_state.locked = False

    new_pdf.close.assert_called_once_with()


def test_unit_pdfium_new_document_closes_when_cached_split_fails(tmp_path: Path):
    hook = SplitPdfHook()
    new_pdf = MagicMock()
    new_pdf.save.side_effect = RuntimeError("save failed")
    pdf_document = MagicMock()
    pdf_document.__enter__.return_value = [MagicMock()]
    pdf_document.__exit__.return_value = None
    pdf_document_factory = MagicMock(return_value=pdf_document)
    pdf_document_factory.new.return_value = new_pdf

    hook._split_pdf_setup_state.locked = True
    try:
        with patch(
            "unstructured_client._hooks.custom.split_pdf_hook.pdfium.PdfDocument",
            pdf_document_factory,
        ), pytest.raises(RuntimeError, match="save failed"):
            hook._get_pdf_chunk_paths(
                b"%PDF",
                operation_id="operation-id",
                cache_tmp_data_dir=str(tmp_path),
                split_size=1,
            )
    finally:
        hook._split_pdf_setup_state.locked = False

    new_pdf.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_unit_split_pdf_before_request_async_cancellation_cleans_prepared_state():
    setup_started = threading.Event()
    release_setup = threading.Event()
    operation_id = "cancelled-during-setup"
    tempdir = MagicMock()
    hook = SplitPdfHook()

    def slow_setup(hook_ctx, request):
        del hook_ctx, request
        setup_started.set()
        release_setup.wait(timeout=1)
        hook.coroutines_to_execute[operation_id] = []
        hook.pending_operation_ids[operation_id] = operation_id
        hook.tempdirs[operation_id] = tempdir
        return httpx.Request(
            "GET",
            "http://localhost:8888/general/docs",
            headers={"operation_id": operation_id},
            extensions={"split_pdf_operation_id": operation_id},
        )

    hook_ctx = MagicMock(spec=BeforeRequestContext)
    hook_ctx.operation_id = "partition"
    request = httpx.Request("POST", "http://localhost:8888/general/v0/general")

    with patch.object(hook, "_before_request_unlocked", side_effect=slow_setup):
        task = asyncio.create_task(hook.before_request_async(hook_ctx, request))
        await asyncio.to_thread(setup_started.wait, 1)
        task.cancel()
        release_setup.set()

        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)

    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids
    assert operation_id not in hook.tempdirs
    tempdir.cleanup.assert_called_once()

    with patch.object(hook, "_before_request_unlocked", return_value=request):
        assert await asyncio.wait_for(hook.before_request_async(hook_ctx, request), timeout=1) is request


@pytest.mark.asyncio
async def test_unit_split_pdf_before_request_async_cancellation_before_admission_does_not_queue():
    setup_started = threading.Event()
    release_setup = threading.Event()
    hook = SplitPdfHook()
    hook_ctx = MagicMock(spec=BeforeRequestContext)
    hook_ctx.operation_id = "partition"
    request = httpx.Request("POST", "http://localhost:8888/general/v0/general")

    def slow_setup(hook_ctx_arg, request_arg):
        del hook_ctx_arg
        setup_started.set()
        release_setup.wait(timeout=1)
        return request_arg

    with patch.object(hook, "_before_request_unlocked", side_effect=slow_setup) as mock_setup:
        first_task = asyncio.create_task(hook.before_request_async(hook_ctx, request))
        await asyncio.to_thread(setup_started.wait, 1)
        second_task = asyncio.create_task(hook.before_request_async(hook_ctx, request))
        await asyncio.sleep(0)

        second_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second_task

        release_setup.set()
        assert await asyncio.wait_for(first_task, timeout=1) is request

    assert mock_setup.call_count == 1


@pytest.mark.asyncio
async def test_unit_do_request_async_cancellation_during_before_request_cancels_setup():
    setup_started = threading.Event()
    release_setup = threading.Event()

    class SlowBeforeRequestHook:
        def before_request(self, hook_ctx, request):
            del hook_ctx, request
            setup_started.set()
            release_setup.wait(timeout=1)
            return httpx.Request("GET", "http://localhost:8888/general/docs")

    hooks = SDKHooks()
    hooks.before_request_hooks = [SlowBeforeRequestHook()]  # type: ignore[list-item]

    client = _BlockingAsyncClient()
    config = SDKConfiguration(
        client=None,
        client_supplied=False,
        async_client=client,  # type: ignore[arg-type]
        async_client_supplied=True,
        debug_logger=logging.getLogger("test"),
    )
    config.__dict__["_hooks"] = hooks
    sdk = BaseSDK(config)
    task = asyncio.create_task(
        sdk.do_request_async(
            _make_sdk_hook_context(),
            httpx.Request("POST", "http://localhost:8888/general/v0/general"),
            error_status_codes=[],
        )
    )

    await asyncio.to_thread(setup_started.wait, 1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=0.05)

    release_setup.set()


def test_unit_before_request_uses_hook_ctx_timeout_when_request_timeout_missing():
    hook, _, result = _make_hook_with_split_request(
        timeout_extension=None,
        config_timeout_ms=34_000,
    )
    operation_id = result.headers["operation_id"]

    assert hook.operation_timeouts[operation_id] == 34.0


@pytest.mark.asyncio
async def test_unit_before_request_threads_client_retry_config_into_chunk_execution():
    retry_config = RetryConfig(
        "backoff",
        BackoffStrategy(1, 2, 3.0, 4),
        retry_connection_errors=False,
    )
    hook, _, result = _make_hook_with_split_request(
        retry_config=retry_config,
        pdf_chunks=[(io.BytesIO(b"chunk"), 0)],
    )
    operation_id = result.headers["operation_id"]
    coroutine = hook.coroutines_to_execute[operation_id][0]

    with patch(
        "unstructured_client._hooks.custom.request_utils.call_api_async",
        new=AsyncMock(return_value=_httpx_json_response([])),
    ) as mock_call_api_async:
        async with httpx.AsyncClient() as client:
            await coroutine(async_client=client, limiter=asyncio.Semaphore(1))

    assert mock_call_api_async.await_args.kwargs["retry_config"] is retry_config


def test_unit_after_success_clears_on_await_elements_exception():
    hook, _, result = _make_hook_with_split_request()
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"

    with patch.object(hook, "_await_elements", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            hook.after_success(success_ctx, response)

    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids


@pytest.mark.asyncio
async def test_unit_after_success_async_clears_on_await_elements_exception():
    hook, _, result = _make_hook_with_split_request()
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"

    with patch.object(hook, "_await_elements_async", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            await hook.after_success_async(success_ctx, response)

    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids


@pytest.mark.asyncio
async def test_unit_after_success_async_collects_chunks_without_sync_executor():
    hook, _, result = _make_hook_with_split_request(
        pdf_chunks=[(io.BytesIO(b"chunk-1"), 0), (io.BytesIO(b"chunk-2"), 2)],
    )
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"

    assert operation_id not in hook.executors

    with patch(
        "unstructured_client._hooks.custom.request_utils.call_api_async",
        new=AsyncMock(
            side_effect=[
                _httpx_json_response([{"page_number": 1}]),
                _httpx_json_response([{"page_number": 3}]),
            ]
        ),
    ) as mock_call_api_async:
        returned_response = await hook.after_success_async(success_ctx, response)

    assert returned_response.json() == [{"page_number": 1}, {"page_number": 3}]
    assert mock_call_api_async.await_count == 2
    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids


@pytest.mark.asyncio
async def test_unit_after_success_async_cancels_pending_chunks_and_clears_state():
    hook, _, result = _make_hook_with_split_request(
        pdf_chunks=[(io.BytesIO(b"chunk-1"), 0), (io.BytesIO(b"chunk-2"), 2)],
    )
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"
    started = asyncio.Event()
    started_counter = Counter()
    cancelled_counter = Counter()

    async def _pending_request(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        try:
            started_counter.update(["started"])
            if started_counter["started"] == 2:
                started.set()
            await asyncio.Event().wait()
            return _httpx_json_response([])
        except asyncio.CancelledError:
            cancelled_counter.update(["cancelled"])
            raise

    hook.coroutines_to_execute[operation_id] = [partial(_pending_request)] * 2

    task = asyncio.create_task(hook.after_success_async(success_ctx, response))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert cancelled_counter["cancelled"] == 2
    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids


@pytest.mark.asyncio
async def test_unit_after_success_async_timeout_cancels_chunks_and_clears_state():
    hook, _, result = _make_hook_with_split_request(
        pdf_chunks=[(io.BytesIO(b"chunk-1"), 0), (io.BytesIO(b"chunk-2"), 2)],
    )
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"
    tempdir = MagicMock()
    hook.tempdirs[operation_id] = tempdir
    hook.operation_timeouts[operation_id] = 0.001
    cancelled_counter = Counter()

    async def _pending_request(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        del async_client, limiter
        try:
            await asyncio.Event().wait()
            return _httpx_json_response([])
        except asyncio.CancelledError:
            cancelled_counter.update(["cancelled"])
            raise

    hook.coroutines_to_execute[operation_id] = [partial(_pending_request)] * 2

    with patch("unstructured_client._hooks.custom.split_pdf_hook.TIMEOUT_BUFFER_SECONDS", 0):
        with pytest.raises(TimeoutError):
            await hook.after_success_async(success_ctx, response)

    assert cancelled_counter["cancelled"] == 2
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids
    assert operation_id not in hook.tempdirs
    tempdir.cleanup.assert_called_once()


def test_unit_after_success_sync_lazily_creates_and_cleans_executor():
    hook, _, result = _make_hook_with_split_request(
        pdf_chunks=[(io.BytesIO(b"chunk"), 0)],
    )
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"
    fake_executor = MagicMock()
    fake_future = MagicMock()
    fake_future.done.return_value = True
    fake_future.result.return_value = [(1, _httpx_json_response([{"page_number": 1}]))]
    fake_executor.submit.return_value = fake_future

    with patch(
        "unstructured_client._hooks.custom.split_pdf_hook.futures.ThreadPoolExecutor",
        return_value=fake_executor,
    ):
        returned_response = hook.after_success(success_ctx, response)

    assert returned_response.json() == [{"page_number": 1}]
    fake_executor.submit.assert_called_once()
    fake_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids


def test_unit_future_timeout_triggers_cleanup(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="unstructured-client")
    hook, _, result = _make_hook_with_split_request(pdf_chunks=[(io.BytesIO(b"chunk"), 0)])
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"

    fake_future: futures.Future[list[tuple[int, httpx.Response]]] = futures.Future()

    def _raise_timeout(timeout=None):
        raise futures.TimeoutError()

    fake_future.result = _raise_timeout  # type: ignore[method-assign]
    fake_executor = MagicMock()
    tempdir = MagicMock()
    tempdir.name = "/tmp/test-split-timeout"
    loop = MagicMock()

    def _submit_side_effect(*args, **kwargs):
        args[1].close()
        loop_holder = args[2]
        loop_holder["loop"] = loop
        return fake_future

    fake_executor.submit.side_effect = _submit_side_effect
    hook.executors[operation_id] = fake_executor
    hook.tempdirs[operation_id] = tempdir

    with pytest.raises(futures.TimeoutError):
        hook.after_success(success_ctx, response)

    assert operation_id not in hook.executors
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.pending_operation_ids
    loop.call_soon_threadsafe.assert_called()
    tempdir.cleanup.assert_not_called()
    fake_executor.shutdown.assert_not_called()
    assert f"event=batch_timeout operation_id={operation_id}" in caplog.text

    fake_future.set_exception(futures.CancelledError())

    tempdir.cleanup.assert_called_once()
    fake_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


def test_unit_future_timeout_preserves_timeout_when_loop_is_closed(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.INFO, logger="unstructured-client")
    hook, _, result = _make_hook_with_split_request(pdf_chunks=[(io.BytesIO(b"chunk"), 0)])
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"

    fake_future: futures.Future[list[tuple[int, httpx.Response]]] = futures.Future()

    def _raise_timeout(timeout=None):
        raise futures.TimeoutError()

    fake_future.result = _raise_timeout  # type: ignore[method-assign]
    fake_executor = MagicMock()
    tempdir = MagicMock()
    tempdir.name = "/tmp/test-split-timeout-closed-loop"
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = RuntimeError("Event loop is closed")

    def _submit_side_effect(*args, **kwargs):
        loop_holder = args[2]
        loop_holder["loop"] = loop
        return fake_future

    fake_executor.submit.side_effect = _submit_side_effect
    hook.executors[operation_id] = fake_executor
    hook.tempdirs[operation_id] = tempdir

    with pytest.raises(futures.TimeoutError):
        hook.after_success(success_ctx, response)

    assert "event=loop_closed_during_cancel" in caplog.text
    fake_future.set_exception(futures.CancelledError())
    tempdir.cleanup.assert_called_once()
    fake_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


def test_unit_clear_operation_does_not_raise_when_loop_is_closed():
    hook = SplitPdfHook()
    operation_id = "loop-closed-clear-operation"
    future: futures.Future[list[tuple[int, httpx.Response]]] = futures.Future()
    executor = MagicMock()
    tempdir = MagicMock()
    loop = MagicMock()
    loop.call_soon_threadsafe.side_effect = RuntimeError("Event loop is closed")

    hook.coroutines_to_execute[operation_id] = [MagicMock()]
    hook.executors[operation_id] = executor
    hook.tempdirs[operation_id] = tempdir
    hook.operation_futures[operation_id] = future
    hook.operation_loops[operation_id] = {"loop": loop}

    hook._clear_operation(operation_id)

    future.set_result([])
    tempdir.cleanup.assert_called_once()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


@pytest.mark.asyncio
async def test_unit_call_api_async_closes_file_on_exception():
    pdf_chunk_file = MagicMock(spec=io.BufferedReader)
    pdf_chunk_file.closed = False
    request = httpx.Request("POST", "http://localhost:8888/general/v0/general")
    client = AsyncMock(spec=httpx.AsyncClient)

    with patch(
        "unstructured_client._hooks.custom.request_utils.retry_async",
        new=AsyncMock(side_effect=httpx.ConnectError("boom", request=request)),
    ):
        with pytest.raises(httpx.ConnectError):
            await request_utils.call_api_async(
                client=client,
                pdf_chunk_request=request,
                pdf_chunk_file=pdf_chunk_file,
                limiter=asyncio.Semaphore(1),
            )

    pdf_chunk_file.close.assert_called_once()


@pytest.mark.asyncio
async def test_unit_call_api_async_logs_chunk_context(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger="unstructured-client")
    pdf_chunk_file = io.BytesIO(b"chunk")
    request = httpx.Request("POST", "http://localhost:8888/general/v0/general")
    client = AsyncMock(spec=httpx.AsyncClient)

    with patch(
        "unstructured_client._hooks.custom.request_utils.retry_async",
        new=AsyncMock(side_effect=httpx.ConnectError("boom", request=request)),
    ):
        with pytest.raises(httpx.ConnectError):
            await request_utils.call_api_async(
                client=client,
                pdf_chunk_request=request,
                pdf_chunk_file=pdf_chunk_file,
                limiter=asyncio.Semaphore(1),
                operation_id="op-123",
                chunk_index=4,
                page_number=17,
            )

    assert "event=chunk_request_error operation_id=op-123 chunk_index=4 page_number=17" in caplog.text


def test_unit_allow_failed_partial_results(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="unstructured-client")
    hook = SplitPdfHook()
    operation_id = "allow-failed-partial"
    hook.coroutines_to_execute[operation_id] = [partial(_request_mock, fails=False, content="unused")] * 3
    hook.concurrency_level[operation_id] = 3
    hook.allow_failed[operation_id] = True
    hook.cache_tmp_data_feature[operation_id] = False
    hook.executors[operation_id] = MagicMock()

    fake_future = MagicMock()
    fake_future.result.return_value = [
        (1, _httpx_json_response([{"page_number": 1}])),
        (2, _httpx_response("boom", status_code=500)),
        (3, _httpx_json_response([{"page_number": 3}])),
    ]
    hook.executors[operation_id].submit.return_value = fake_future

    elements = hook._await_elements(operation_id)

    assert elements == [{"page_number": 1}, {"page_number": 3}]
    assert len(hook.api_failed_responses[operation_id]) == 1
    assert f"event=batch_complete operation_id={operation_id}" in caplog.text
    assert "success_count=2" in caplog.text
    assert "failure_count=1" in caplog.text


def test_unit_allow_failed_all_fail_records_failures():
    hook = SplitPdfHook()
    operation_id = "allow-failed-all-fail"
    hook.coroutines_to_execute[operation_id] = [partial(_request_mock, fails=False, content="unused")] * 2
    hook.concurrency_level[operation_id] = 2
    hook.allow_failed[operation_id] = True
    hook.cache_tmp_data_feature[operation_id] = False
    hook.executors[operation_id] = MagicMock()

    fake_future = MagicMock()
    fake_future.result.return_value = [
        (1, _httpx_response("boom", status_code=500)),
        (2, _httpx_response("boom", status_code=500)),
    ]
    hook.executors[operation_id].submit.return_value = fake_future

    assert hook._await_elements(operation_id) == []
    assert len(hook.api_failed_responses[operation_id]) == 2


def test_unit_allow_failed_after_success_returns_first_failed_response_when_zero_chunks_succeed():
    hook, _, result = _make_hook_with_split_request(allow_failed="true")
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"
    failed_response = _httpx_response("transport failure", status_code=500)
    failed_response.extensions["transport_exception"] = httpx.ConnectError(
        "boom",
        request=failed_response.request,
    )
    hook._annotate_failure_response(
        operation_id,
        failed_chunk_index=1,
        successful_count=0,
        failed_count=1,
        total_chunks=1,
        response=failed_response,
    )
    hook.allow_failed[operation_id] = True
    hook.api_successful_responses[operation_id] = []
    hook.api_failed_responses[operation_id] = [failed_response]

    with patch.object(hook, "_await_elements", return_value=[]):
        returned_response = hook.after_success(success_ctx, response)

    assert returned_response is failed_response
    assert returned_response.headers[f"{SPLIT_PDF_HEADER_PREFIX}Operation-Id"] == operation_id
    assert returned_response.headers[f"{SPLIT_PDF_HEADER_PREFIX}Chunk-Index"] == "1"
    assert returned_response.headers[f"{SPLIT_PDF_HEADER_PREFIX}Success-Count"] == "0"
    assert returned_response.headers[f"{SPLIT_PDF_HEADER_PREFIX}Failure-Count"] == "1"
    assert returned_response.extensions["split_pdf_failure_metadata"][
        f"{SPLIT_PDF_HEADER_PREFIX}Operation-Id"
    ] == operation_id


def test_unit_disallow_failed_after_success_returns_first_failed_response():
    hook, _, result = _make_hook_with_split_request()
    operation_id = result.headers["operation_id"]
    response = httpx.Response(status_code=200, request=result)
    success_ctx = MagicMock(spec=AfterSuccessContext)
    success_ctx.operation_id = "partition"
    failed_response = _httpx_response("failure", status_code=500)
    hook.allow_failed[operation_id] = False
    hook.api_failed_responses[operation_id] = [failed_response]

    with patch.object(hook, "_await_elements", return_value=[]):
        returned_response = hook.after_success(success_ctx, response)

    assert returned_response is failed_response


def test_before_request_failure_after_state_setup_cleans_partial_operation():
    hook = SplitPdfHook()
    hook.sdk_init(base_url="http://localhost:8888", client=httpx.Client())
    executor = MagicMock()
    tempdir = MagicMock()
    tempdir.name = "/tmp/before-request-failure"
    hook_ctx = MagicMock(spec=BeforeRequestContext)
    hook_ctx.operation_id = "partition"
    hook_ctx.config = MagicMock()
    hook_ctx.config.timeout_ms = 12_000
    hook_ctx.config.retry_config = UNSET
    request = httpx.Request(
        "POST",
        "http://localhost:8888/general/v0/general",
        headers={"Content-Type": "multipart/form-data"},
        extensions={"timeout": {"connect": 12.0, "read": 12.0, "write": 12.0, "pool": 12.0}},
    )
    mock_pdf_file = MagicMock()
    mock_form_data = {
        "split_pdf_page": "true",
        "strategy": "fast",
        "split_pdf_cache_tmp_data": "true",
        "files": {
            "filename": "test.pdf",
            "content_type": "application/pdf",
            "file": mock_pdf_file,
        },
    }
    mock_pdf_reader = MagicMock()
    mock_pdf_reader.get_num_pages.return_value = 100
    mock_pdf_reader.pages = [MagicMock()] * 100
    mock_pdf_reader.stream = io.BytesIO(b"fake-pdf-bytes")

    def _chunk_paths_side_effect(*args, **kwargs):
        hook.tempdirs[kwargs["operation_id"]] = tempdir
        return [(Path("/tmp/chunk-1.pdf"), 0)]

    with patch("unstructured_client._hooks.custom.request_utils.get_multipart_stream_fields") as mock_get_fields, \
         patch("unstructured_client._hooks.custom.pdf_utils.read_pdf") as mock_read_pdf, \
         patch("unstructured_client._hooks.custom.pdf_utils.check_pdf") as mock_check_pdf, \
         patch("unstructured_client._hooks.custom.request_utils.get_base_url") as mock_get_base_url, \
         patch("unstructured_client._hooks.custom.split_pdf_hook.futures.ThreadPoolExecutor", return_value=executor), \
         patch("unstructured_client._hooks.custom.request_utils.create_pdf_chunk_request", side_effect=RuntimeError("chunk build failed")), \
         patch.object(hook, "_trim_large_pages", side_effect=lambda pdf, fd: pdf), \
         patch.object(hook, "_get_pdf_chunk_paths", side_effect=_chunk_paths_side_effect), \
         patch.object(hook, "_get_pdf_chunk_files", return_value=[(io.BytesIO(b"chunk"), 0)]):
        mock_get_fields.return_value = mock_form_data
        mock_read_pdf.return_value = mock_pdf_reader
        mock_check_pdf.return_value = mock_pdf_reader
        mock_get_base_url.return_value = "http://localhost:8888"

        with pytest.raises(RuntimeError, match="chunk build failed"):
            hook.before_request(hook_ctx, request)

    assert hook.coroutines_to_execute == {}
    assert hook.executors == {}
    assert hook.tempdirs == {}
    assert hook.operation_timeouts == {}
    assert hook.operation_retry_configs == {}
    assert hook.allow_failed == {}
    assert hook.cache_tmp_data_feature == {}
    assert hook.cache_tmp_data_dir == {}
    tempdir.cleanup.assert_called_once()
    executor.shutdown.assert_not_called()