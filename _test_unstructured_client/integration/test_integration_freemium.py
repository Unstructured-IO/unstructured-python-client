import os
from pathlib import Path

import pytest
import requests
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


@pytest.fixture(scope="module")
def client() -> UnstructuredClient:
    _client = UnstructuredClient(api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"))
    yield _client


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return Path(__file__).resolve().parents[2] / "_sample_docs"


@pytest.mark.parametrize("strategy", ["fast", "ocr_only", "hi_res"])
def test_partition_strategies(strategy, client, doc_path):
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
    )

    response = client.general.partition(req)
    assert response.status_code == 200
    assert len(response.elements)
