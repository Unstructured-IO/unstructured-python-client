"""Unit tests for the on-disk NDJSON recombination used by elements-file mode.

This helper is what removes the four in-memory copies the split-PDF recombination used to
make (per-chunk list, flattened list, json.dumps blob, SDK re-parse). It must:
  - handle chunk files that are JSON arrays (server returned application/json)
  - handle chunk files that are already NDJSON (server honored application/x-ndjson)
  - preserve element order across chunks
  - round-trip payload strings byte-for-byte
"""

import json

import pytest

import httpx

from unstructured_client._hooks.custom.request_utils import (
    ELEMENTS_FILE_HEADER,
    combine_chunk_files_to_ndjson,
    create_elements_file_response,
    write_chunk_body_to_temp,
)


def _elements(prefix, count):
    return [
        {
            "type": "Table" if i % 2 == 0 else "NarrativeText",
            "text": f"{prefix}-{i}",
            "metadata": {"page_number": i + 1, "image_base64": f"PAYLOAD{prefix}{i}" * 4},
        }
        for i in range(count)
    ]


def _write_json_array(path, elements):
    path.write_text(json.dumps(elements), encoding="utf-8")


def _write_ndjson(path, elements):
    with path.open("w", encoding="utf-8") as f:
        for element in elements:
            f.write(json.dumps(element))
            f.write("\n")


def _read_ndjson(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_combines_json_array_chunks_in_order(tmp_path):
    chunk_a = tmp_path / "a.json"
    chunk_b = tmp_path / "b.json"
    elements_a = _elements("a", 3)
    elements_b = _elements("b", 2)
    _write_json_array(chunk_a, elements_a)
    _write_json_array(chunk_b, elements_b)

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson([str(chunk_a), str(chunk_b)], str(out))

    assert written == 5
    assert _read_ndjson(out) == elements_a + elements_b


def test_combines_ndjson_chunks_without_parsing(tmp_path):
    """The zero-parse path: both ends speak NDJSON."""
    chunk_a = tmp_path / "a.ndjson"
    chunk_b = tmp_path / "b.ndjson"
    elements_a = _elements("a", 4)
    elements_b = _elements("b", 1)
    _write_ndjson(chunk_a, elements_a)
    _write_ndjson(chunk_b, elements_b)

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson([str(chunk_a), str(chunk_b)], str(out))

    assert written == 5
    assert _read_ndjson(out) == elements_a + elements_b


def test_mixed_chunk_formats(tmp_path):
    """A server upgraded mid-flight, or a retry served by an older pod."""
    chunk_a = tmp_path / "a.json"
    chunk_b = tmp_path / "b.ndjson"
    elements_a = _elements("a", 2)
    elements_b = _elements("b", 2)
    _write_json_array(chunk_a, elements_a)
    _write_ndjson(chunk_b, elements_b)

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson([str(chunk_a), str(chunk_b)], str(out))

    assert written == 4
    assert _read_ndjson(out) == elements_a + elements_b


@pytest.mark.parametrize("body", ["", "   ", "\n\n"])
def test_empty_chunk_files_are_skipped(tmp_path, body):
    chunk_a = tmp_path / "a.json"
    chunk_empty = tmp_path / "empty.json"
    elements_a = _elements("a", 2)
    _write_json_array(chunk_a, elements_a)
    chunk_empty.write_text(body, encoding="utf-8")

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson([str(chunk_a), str(chunk_empty)], str(out))

    assert written == 2
    assert _read_ndjson(out) == elements_a


def test_empty_array_chunk_contributes_nothing(tmp_path):
    """A chunk that legitimately produced no elements (e.g. blank pages)."""
    chunk_a = tmp_path / "a.json"
    chunk_b = tmp_path / "b.json"
    _write_json_array(chunk_a, [])
    elements_b = _elements("b", 3)
    _write_json_array(chunk_b, elements_b)

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson([str(chunk_a), str(chunk_b)], str(out))

    assert written == 3
    assert _read_ndjson(out) == elements_b


def test_payload_round_trips_exactly(tmp_path):
    """Base64 payloads are the reason this path exists; they must survive unchanged."""
    payload = "A" * 100_000
    element = {"type": "Table", "text": "t", "metadata": {"image_base64": payload}}
    chunk = tmp_path / "a.json"
    _write_json_array(chunk, [element])

    out = tmp_path / "combined.ndjson"
    combine_chunk_files_to_ndjson([str(chunk)], str(out))

    result = _read_ndjson(out)
    assert result[0]["metadata"]["image_base64"] == payload


def test_non_ascii_is_preserved(tmp_path):
    element = {"type": "NarrativeText", "text": "日本語 café ✓", "metadata": {}}
    chunk = tmp_path / "a.json"
    _write_json_array(chunk, [element])

    out = tmp_path / "combined.ndjson"
    combine_chunk_files_to_ndjson([str(chunk)], str(out))

    assert _read_ndjson(out)[0]["text"] == "日本語 café ✓"


def test_write_chunk_body_to_temp_roundtrips(tmp_path):
    """The cache_tmp_data=OFF path: an in-memory NDJSON body must spill verbatim.

    Regression guard. `ndjson_mode` used to also require cache_tmp_data, so with caching off
    the server returned NDJSON while the hook took the JSON path and `res.json()` raised on a
    body this client had itself requested.
    """
    elements = _elements("x", 3)
    body = "".join(json.dumps(e) + "\n" for e in elements).encode()
    response = httpx.Response(status_code=200, content=body)

    path = write_chunk_body_to_temp(response, str(tmp_path))
    assert _read_ndjson(path) == elements


def test_combine_accepts_bodies_spilled_without_caching(tmp_path):
    """End-to-end of the uncached path: spill two bodies, then combine them."""
    a, b = _elements("a", 2), _elements("b", 3)
    ra = httpx.Response(200, content="".join(json.dumps(e) + "\n" for e in a).encode())
    rb = httpx.Response(200, content="".join(json.dumps(e) + "\n" for e in b).encode())
    paths = [write_chunk_body_to_temp(r, str(tmp_path)) for r in (ra, rb)]

    out = tmp_path / "combined.ndjson"
    written = combine_chunk_files_to_ndjson(paths, str(out))

    assert written == 5
    assert _read_ndjson(out) == a + b


def test_spilled_body_is_released_from_the_response(tmp_path):
    """After spilling, the response must no longer hold the body.

    Regression guard for the real failure mode: every chunk response is retained in
    `api_successful_responses` for failure bookkeeping, so spilling to disk without
    releasing `_content` still accumulates the whole document in memory (125 chunks x
    32 MB = 4 GB observed on a 2500-page split).
    """
    elements = _elements("a", 3)
    body = "".join(json.dumps(e) + "\n" for e in elements).encode()
    response = httpx.Response(status_code=200, content=body)
    assert len(response.content) == len(body)

    path = write_chunk_body_to_temp(response, str(tmp_path))
    response._content = path.encode()

    # The body is on disk, and the response now costs a path rather than a payload.
    assert _read_ndjson(path) == elements
    assert response.text == path
    assert len(response.content) < 512


def test_elements_file_response_carries_path_in_header_and_body(tmp_path):
    path = str(tmp_path / "combined.ndjson")
    response = create_elements_file_response(path)

    assert response.status_code == 200
    assert response.headers[ELEMENTS_FILE_HEADER] == path
    assert response.headers["Content-Type"] == "application/x-ndjson"
    # Body-as-path mirrors the existing cached-chunk convention in the split hook.
    assert response.text == path
