# Get unit tests for request_utils.py module
import httpx
import pytest

from unstructured_client._hooks.custom.request_utils import (
    create_pdf_chunk_request_params,
    get_multipart_stream_fields,
)


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




@pytest.mark.asyncio
@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("status_code", [500, 503])
async def test_declared_non_retryable_chunk_sent_once(tmp_path, cached, status_code):
    import asyncio
    import io

    from unstructured_client._hooks.custom.split_pdf_hook import SplitPdfHook
    from unstructured_client.utils import BackoffStrategy, RetryConfig

    body = {"detail": "unsupported chunk", "retryable": False}
    attempts = []

    def respond(request):
        attempts.append(request)
        return httpx.Response(status_code, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        response = await SplitPdfHook().call_api_partial(
            pdf_chunk_request=httpx.Request(
                "POST", "http://test.invalid/general/v0/general",
                headers={"Accept": "application/x-ndjson" if cached else "application/json"},
                content=b"pdf chunk",
            ),
            pdf_chunk_file=io.BytesIO(b"pdf chunk"),
            limiter=asyncio.Semaphore(1),
            _operation_id="declared-error", chunk_index=0, page_number=1,
            async_client=client,
            retry_config=RetryConfig("backoff", BackoffStrategy(1, 1, 1, 2), True),
            cache_tmp_data_feature=cached, temp_dir_path=str(tmp_path),
        )
    assert len(attempts) == 1
    assert response.status_code == status_code
    assert response.json() == body
    assert list(tmp_path.iterdir()) == []
