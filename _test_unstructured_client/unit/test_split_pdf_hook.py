from __future__ import annotations

import asyncio
import io
import logging
from asyncio import Task
from collections import Counter
from typing import Coroutine

import httpx
import pytest
import requests
from requests_toolbelt import MultipartDecoder, MultipartEncoder

from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
)
from unstructured_client._hooks.custom.split_pdf_hook import (
    DEFAULT_CONCURRENCY_LEVEL,
    DEFAULT_STARTING_PAGE_NUMBER,
    MAX_CONCURRENCY_LEVEL,
    MAX_PAGES_PER_SPLIT,
    MIN_PAGES_PER_SPLIT,
    SplitPdfHook,
    get_optimal_split_size, run_tasks,
)
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


def test_unit_is_pdf_valid_pdf():
    """Test is pdf method returns True for valid pdf file with filename."""
    filename = "_sample_docs/layout-parser-paper-fast.pdf"

    with open(filename, "rb") as f:
        file = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    result = pdf_utils.read_pdf(file)

    assert result is not None


def test_unit_is_pdf_valid_pdf_without_file_extension():
    """Test is pdf method returns True for file with valid pdf content without basing on file extension."""
    filename = "_sample_docs/layout-parser-paper-fast.pdf"
    
    with open(filename, "rb") as f:
        file = shared.Files(
            content=f.read(),
            file_name="uuid1234",
        )

    result = pdf_utils.read_pdf(file)

    assert result is not None


def test_unit_is_pdf_invalid_extension():
    """Test is pdf method returns False for file with invalid extension."""
    file = shared.Files(content=b"txt_content", file_name="test_file.txt")

    result = pdf_utils.read_pdf(file)

    assert result is None


def test_unit_is_pdf_invalid_pdf():
    """Test is pdf method returns False for file with invalid pdf content."""
    file = shared.Files(content=b"invalid_pdf_content", file_name="test_file.pdf")

    result = pdf_utils.read_pdf(file)

    assert result is None


def test_unit_is_pdf_invalid_pdf_without_file_extension():
    """Test is pdf method returns False for file with invalid pdf content without basing on file extension."""
    file = shared.Files(content=b"invalid_pdf_content", file_name="uuid1234")

    result = pdf_utils.read_pdf(file)

    assert result is not None
    

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


async def _request_mock(fails: bool, content: str) -> requests.Response:
    response = requests.Response()
    response.status_code = 500 if fails else 200
    response._content = content.encode()
    return response


@pytest.mark.parametrize(
    ("allow_failed", "tasks", "expected_responses"), [
        pytest.param(
            True, [
                _request_mock(fails=False, content="1"),
                _request_mock(fails=False, content="2"),
                _request_mock(fails=False, content="3"),
                _request_mock(fails=False, content="4"),
            ],
            ["1", "2", "3", "4"],
            id="no failures, fails allower"
        ),
        pytest.param(
            True, [
                _request_mock(fails=False, content="1"),
                _request_mock(fails=True, content="2"),
                _request_mock(fails=False, content="3"),
                _request_mock(fails=True, content="4"),
            ],
            ["1", "2", "3", "4"],
            id="failures, fails allowed"
        ),
        pytest.param(
            False, [
                _request_mock(fails=True, content="failure"),
                _request_mock(fails=False, content="2"),
                _request_mock(fails=True, content="failure"),
                _request_mock(fails=False, content="4"),
            ],
            ["failure"],
            id="failures, fails disallowed"
        ),
        pytest.param(
            False, [
                _request_mock(fails=False, content="1"),
                _request_mock(fails=False, content="2"),
                _request_mock(fails=False, content="3"),
                _request_mock(fails=False, content="4"),
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


async def _fetch_canceller_error(fails: bool, content: str, cancelled_counter: Counter):
    try:
        if not fails:
            await asyncio.sleep(0.01)
            print("Doesn't fail")
        else:
            print("Fails")
        return await _request_mock(fails=fails, content=content)
    except asyncio.CancelledError:
        cancelled_counter.update(["cancelled"])
        print(cancelled_counter["cancelled"])
        print("Cancelled")


@pytest.mark.asyncio
async def test_remaining_tasks_cancelled_when_fails_disallowed():
    cancelled_counter = Counter()
    tasks = [
        _fetch_canceller_error(fails=True, content="1", cancelled_counter=cancelled_counter),
        *[_fetch_canceller_error(fails=False, content=f"{i}", cancelled_counter=cancelled_counter)
          for i in range(2, 200)],
    ]

    await run_tasks(tasks, allow_failed=False)
    # give some time to actually cancel the tasks in background
    await asyncio.sleep(1)
    print("Cancelled amount: ", cancelled_counter["cancelled"])
    assert len(tasks) > cancelled_counter["cancelled"] > 0
