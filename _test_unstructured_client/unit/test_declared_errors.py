import asyncio

import httpx
import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models.errors import (
    HTTPValidationError,
    HTTPValidationErrorData,
    SDKError,
    ServerError,
    ServerErrorData,
)
from unstructured_client.utils import BackoffStrategy, RetryConfig
from unstructured_client.utils.declared_errors import (
    DeclaredErrorFields,
    parse_declared_error_fields,
)

DECLARED_BODY = {
    "detail": "OCR timed out",
    "retryable": False,
    "error_type": "timeout",
    "error_reason": "ocr_timeout",
    "audience": "platform",
}
DECLARED_FIELDS = DeclaredErrorFields(
    retryable=False, error_type="timeout", error_reason="ocr_timeout", audience="platform"
)


def _response(status_code: int, **kwargs) -> httpx.Response:
    return httpx.Response(
        status_code,
        request=httpx.Request("POST", "http://test.invalid/general/v0/general"),
        **kwargs,
    )


def _declared(error) -> DeclaredErrorFields:
    return DeclaredErrorFields(
        retryable=error.retryable,
        error_type=error.error_type,
        error_reason=error.error_reason,
        audience=error.audience,
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ('{"detail":"x","retryable":false,"error_type":"timeout",'
         '"error_reason":"ocr_timeout","audience":"platform"}', DECLARED_FIELDS),
        ('{"retryable":true}', DeclaredErrorFields(retryable=True)),
        ('{"detail":"x","retryable":false,"audience":null}', DeclaredErrorFields(retryable=False)),
        ('{"detail":"Internal server error"}', DeclaredErrorFields()),
        ('{"retryable":"false","error_type":5,"error_reason":"  ","audience":[]}',
         DeclaredErrorFields()),
        ('{"retryable":0}', DeclaredErrorFields()),
        ('[{"retryable":false}]', DeclaredErrorFields()),
        ("false", DeclaredErrorFields()),
        ("{broken", DeclaredErrorFields()),
        ("upstream error", DeclaredErrorFields()),
        ("", DeclaredErrorFields()),
        (None, DeclaredErrorFields()),
        pytest.param(
            '{"retryable":false,"detail":' + "[" * 100_000 + "]" * 100_000 + "}",
            DeclaredErrorFields(),
            id="deeply-nested",
        ),
    ],
)
def test_parse_declared_error_fields(text, expected):
    assert parse_declared_error_fields(text) == expected


def test_server_error_exposes_declared_fields():
    response = _response(503, json=DECLARED_BODY)
    error = ServerError(ServerErrorData(detail="OCR timed out"), response)

    assert _declared(error) == DECLARED_FIELDS
    assert error.data.detail == "OCR timed out"


def test_sdk_error_exposes_declared_fields():
    response = _response(400, json=DECLARED_BODY)
    error = SDKError("API error occurred", response, response.text)

    assert _declared(error) == DECLARED_FIELDS


def test_http_validation_error_exposes_declared_fields():
    response = _response(422, json=DECLARED_BODY)
    error = HTTPValidationError(HTTPValidationErrorData(detail="OCR timed out"), response)

    assert _declared(error) == DECLARED_FIELDS


def test_explicit_body_takes_precedence_over_response_text():
    response = _response(500, json={"detail": "x"})
    error = SDKError("API error occurred", response, '{"retryable":false}')

    assert error.retryable is False


def test_undeclared_error_reads_none():
    response = _response(500, json={"detail": "Internal server error"})
    error = ServerError(ServerErrorData(detail="Internal server error"), response)

    assert _declared(error) == DeclaredErrorFields()


@pytest.mark.parametrize("async_mode", [False, True])
@pytest.mark.parametrize("status_code,error_class", [(400, SDKError), (503, ServerError)])
def test_public_partition_raises_declared_fields(async_mode, status_code, error_class):
    def respond(request):
        return httpx.Response(status_code, json=DECLARED_BODY)

    async def run():
        transport = httpx.MockTransport(respond)
        with httpx.Client(transport=transport) as client:
            async with httpx.AsyncClient(transport=transport) as async_client:
                sdk = UnstructuredClient(
                    server_url="http://test.invalid", client=client, async_client=async_client
                )
                request = {"partition_parameters": {
                    "files": {"content": b"hello", "file_name": "test.txt"},
                    "split_pdf_page": False,
                }}
                retries = RetryConfig("none", BackoffStrategy(1, 1, 1.0, 1), False)
                with pytest.raises(error_class) as exc:
                    if async_mode:
                        await sdk.general.partition_async(request=request, retries=retries)
                    else:
                        sdk.general.partition(request=request, retries=retries)
                return exc.value

    error = asyncio.run(run())
    assert _declared(error) == DECLARED_FIELDS
