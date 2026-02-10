from __future__ import annotations

import asyncio
from asyncio import Task
from collections import Counter
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import requests
from requests_toolbelt import MultipartDecoder

from _test_unstructured_client.unit_utils import sample_docs_path
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
    SplitPdfHook,
    get_optimal_split_size, run_tasks,
)
from unstructured_client._hooks.types import BeforeRequestContext
from unstructured_client.models import shared


def test_unit_clear_operation():
    """Test clear operation method properly clears request/response data."""
    hook = SplitPdfHook()
    operation_id = "some_id"

    async def example():
        pass

    hook.coroutines_to_execute[operation_id] = [example(), example()]
    hook.api_successful_responses[operation_id] = [
        requests.Response(),
        requests.Response(),
    ]

    assert len(hook.coroutines_to_execute[operation_id]) == 2
    assert len(hook.api_successful_responses[operation_id]) == 2

    hook._clear_operation(operation_id)

    assert hook.coroutines_to_execute.get(operation_id) is None
    assert hook.api_successful_responses.get(operation_id) is None


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
    assert headers, expected_headers


def test_unit_create_response():
    """Test create response method properly overrides body elements and Content-Length header."""
    test_elements = [{"key": "value"}, {"key_2": "value"}]

    expected_status_code = 200
    expected_content = b'[{"key": "value"}, {"key_2": "value"}]'
    expected_content_length = "38"

    response = request_utils.create_response(test_elements)

    assert response.status_code, expected_status_code
    assert response._content, expected_content
    assert response.headers.get("Content-Length"), expected_content_length


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


def test_per_request_settings_isolation():
    """Test that multiple concurrent requests have isolated settings.

    This validates the fix for race conditions where instance-level settings
    would be shared between concurrent requests, causing one request to use
    another's configuration.
    """
    hook = SplitPdfHook()

    # Simulate two different operations with different settings
    operation_id_1 = "op-1"
    operation_id_2 = "op-2"

    # Set different settings for each operation
    hook.allow_failed[operation_id_1] = True
    hook.cache_tmp_data_feature[operation_id_1] = True
    hook.cache_tmp_data_dir[operation_id_1] = "/tmp/op1"
    hook.concurrency_level[operation_id_1] = 5

    hook.allow_failed[operation_id_2] = False
    hook.cache_tmp_data_feature[operation_id_2] = False
    hook.cache_tmp_data_dir[operation_id_2] = "/tmp/op2"
    hook.concurrency_level[operation_id_2] = 10

    # Verify that each operation has its own isolated settings
    assert hook.allow_failed[operation_id_1] is True
    assert hook.allow_failed[operation_id_2] is False

    assert hook.cache_tmp_data_feature[operation_id_1] is True
    assert hook.cache_tmp_data_feature[operation_id_2] is False

    assert hook.cache_tmp_data_dir[operation_id_1] == "/tmp/op1"
    assert hook.cache_tmp_data_dir[operation_id_2] == "/tmp/op2"

    assert hook.concurrency_level[operation_id_1] == 5
    assert hook.concurrency_level[operation_id_2] == 10


def test_per_request_settings_cleanup():
    """Test that per-request settings are properly cleaned up after operation completes."""
    hook = SplitPdfHook()

    operation_id = "test-op"

    # Set up operation data
    hook.allow_failed[operation_id] = True
    hook.cache_tmp_data_feature[operation_id] = True
    hook.cache_tmp_data_dir[operation_id] = "/tmp/test"
    hook.concurrency_level[operation_id] = 8
    hook.coroutines_to_execute[operation_id] = []
    hook.api_successful_responses[operation_id] = []
    hook.api_failed_responses[operation_id] = []

    # Verify data exists
    assert operation_id in hook.allow_failed
    assert operation_id in hook.cache_tmp_data_feature
    assert operation_id in hook.cache_tmp_data_dir
    assert operation_id in hook.concurrency_level

    # Clear the operation
    hook._clear_operation(operation_id)

    # Verify all data is cleaned up
    assert operation_id not in hook.allow_failed
    assert operation_id not in hook.cache_tmp_data_feature
    assert operation_id not in hook.cache_tmp_data_dir
    assert operation_id not in hook.concurrency_level
    assert operation_id not in hook.coroutines_to_execute
    assert operation_id not in hook.api_successful_responses
    assert operation_id not in hook.api_failed_responses


@pytest.mark.asyncio
async def test_concurrent_async_operations_isolation():
    """Test that concurrent async operations maintain isolated settings.

    This simulates the real-world scenario where multiple partition_async
    calls are made concurrently and ensures they don't interfere with each other.
    """
    hook = SplitPdfHook()

    # Track which settings each operation saw
    operation_settings = {}

    async def simulate_operation(op_id: str, allow_failed: bool, cache_enabled: bool):
        """Simulate an operation that sets and reads its own settings."""
        # Set operation-specific settings
        hook.allow_failed[op_id] = allow_failed
        hook.cache_tmp_data_feature[op_id] = cache_enabled
        hook.concurrency_level[op_id] = 5

        # Simulate some async work
        await asyncio.sleep(0.01)

        # Read back settings and verify they haven't changed
        operation_settings[op_id] = {
            'allow_failed': hook.allow_failed.get(op_id),
            'cache_enabled': hook.cache_tmp_data_feature.get(op_id),
            'concurrency_level': hook.concurrency_level.get(op_id),
        }

        # Clean up
        hook._clear_operation(op_id)

    # Run multiple operations concurrently with different settings
    tasks = [
        simulate_operation("op-1", True, True),
        simulate_operation("op-2", False, False),
        simulate_operation("op-3", True, False),
        simulate_operation("op-4", False, True),
    ]

    await asyncio.gather(*tasks)

    # Verify each operation saw its own settings correctly
    assert operation_settings["op-1"] == {'allow_failed': True, 'cache_enabled': True, 'concurrency_level': 5}
    assert operation_settings["op-2"] == {'allow_failed': False, 'cache_enabled': False, 'concurrency_level': 5}
    assert operation_settings["op-3"] == {'allow_failed': True, 'cache_enabled': False, 'concurrency_level': 5}
    assert operation_settings["op-4"] == {'allow_failed': False, 'cache_enabled': True, 'concurrency_level': 5}


@pytest.mark.asyncio
async def test_await_elements_uses_operation_settings():
    """Test that _await_elements correctly uses per-operation settings."""
    hook = SplitPdfHook()

    operation_id = "test-op"

    # Set operation-specific settings
    hook.allow_failed[operation_id] = True
    hook.cache_tmp_data_feature[operation_id] = False
    hook.concurrency_level[operation_id] = 3

    # Mock the coroutines to execute
    async def mock_coroutine(async_client, limiter):
        """Mock coroutine that returns a successful response."""
        response = httpx.Response(
            status_code=200,
            json=[{"element": "test"}],
        )
        return response

    hook.coroutines_to_execute[operation_id] = [
        partial(mock_coroutine)
    ]

    # Mock run_tasks to verify it receives the correct settings
    with patch("unstructured_client._hooks.custom.split_pdf_hook.run_tasks") as mock_run_tasks:
        mock_run_tasks.return_value = [(1, httpx.Response(
            status_code=200,
            content=b'[{"element": "test"}]',
        ))]

        await hook._await_elements(operation_id)

        # Verify run_tasks was called with the operation-specific settings
        mock_run_tasks.assert_called_once()
        call_args = mock_run_tasks.call_args

        # Check that allow_failed matches what we set
        assert call_args.kwargs['allow_failed'] is True
        assert call_args.kwargs['concurrency_level'] == 3


def test_default_values_used_when_operation_not_found():
    """Test that default values are used when operation_id is not in the settings dicts."""
    hook = SplitPdfHook()

    # Don't set any values for this operation
    operation_id = "missing-op"

    # Access settings with .get() should return defaults
    from unstructured_client._hooks.custom.split_pdf_hook import (
        DEFAULT_ALLOW_FAILED,
        DEFAULT_CACHE_TMP_DATA,
        DEFAULT_CACHE_TMP_DATA_DIR,
        DEFAULT_CONCURRENCY_LEVEL,
    )

    assert hook.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED) == DEFAULT_ALLOW_FAILED
    assert hook.cache_tmp_data_feature.get(operation_id, DEFAULT_CACHE_TMP_DATA) == DEFAULT_CACHE_TMP_DATA
    assert hook.cache_tmp_data_dir.get(operation_id, DEFAULT_CACHE_TMP_DATA_DIR) == DEFAULT_CACHE_TMP_DATA_DIR
    assert hook.concurrency_level.get(operation_id, DEFAULT_CONCURRENCY_LEVEL) == DEFAULT_CONCURRENCY_LEVEL