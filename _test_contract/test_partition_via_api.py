from pathlib import Path

import httpx
import pytest
from unstructured.partition.api import partition_via_api


@pytest.mark.xfail
@pytest.mark.parametrize(
    ("url", "full_url"), [
        ("http://localhost:8000", "http://localhost:8000/general/v0/general"),
        ("http://localhost:8000/general/v0/general", "http://localhost:8000/general/v0/general"),
    ]
)
def test_partition_via_api_custom_url(
    httpx_mock,
    doc_path: Path,
    url: str,
    full_url: str,
    dummy_partitioned_text: str
):
    """
    Assert that we can specify api_url and requests are sent to the right place
    """

    filename = "layout-parser-paper-fast.pdf"

    # adding response automatically checks whether a response to a request to given URL was found
    httpx_mock.add_response(
        method="POST",
        url=full_url,
        headers={"Content-Type": "application/json"},
        content=dummy_partitioned_text.encode(),
    )

    partition_via_api(filename=str(doc_path / filename), api_url=url, metadata_filename=filename)


@pytest.mark.xfail
def test_partition_via_api_pass_list_type_parameters(
    httpx_mock,
    doc_path: Path,
    dummy_partitioned_text: str
):
    url = "http://localhost:8000/general/v0/general"
    filename = "layout-parser-paper-fast.pdf"

    httpx_mock.add_response(
        method="POST",
        headers={"Content-Type": "application/json"},
        content=dummy_partitioned_text.encode(),
        url=url,
    )

    params = dict(
        split_pdf_page=False,
        strategy="hi_res",
        extract_image_block_types=["image", "table"],
        skip_infer_table_types=["pdf", "docx"],
        languages=["eng"],
    )

    partition_via_api(filename=str(doc_path / filename),
                      api_url=url,
                      metadata_filename=filename,
                      **params)

    requests = httpx_mock.get_requests()

    assert len(requests) == 1

    request = requests[0]

    parsed_multipart_form = _parse_multipart_data(request)
    assert "coordinates" in parsed_multipart_form
    for key, value in params.items():
        assert key in parsed_multipart_form
        assert parsed_multipart_form[key] == value


def _parse_multipart_data(request: httpx.Request) -> dict:
    """Parser for multipart form data in raw format to a dictionary. Ommits "files" field
    Includes table-like entries.
    """
    data = request.content
    boundary = request.headers["Content-Type"].split("boundary=")[1]
    parts = data.split(f"--{boundary}".encode())
    parts = [part.strip() for part in parts if part.strip()]
    parsed_data = {}
    for part in parts:
        if b"Content-Disposition: form-data" in part:
            try:
                semicolon_pos = part.find(b";")
                contents = part[semicolon_pos + 2:]
                if b"name=\"files\"" in contents:
                    continue
                contents = contents.decode()
                key, value = contents.split("\r\n\r\n")
                key = key.replace("name=", "").strip('"')
                if "[]" in key:
                    key = key.replace("[]", "")
                    if key not in parsed_data:
                        parsed_data[key] = []
                    parsed_data[key].append(value)
                elif value in ["true", "false"]:
                    parsed_data[key] = value == "true"
                else:
                    parsed_data[key] = value
            except Exception as ex:
                print(ex)
    return parsed_data
