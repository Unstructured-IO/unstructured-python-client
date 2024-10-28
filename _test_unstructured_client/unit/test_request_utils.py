from __future__ import annotations

# Get unit tests for request_utils.py module
import httpx
import pytest

from unstructured_client._hooks.custom.request_utils import create_pdf_chunk_request_params, create_response, get_multipart_stream_fields


# make the above test using @pytest.mark.parametrize
@pytest.mark.parametrize(("input_request", "expected"), [
    (httpx.Request("POST", "http://localhost:8000", data={}, headers={"Content-Type": "multipart/form-data"}), {}),
    (httpx.Request("POST", "http://localhost:8000", data={"hello": "world"}, headers={"Content-Type": "application/json"}), {}),
    (httpx.Request(
        "POST",
        "http://localhost:8000",
        data={"hello": "world"},
        files={"files": ("hello.pdf", b"hello", "application/pdf")},
        headers={"Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"}),
    {
        "hello": "world",
        "files": {
            "content_type":"application/pdf",
            "filename": "hello.pdf",
            "file": b"hello",
        }
     }
    ),
])
def test_get_multipart_stream_fields(input_request, expected):
    fields = get_multipart_stream_fields(input_request)
    assert fields == expected


def test_multipart_stream_fields_raises_value_error_when_filename_is_not_set():
    with pytest.raises(ValueError):
        get_multipart_stream_fields(httpx.Request(
            "POST",
            "http://localhost:8000",
            data={"hello": "world"},
            files={"files": ("", b"hello", "application/pdf")},
            headers={"Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"}),
        )


@pytest.mark.parametrize(("input_form_data", "page_number", "expected_form_data"), [
    (
            {"hello": "world"},
            2,
            {"hello": "world", "split_pdf_page": "false", "starting_page_number": "2"}
    ),
    (
            {"hello": "world", "split_pdf_page": "true"},
            2,
            {"hello": "world", "split_pdf_page": "false", "starting_page_number": "2"}
    ),
    (
            {"hello": "world", "split_pdf_page": "true", "files": "dummy_file"},
            3,
            {"hello": "world", "split_pdf_page": "false", "starting_page_number": "3"}
    ),
    (
            {"split_pdf_page_range[]": [1, 3], "hello": "world", "split_pdf_page": "true", "files": "dummy_file"},
            3,
            {"hello": "world", "split_pdf_page": "false", "starting_page_number": "3"}
    ),
    (
            {"split_pdf_page_range": [1, 3], "hello": "world", "split_pdf_page": "true", "files": "dummy_file"},
            4,
            {"hello": "world", "split_pdf_page": "false", "starting_page_number": "4"}
    ),
])
def test_create_pdf_chunk_request_params(input_form_data, page_number, expected_form_data):
    form_data = create_pdf_chunk_request_params(input_form_data, page_number)
    assert form_data == expected_form_data


def test_create_response_for_json():
    elements = [
        {"type": "Title", "text": "Hello, World!"},
        {"type": "NarrativeText", "text": "Goodbye!"},
    ]
    response = create_response(elements)
    assert response.status_code == 200
    assert response.json() == elements
    assert response.headers["Content-Type"] == "application/json"


def test_create_response_for_csv():
    elements = 'type,element_id,text,languages,page_number,filename,filetype,parent_id' \
        '\nTitle,f73329878fbbb0bb131a83e7b6daacbe,Module One - Introduction to Product' \
        ' Development and Quality Assurance,[\'eng\'],1,list-item-example-1.pdf,application/pdf,'
    response = create_response(elements)
    assert response.status_code == 200
    assert response.json() == None
    assert response.headers["Content-Type"] == "text/csv"
