from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import time

from deepdiff import DeepDiff
import pytest
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError, ServerError, HTTPValidationError
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig


FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
LOCAL_API_URL = "http://localhost:8000"
logger = logging.getLogger("integration.split_pdf")


def _log_integration_progress(event: str, **fields) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"integration event={event} {rendered_fields}", flush=True)
    logger.info("integration event=%s %s", event, rendered_fields)


@pytest.fixture(scope="function")
def client() -> UnstructuredClient:
    _client = UnstructuredClient(
        api_key_auth=os.getenv("UNSTRUCTURED_API_KEY") or FAKE_KEY,
        server_url=os.getenv("UNSTRUCTURED_SERVER_URL") or LOCAL_API_URL,
        timeout_ms=120_000,
    )
    yield _client


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return Path(__file__).resolve().parents[2] / "_sample_docs"


@pytest.mark.parametrize("split_pdf", [True, False])
@pytest.mark.parametrize("strategy", ["fast", "ocr_only", "hi_res"])
def test_partition_strategies(split_pdf, strategy, client, doc_path):
    filename = "layout-parser-paper-fast.pdf"
    with open(doc_path / filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy=strategy,
            languages=["eng"],
            split_pdf_page=split_pdf,
        )
    )

    case_context = f"test=partition_strategies file={filename} strategy={strategy} split_pdf={split_pdf}"
    _log_integration_progress("partition_start", case_context=case_context)
    started_at = time.perf_counter()
    response = client.general.partition(
        request=req
    )
    _log_integration_progress(
        "partition_complete",
        case_context=case_context,
        status_code=response.status_code,
        element_count=len(response.elements),
        elapsed_ms=round((time.perf_counter() - started_at) * 1000),
    )
    assert response.status_code == 200
    assert len(response.elements)


@pytest.mark.parametrize("split_pdf", [True, False])
@pytest.mark.parametrize("error", [(500, ServerError), (403, SDKError), (422, HTTPValidationError)])
def test_partition_handling_server_error(error, split_pdf, monkeypatch, doc_path):
    """
    Mock different error responses, assert that the client throws the correct error
    """
    filename = "layout-parser-paper-fast.pdf"
    import httpx

    error_code, sdk_raises = error

    # Create the mock response
    json_data = {"detail": "An error occurred"}
    response = httpx.Response(
        status_code=error_code,
        headers={'Content-Type': 'application/json'},
        content=json.dumps(json_data),
        request=httpx.Request("POST", "http://mock-request"),
    )

    monkeypatch.setattr(httpx.AsyncClient, "send", lambda *args, **kwargs: response)
    monkeypatch.setattr(httpx.Client, "send", lambda *args, **kwargs: response)

    # initialize client after patching
    client = UnstructuredClient(
        api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"),
        retry_config=RetryConfig("backoff", BackoffStrategy(1, 10, 1.5, 30), False),
    )

    with open(doc_path / filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy="fast",
            languages=["eng"],
            split_pdf_page=split_pdf,
        )
    )

    with pytest.raises(sdk_raises):
        response = client.general.partition(
            request=req
        )


@pytest.mark.asyncio
async def test_partition_async_returns_elements(client, doc_path):
    filename = "layout-parser-paper.pdf"
    with open(doc_path / filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy="fast",
            languages=["eng"],
            split_pdf_page=True,
        )
    )

    _log_integration_progress("partition_async_start", file=filename, strategy="fast", split_pdf=True)
    started_at = time.perf_counter()
    response = await client.general.partition_async(request=req)
    _log_integration_progress(
        "partition_async_complete",
        file=filename,
        strategy="fast",
        status_code=response.status_code,
        element_count=len(response.elements),
        elapsed_ms=round((time.perf_counter() - started_at) * 1000),
    )
    assert response.status_code == 200
    assert len(response.elements)


@pytest.mark.asyncio
async def test_partition_async_processes_concurrent_files(client, doc_path):
    """
    Assert that partition_async can be used to send multiple files concurrently.
    Send two page ranges serially and then via asyncio.gather.
    Both execution modes should return the same payloads.
    """
    filename = "layout-parser-paper.pdf"

    with open(doc_path / filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    requests = [
        operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy="fast",
                languages=["eng"],
                split_pdf_page=True,
                split_pdf_page_range=[1, 3],
            )
        ),
        operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy="fast",
                languages=["eng"],
                split_pdf_page=True,
                split_pdf_page_range=[10, 12],
            )
        )
    ]

    serial_results = []
    _log_integration_progress("partition_async_serial_start", request_count=len(requests), file=filename)
    for req in requests:
        started_at = time.perf_counter()
        res = await client.general.partition_async(request=req)
        assert res.status_code == 200
        serial_results.append(res.elements)
        _log_integration_progress(
            "partition_async_serial_complete",
            status_code=res.status_code,
            element_count=len(res.elements),
            elapsed_ms=round((time.perf_counter() - started_at) * 1000),
        )

    _log_integration_progress("partition_async_concurrent_start", request_count=len(requests), file=filename)
    started_at = time.perf_counter()
    results = await asyncio.gather(
        client.general.partition_async(request=requests[0]),
        client.general.partition_async(request=requests[1])
    )
    _log_integration_progress(
        "partition_async_concurrent_complete",
        request_count=len(results),
        elapsed_ms=round((time.perf_counter() - started_at) * 1000),
    )

    concurrent_results = []
    for res in results:
        assert res.status_code == 200
        concurrent_results.append(res.elements)

    diff = DeepDiff(
        t1=serial_results,
        t2=concurrent_results,
        ignore_order=True,
    )
    assert len(diff) == 0


def test_uvloop_partitions_without_errors(client, doc_path):
    """Test that we can use pdf splitting within another asyncio loop."""
    filename = "layout-parser-paper-fast.pdf"

    async def call_api():
        with open(doc_path / filename, "rb") as f:
            files = shared.Files(
                content=f.read(),
                file_name=filename,
            )

        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy="fast",
                languages=["eng"],
                split_pdf_page=True,
            )
        )

        resp = client.general.partition(
            request=req
        )

        if resp is not None:
            return resp.elements
        else:
            return []

    import uvloop
    started_at = time.perf_counter()
    elements = uvloop.run(call_api())
    _log_integration_progress(
        "uvloop_partition_complete",
        file=filename,
        element_count=len(elements),
        elapsed_ms=round((time.perf_counter() - started_at) * 1000),
    )
    assert len(elements) > 0


def test_returns_422_for_invalid_pdf(
    caplog: pytest.LogCaptureFixture,
    doc_path: Path,
    client: UnstructuredClient,
):
    """Test that we get a RequestError with the correct error message for invalid PDF files."""
    pdf_name = "failing-invalid.pdf"
    with open(doc_path / pdf_name, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=pdf_name,
        )

    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=files,
            strategy="fast",
            split_pdf_page=True,
        )
    )

    with pytest.raises(HTTPValidationError):
        client.general.partition(request=req)

    assert "File does not appear to be a valid PDF" in caplog.text
    assert "422" in caplog.text
