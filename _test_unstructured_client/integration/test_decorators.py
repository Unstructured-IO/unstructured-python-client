import pytest
import requests
from deepdiff import DeepDiff
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import HTTPValidationError

FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


@pytest.mark.parametrize("concurrency_level", [1, 2, 5])
@pytest.mark.parametrize(
    ("filename", "expected_ok", "strategy"),
    [
        ("_sample_docs/list-item-example-1.pdf", True, "fast"),  # 1 page
        ("_sample_docs/layout-parser-paper-fast.pdf", True, "fast"),  # 2 pages
        # NOTE(mike): using "fast" strategy fails on this file for unknown reasons
        ("_sample_docs/layout-parser-paper.pdf", True, "hi_res"),  # 16 pages
        ("_sample_docs/fake.doc", False, "fast"),
        ("_sample_docs/emoji.xlsx", True, "fast"),
        ("_sample_docs/csv-with-long-lines.csv", False, "fast"),
        ("_sample_docs/ideas-page.html", False, "fast"),
    ],
)
def test_integration_split_pdf_has_same_output_as_non_split(
    concurrency_level: int, filename: str, expected_ok: bool, strategy: str, caplog
):
    """
    Tests that output that we get from the split-by-page pdf is the same as from non-split.

    Requires unstructured-api running in bg. See Makefile for how to run it.
    Doesn't check for raw_response as there's no clear patter for how it changes with the number of pages / concurrency_level.
    """
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY, server_url="localhost:8000")

    with open(filename, "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name=filename,
        )

    if not expected_ok:
        # This will append .pdf to filename to fool first line of filetype detection, to simulate decoding error
        files.file_name += ".pdf"

    req = shared.PartitionParameters(
        files=files,
        strategy=strategy,
        languages=["eng"],
        split_pdf_page=True,
        split_pdf_concurrency_level=concurrency_level,
    )

    try:
        resp_split = client.general.partition(req)
    except (HTTPValidationError, AttributeError) as exc:
        if not expected_ok:
            assert "The file does not appear to be a valid PDF." in caplog.text
            assert "File does not appear to be a valid PDF" in str(exc)
            return
        else:
            assert exc is None

    req.split_pdf_page = False
    resp_single = client.general.partition(req)

    assert len(resp_split.elements) == len(resp_single.elements)
    assert resp_split.content_type == resp_single.content_type
    assert resp_split.status_code == resp_single.status_code

    diff = DeepDiff(
        t1=resp_split.elements,
        t2=resp_single.elements,
        exclude_regex_paths=[
            r"root\[\d+\]\['metadata'\]\['parent_id'\]",
        ],
    )
    assert len(diff) == 0


def test_integration_split_pdf_for_file_with_no_name():
    """
    Tests that the client raises an error when the file_name is empty.
    """
    try:
        response = requests.get("http://localhost:8000/general/docs")
        assert response.status_code == 200, "The unstructured-api is not running on localhost:8000"
    except requests.exceptions.ConnectionError:
        assert False, "The unstructured-api is not running on localhost:8000"

    client = UnstructuredClient(api_key_auth=FAKE_KEY, server_url="localhost:8000")

    with open("_sample_docs/layout-parser-paper-fast.pdf", "rb") as f:
        files = shared.Files(
            content=f.read(),
            file_name="    ",
        )

    req = shared.PartitionParameters(
        files=files,
        strategy="fast",
        languages=["eng"],
        split_pdf_page=True,
    )

    pytest.raises(ValueError, client.general.partition, req)
