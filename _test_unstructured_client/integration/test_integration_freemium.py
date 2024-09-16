import asyncio
import json
import os
from pathlib import Path

import pytest
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError, ServerError, HTTPValidationError
from unstructured_client.utils.retries import BackoffStrategy, RetryConfig


@pytest.fixture(scope="module")
def client() -> UnstructuredClient:
    _client = UnstructuredClient(api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"), server='free-api')
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

    response = client.general.partition(request=req)
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
        response = client.general.partition(request=req)


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

        resp = client.general.partition(request=req)

        if resp is not None:
            return resp.elements
        else:
            return []

    import uvloop
    uvloop.install()
    elements = asyncio.run(call_api())
    assert len(elements) > 0
