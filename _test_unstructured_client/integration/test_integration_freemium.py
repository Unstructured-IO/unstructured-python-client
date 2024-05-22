import os
from pathlib import Path

import pytest
import requests
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.utils.retries import RetryConfig, BackoffStrategy
from unstructured_client.models.errors.sdkerror import SDKError


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

    req = shared.PartitionParameters(
        files=files,
        strategy=strategy,
        languages=["eng"],
        split_pdf_page=split_pdf,
    )

    response = client.general.partition(req)
    assert response.status_code == 200
    assert len(response.elements)


@pytest.mark.parametrize("split_pdf", [True, False])
@pytest.mark.parametrize("error_code", [500, 403])
def test_partition_handling_server_error(error_code, split_pdf,monkeypatch, doc_path):
    filename = "layout-parser-paper-fast.pdf"
    from unstructured_client.sdkconfiguration import requests_http

    response = requests_http.Response()
    response.status_code = error_code
    monkeypatch.setattr(requests_http.Session, "send", lambda *args, **kwargs: response)

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

    req = shared.PartitionParameters(
        files=files,
        strategy="fast",
        languages=["eng"],
        split_pdf_page=split_pdf,
    )

    with pytest.raises(SDKError, match=f"API error occurred: Status {error_code}"):
        response = client.general.partition(req)

