"""Unit tests for NDJSON elements-file mode.

The on-disk recombination replaces the four in-memory copies the split-PDF path used to
make (per-chunk list, flattened list, json.dumps blob, SDK re-parse). It must:
  - handle chunk files that are JSON arrays (server returned application/json)
  - handle chunk files that are already NDJSON (server honored application/x-ndjson)
  - preserve element order across chunks
  - round-trip payload strings byte-for-byte
  - leave no temp files behind other than the combined file the caller owns
"""

import json
import os
from pathlib import Path

import pytest

import httpx

from unstructured_client._hooks.custom.request_utils import (
    ELEMENTS_FILE_EXTENSION_KEY,
    combine_chunk_files_to_ndjson,
    create_elements_file_response,
    write_chunk_body_to_temp,
)
from unstructured_client._hooks.custom.split_pdf_hook import SplitPdfHook
from unstructured_client.general import _ndjson_elements_file


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

    Regression guard: every chunk response is retained in `api_successful_responses` for
    failure bookkeeping, so spilling to disk without releasing `_content` still
    accumulates the whole document in memory, defeating the point of spilling.
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


def test_elements_file_response_carries_path_in_extension_and_body(tmp_path):
    path = str(tmp_path / "combined.ndjson")
    response = create_elements_file_response(path)

    assert response.status_code == 200
    assert response.extensions[ELEMENTS_FILE_EXTENSION_KEY] == path
    assert response.headers["Content-Type"] == "application/x-ndjson"
    # Body-as-path mirrors the existing cached-chunk convention in the split hook.
    assert response.text == path


def test_server_cannot_name_a_local_file_via_a_response_header(tmp_path):
    """The elements-file marker must not be reachable from the wire.

    Callers are documented to open `elements_file` and then delete it, so trusting a
    server-supplied path would hand a hostile server an arbitrary local file to destroy.
    A header must be ignored and the body copied to a file this client created.
    """
    victim = tmp_path / "victim"
    victim.write_text("do not touch", encoding="utf-8")
    response = httpx.Response(
        200,
        headers={
            "content-type": "application/x-ndjson",
            "x-unstructured-elements-file": str(victim),
        },
        content=b'{"safe": true}\n',
    )

    resolved = _ndjson_elements_file(response)

    assert resolved != str(victim)
    assert victim.read_text(encoding="utf-8") == "do not touch"
    assert _read_ndjson(resolved) == [{"safe": True}]
    os.unlink(resolved)


# --- hook-level temp-file lifecycle ------------------------------------------------


def _ndjson_response(elements):
    body = "".join(json.dumps(e) + "\n" for e in elements).encode()
    return httpx.Response(status_code=200, content=body)


def _hook_in_ndjson_mode(operation_id, tmp_path):
    """A hook set up as `before_request` would leave it for an uncached NDJSON run."""
    hook = SplitPdfHook()
    hook.ndjson_mode[operation_id] = True
    hook.cache_tmp_data_feature[operation_id] = False
    hook.cache_tmp_data_dir[operation_id] = str(tmp_path)
    hook.allow_failed[operation_id] = False
    return hook


def _ndjson_files_in(directory):
    return sorted(p.name for p in Path(directory).glob("*.ndjson"))


def test_spilled_chunk_files_are_deleted_after_combining(tmp_path):
    """Regression guard: spilled chunks used to be left in the temp dir forever.

    `cache_tmp_data` defaults to off, so this is the default path. One file per chunk
    accumulating for the lifetime of the host is a disk leak, not a memory one.
    """
    operation_id = "op-cleanup"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)
    responses = [(0, _ndjson_response(_elements("a", 2))), (1, _ndjson_response(_elements("b", 3)))]

    hook._elements_from_task_responses(operation_id, responses, started_at=0.0)

    combined = hook.ndjson_output_path[operation_id]
    # Exactly one file survives: the combined output the caller owns.
    assert _ndjson_files_in(tmp_path) == [Path(combined).name]
    assert len(_read_ndjson(combined)) == 5


def test_spilled_chunks_land_in_the_operation_tempdir_when_one_exists(tmp_path):
    """Spilling into the operation's tempdir means cleanup happens even if we miss it."""
    operation_id = "op-tempdir"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)
    operation_dir = tmp_path / "unstructured_client_op"
    operation_dir.mkdir()

    class _FakeTempDir:
        name = str(operation_dir)

    hook.tempdirs[operation_id] = _FakeTempDir()  # type: ignore[assignment]
    spill_dir = hook._operation_tempdir_path(operation_id)

    assert spill_dir == str(operation_dir)


def test_combined_file_is_returned_on_success(tmp_path):
    operation_id = "op-success"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)
    elements = _elements("a", 4)

    hook._elements_from_task_responses(
        operation_id, [(0, _ndjson_response(elements))], started_at=0.0
    )
    response = hook._build_after_success_response(operation_id, httpx.Response(200), [])

    combined = response.extensions[ELEMENTS_FILE_EXTENSION_KEY]
    assert os.path.exists(combined)
    assert _read_ndjson(combined) == elements


def test_combined_file_is_discarded_when_a_failure_response_is_returned(tmp_path):
    """Regression guard: on the failure path nothing downstream learns the path.

    `_build_after_success_response` returns the failed chunk response instead, so the
    combined file would be leaked for the lifetime of the host.
    """
    operation_id = "op-strict-failure"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)
    responses = [
        (0, _ndjson_response(_elements("a", 2))),
        (1, httpx.Response(status_code=500, content=b"boom")),
    ]

    hook._elements_from_task_responses(operation_id, responses, started_at=0.0)
    combined = hook.ndjson_output_path[operation_id]
    assert os.path.exists(combined)

    response = hook._build_after_success_response(operation_id, httpx.Response(200), [])

    assert response.status_code == 500
    assert not os.path.exists(combined)
    assert _ndjson_files_in(tmp_path) == []


def test_malformed_chunk_leaves_no_partial_output_behind(tmp_path):
    """Regression guard: recombination that raises must not orphan a partial file.

    The combined file is the one artifact here that no temp directory owns, so a partial
    one would outlive the failed operation.
    """
    operation_id = "op-malformed"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)

    with pytest.raises(json.JSONDecodeError):
        hook._elements_from_task_responses(
            operation_id, [(0, httpx.Response(200, content=b"[not-json"))], started_at=0.0
        )

    assert operation_id not in hook.ndjson_output_path
    assert _ndjson_files_in(tmp_path) == []
    assert list(Path(tmp_path).glob("*.partial")) == []


def test_no_combined_file_is_created_when_every_chunk_failed(tmp_path):
    operation_id = "op-all-failed"
    hook = _hook_in_ndjson_mode(operation_id, tmp_path)
    responses = [(0, httpx.Response(status_code=500, content=b"boom"))]

    hook._elements_from_task_responses(operation_id, responses, started_at=0.0)

    assert operation_id not in hook.ndjson_output_path
    assert _ndjson_files_in(tmp_path) == []
