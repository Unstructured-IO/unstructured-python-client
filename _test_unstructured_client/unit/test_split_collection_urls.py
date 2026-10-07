import asyncio
import io

import httpx
import pytest
from pypdf import PdfWriter

from unstructured_client import UnstructuredClient
from unstructured_client._hooks.custom.split_pdf_hook import _get_collection_url
from unstructured_client.models import operations, shared
from unstructured_client.utils import BackoffStrategy, RetryConfig


PREFIXES = [
    "",
    "/deployment",
    "/one/two",
    "/general/v0/general/deployment",
    "/encoded%2Fprefix",
]


@pytest.fixture
def pdf_bytes():
    document = PdfWriter()
    for _ in range(4):
        document.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    document.write(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize("prefix", PREFIXES)
def test_collection_url_preserves_encoded_prefix_and_replaces_terminal_route(prefix):
    url = httpx.URL(
        f"https://local.invalid{prefix}/general/v0/general?strategy=fast#fragment"
    )
    assert (
        str(_get_collection_url(url)) == f"https://local.invalid{prefix}/general/docs"
    )


def make_sdk(monkeypatch, prefix, override):
    sent = []

    def respond(request):
        sent.append((request.method, str(request.url)))
        return httpx.Response(200, json=[{"text": "hello"}], request=request)

    transport = httpx.MockTransport(respond)
    original_async_client = httpx.AsyncClient
    sync_client = httpx.Client(transport=transport)
    async_client = original_async_client(transport=transport)
    sdk = UnstructuredClient(
        server_url="http://unused.invalid"
        if override
        else f"http://local.invalid{prefix}",
        client=sync_client,
        async_client=async_client,
    )
    # Split chunks create their own async HTTP client; keep every request offline.
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )
    return sdk, sent, sync_client, async_client


def request(pdf_bytes, split):
    return operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(content=pdf_bytes, file_name="test.pdf"),
            split_pdf_page=split,
        )
    )


def assert_routes(sent, prefix, split):
    partition = f"http://local.invalid{prefix}/general/v0/general"
    if split:
        assert sent[0] == ("GET", f"http://local.invalid{prefix}/general/docs")
        assert len(sent) == 3
        assert sent[1:] == [("POST", partition)] * 2
    else:
        assert sent == [("POST", partition)]


@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("override", [False, True])
@pytest.mark.parametrize("split", [False, True])
def test_public_sync_sdk_preserves_deployment_routes(
    monkeypatch, pdf_bytes, prefix, override, split
):
    sdk, sent, sync_client, async_client = make_sdk(monkeypatch, prefix, override)
    result = sdk.general.partition(
        request=request(pdf_bytes, split),
        server_url=f"http://local.invalid{prefix}" if override else None,
        retries=RetryConfig("none", BackoffStrategy(1, 1, 1, 1), False),
    )
    assert result.status_code == 200
    assert_routes(sent, prefix, split)
    sync_client.close()
    asyncio.run(async_client.aclose())


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("override", [False, True])
@pytest.mark.parametrize("split", [False, True])
async def test_public_async_sdk_preserves_deployment_routes(
    monkeypatch, pdf_bytes, prefix, override, split
):
    sdk, sent, sync_client, async_client = make_sdk(monkeypatch, prefix, override)
    result = await sdk.general.partition_async(
        request=request(pdf_bytes, split),
        server_url=f"http://local.invalid{prefix}" if override else None,
        retries=RetryConfig("none", BackoffStrategy(1, 1, 1, 1), False),
    )
    assert result.status_code == 200
    assert_routes(sent, prefix, split)
    sync_client.close()
    await async_client.aclose()
