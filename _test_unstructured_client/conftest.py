from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
import pytest

from unstructured_client.sdk import UnstructuredClient


@pytest.fixture(scope="module")
def client() -> Generator[UnstructuredClient, None, None]:
    _client = UnstructuredClient(api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"), server='free-api')
    yield _client


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return Path(__file__).resolve().parents[1] / "_sample_docs"
