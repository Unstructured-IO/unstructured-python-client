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

from unstructured_client._hooks.custom.request_utils import (
    ELEMENTS_FILE_HEADER,
    combine_chunk_files_to_ndjson,
    create_elements_file_response,
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


def test_elements_file_response_carries_path_in_header_and_body(tmp_path):
    path = str(tmp_path / "combined.ndjson")
    response = create_elements_file_response(path)

    assert response.status_code == 200
    assert response.headers[ELEMENTS_FILE_HEADER] == path
    assert response.headers["Content-Type"] == "application/x-ndjson"
    # Body-as-path mirrors the existing cached-chunk convention in the split hook.
    assert response.text == path
