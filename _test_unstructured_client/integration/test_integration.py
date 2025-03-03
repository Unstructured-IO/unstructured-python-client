from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest
from deepdiff import DeepDiff
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError, ServerError, HTTPValidationError
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig


@pytest.fixture(scope="module")
def client() -> UnstructuredClient:
    _client = UnstructuredClient(api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"))
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

    response = client.general.partition(
        request=req
    )
    assert response.status_code == 200
    assert len(response.elements)


@pytest.fixture(scope="session")
def event_loop():
    """Make the loop session scope to use session async fixtures."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.parametrize("split_pdf", [True, False])
@pytest.mark.parametrize("error", [(500, ServerError), (403, SDKError), (422, HTTPValidationError)])
def test_partition_handling_server_error(error, split_pdf, monkeypatch, doc_path, event_loop):
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

    response = await client.general.partition_async(request=req)
    assert response.status_code == 200
    assert len(response.elements)


@pytest.mark.asyncio
async def test_partition_async_processes_concurrent_files(client, doc_path):
    """
    Assert that partition_async can be used to send multiple files concurrently.
    Send two separate portions of the test doc, serially and then using asyncio.gather.
    The results for both runs should match.
    """
    filename = "layout-parser-paper.pdf"

    with open(doc_path / filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    # Set up two SDK requests
    # For different page ranges
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

    serial_responses = []
    for req in requests:
        res = await client.general.partition_async(request=req)

        assert res.status_code == 200
        serial_responses.append(res.elements)

    concurrent_responses = []
    results = await asyncio.gather(
        client.general.partition_async(request=requests[0]),
        client.general.partition_async(request=requests[1])
    )

    for res in results:
        assert res.status_code == 200
        concurrent_responses.append(res.elements)

    diff = DeepDiff(
        t1=serial_responses,
        t2=concurrent_responses,
        ignore_order=True,
    )

    assert len(diff) == 0


def test_uvloop_partitions_without_errors(client, doc_path):
    async def call_api():
        filename = "layout-parser-paper-fast.pdf"
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
    uvloop.install()
    elements = asyncio.run(call_api())
    assert len(elements) > 0
