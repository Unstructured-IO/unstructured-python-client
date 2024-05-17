import io
import logging
import os
from concurrent.futures import Future
from unittest import TestCase

import pytest
import requests
from requests_toolbelt import MultipartDecoder, MultipartEncoder
from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
)
from unstructured_client._hooks.custom.split_pdf_hook import (
    DEFAULT_CONCURRENCY_LEVEL,
    DEFAULT_STARTING_PAGE_NUMBER,
    MAX_CONCURRENCY_LEVEL,
    MAX_PAGES_PER_SPLIT,
    MIN_PAGES_PER_SPLIT,
    SplitPdfHook,
    get_optimal_split_size,
)
from unstructured_client.models import shared


def test_unit_sdk_init():
    """Test sdk init method properly sets the client."""
    hook = SplitPdfHook()
    # This is a fake URL, test doesn't make an API call
    test_url = "http://localhost:5000"
    test_client = requests.Session()

    hook.sdk_init(test_url, test_client)

    assert hook.client == test_client


def test_unit_clear_operation():
    """Test clear operation method properly clears request/response data."""
    hook = SplitPdfHook()
    operation_id = "some_id"
    hook.partition_requests[operation_id] = [Future(), Future()]
    hook.partition_responses[operation_id] = [
        requests.Response(),
        requests.Response(),
    ]

    assert len(hook.partition_requests[operation_id]) == 2
    assert len(hook.partition_responses[operation_id]) == 2

    hook._clear_operation(operation_id)

    assert hook.partition_requests.get(operation_id) is None
    assert hook.partition_responses.get(operation_id) is None


def test_unit_prepare_request_payload():
    """Test prepare request payload method properly sets split_pdf_page to 'false'
    and removes files key."""
    test_form_data = {
        "files": ("test_file.pdf", b"test_file_content"),
        "split_pdf_page": "true",
        "parameter_1": "value_1",
        "parameter_2": "value_2",
        "parameter_3": "value_3",
    }
    expected_form_data = {
        "split_pdf_page": "false",
        "parameter_1": "value_1",
        "parameter_2": "value_2",
        "parameter_3": "value_3",
    }

    payload = request_utils.prepare_request_payload(test_form_data)

    assert payload != test_form_data
    assert payload, expected_form_data


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
    test_response = requests.Response()
    test_response.status_code = 200
    test_response._content = b'[{"key_2": "value"}]'
    test_response.headers = requests.structures.CaseInsensitiveDict(
        {
            "Content-Type": "application/json",
            "Content-Length": len(test_response._content),
        }
    )

    expected_status_code = 200
    expected_content = b'[{"key": "value"}, {"key_2": "value"}]'
    expected_content_length = "38"

    response = request_utils.create_response(test_response, test_elements)

    assert response.status_code, expected_status_code
    assert response._content, expected_content
    assert response.headers.get("Content-Length"), expected_content_length


def test_unit_create_request():
    """Test create request method properly sets file, Content-Type and Content-Length headers."""

    # Prepare test data
    request = requests.PreparedRequest()
    request.headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer token",
    }
    form_data = {
        "parameter_1": "value_1",
        "parameter_2": "value_2",
    }
    page = (io.BytesIO(b"page_content"), 1)
    filename = "test_file.pdf"

    # Expected results
    expected_payload = {
        "parameter_1": "value_1",
        "parameter_2": "value_2",
        "split_pdf_page": "false",
        "starting_page_number": "7",
    }
    expected_page_filename = "test_file.pdf"
    expected_body = MultipartEncoder(
        fields={
            **expected_payload,
            "files": (
                expected_page_filename,
                page[0],
                "application/pdf",
            ),
        }
    )
    expected_url = ""

    # Create request
    request_obj = request_utils.create_request(request, form_data, page[0], filename, 7)
    request_content_type: str = request_obj.headers.get("Content-Type")
    # Assert the request object
    assert request_obj.method == "POST"
    assert request_obj.url == expected_url
    assert request_obj.data.fields == expected_body.fields
    assert request_content_type.startswith("multipart/form-data")


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
    """Test parse form data method properly parses the form data and returns dictionary."""

    # Prepare test data
    decoded_data = MultipartDecoder(
        b'--boundary\r\nContent-Disposition: form-data; name="files"; filename="test_file.pdf"\r\n\r\nfile_content\r\n--boundary\r\nContent-Disposition: form-data; name="parameter_1"\r\n\r\nvalue_1\r\n--boundary\r\nContent-Disposition: form-data; name="parameter_2"\r\n\r\nvalue_2\r\n--boundary--\r\n',
        "multipart/form-data; boundary=boundary",
    )

    # Expected results
    expected_form_data = {
        "files": shared.Files(b"file_content", "test_file.pdf"),
        "parameter_1": "value_1",
        "parameter_2": "value_2",
    }

    # Parse form data
    form_data = form_utils.parse_form_data(decoded_data)

    # Assert the parsed form data
    assert form_data.get("parameter_1") == expected_form_data.get("parameter_1")
    assert form_data.get("parameter_2") == expected_form_data.get("parameter_2")
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
    """Test is pdf method returns True for valid pdf file (has .pdf extension and can be read)."""
    filename = "_sample_docs/layout-parser-paper-fast.pdf"

    with open(filename, "rb") as f:
        file = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    result = pdf_utils.is_pdf(file)

    assert result is True


def test_unit_is_pdf_invalid_extension(caplog):
    """Test is pdf method returns False for file with invalid extension."""
    file = shared.Files(b"txt_content", "test_file.txt")

    with caplog.at_level(logging.WARNING):
        result = pdf_utils.is_pdf(file)

    assert result is False
    assert "Given file doesn't have '.pdf' extension" in caplog.text


def test_unit_is_pdf_invalid_pdf(caplog):
    """Test is pdf method returns False for file with invalid pdf content."""
    file = shared.Files(b"invalid_pdf_content", "test_file.pdf")

    with caplog.at_level(logging.WARNING):
        result = pdf_utils.is_pdf(file)

    assert result is False
    assert "Attempted to interpret file as pdf" in caplog.text


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
        ({"split_pdf_concurrency_level": 10}, 10),  # valid number
        (
            # exceeds max value
            {"split_pdf_concurrency_level": f"{MAX_CONCURRENCY_LEVEL+1}"},
            MAX_CONCURRENCY_LEVEL,
        ),
        ({"split_pdf_concurrency_level": -3}, DEFAULT_CONCURRENCY_LEVEL),  # negative value
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
