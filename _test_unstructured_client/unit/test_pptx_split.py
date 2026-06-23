from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path
from typing import Iterable, Optional
from unittest.mock import patch

import httpx
import pytest

from unstructured_client._hooks.custom import pptx_utils
from unstructured_client._hooks.custom.split_pdf_hook import (
    DEFAULT_CONCURRENCY_LEVEL,
    HI_RES_STRATEGY,
    SplitPdfHook,
    get_optimal_split_size,
)
from unstructured_client._hooks.types import BeforeRequestContext


# ---------------------------------------------------------------------------
# Synthetic .pptx builder
#
# The splitter only reads the OOXML package structure (presentation.xml,
# its rels, the per-slide rels, and [Content_Types].xml) — it never parses
# slide *content*. So a structurally-faithful package with placeholder XML
# bodies is enough to exercise every code path hermetically, without depending
# on a real PowerPoint file checked into the repo.
# ---------------------------------------------------------------------------

_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def build_synthetic_pptx(
    num_slides: int,
    notes_for: Optional[Iterable[int]] = None,
    rels_overrides: bool = False,
) -> bytes:
    """Build a minimal but structurally valid .pptx with ``num_slides`` slides.

    Args:
        num_slides: Number of slides to create.
        notes_for: 1-based slide numbers that should reference a notes slide.
        rels_overrides: If True, declare a ``<Override>`` content-type for every
            ``.rels`` part too (mirroring decks that don't rely solely on the
            ``<Default Extension="rels">`` rule). Exercises the override pruning.
    """
    notes = set(notes_for or ())
    parts: dict[str, bytes] = {}

    # Shared parts.
    parts["_rels/.rels"] = (
        f'<?xml version="1.0"?><Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
        f'<Relationship Id="rId1" Type="{_REL_NS}/officeDocument" Target="ppt/presentation.xml"/>'
        "</Relationships>"
    ).encode()
    parts["ppt/theme/theme1.xml"] = b"<theme/>"
    parts["ppt/media/image1.png"] = b"\x89PNG\r\n\x1a\nshared-image"
    parts["ppt/slideMasters/slideMaster1.xml"] = b"<sldMaster/>"
    parts["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = (
        f'<Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
        f'<Relationship Id="rId1" Type="{_REL_NS}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        f'<Relationship Id="rId2" Type="{_REL_NS}/theme" Target="../theme/theme1.xml"/>'
        "</Relationships>"
    ).encode()
    parts["ppt/slideLayouts/slideLayout1.xml"] = b"<sldLayout/>"
    parts["ppt/slideLayouts/_rels/slideLayout1.xml.rels"] = (
        f'<Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
        f'<Relationship Id="rId1" Type="{_REL_NS}/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
        "</Relationships>"
    ).encode()
    parts["ppt/notesMasters/notesMaster1.xml"] = b"<notesMaster/>"

    # Slides + their rels (+ optional notes).
    for n in range(1, num_slides + 1):
        parts[f"ppt/slides/slide{n}.xml"] = f"<sld n='{n}'/>".encode()
        slide_rels = [
            f'<Relationship Id="rId1" Type="{_REL_NS}/slideLayout" '
            'Target="../slideLayouts/slideLayout1.xml"/>',
            f'<Relationship Id="rId2" Type="{_REL_NS}/image" '
            'Target="../media/image1.png"/>',
        ]
        if n in notes:
            slide_rels.append(
                f'<Relationship Id="rId3" Type="{_REL_NS}/notesSlide" '
                f'Target="../notesSlides/notesSlide{n}.xml"/>'
            )
            parts[f"ppt/notesSlides/notesSlide{n}.xml"] = f"<notes n='{n}'/>".encode()
            parts[f"ppt/notesSlides/_rels/notesSlide{n}.xml.rels"] = (
                f'<Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
                f'<Relationship Id="rId1" Type="{_REL_NS}/notesMaster" '
                'Target="../notesMasters/notesMaster1.xml"/>'
                f'<Relationship Id="rId2" Type="{_REL_NS}/slide" '
                f'Target="../slides/slide{n}.xml"/>'
                "</Relationships>"
            ).encode()
        parts[f"ppt/slides/_rels/slide{n}.xml.rels"] = (
            f'<Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
            + "".join(slide_rels)
            + "</Relationships>"
        ).encode()

    # presentation.xml: master id list + slide id list (rId14.. for slides).
    sld_ids = "".join(
        f'<p:sldId id="{255 + n}" r:id="rId{13 + n}"/>' for n in range(1, num_slides + 1)
    )
    parts["ppt/presentation.xml"] = (
        '<?xml version="1.0"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        f'xmlns:r="{_REL_NS}">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId2"/></p:sldMasterIdLst>'
        f"<p:sldIdLst>{sld_ids}</p:sldIdLst>"
        '<p:sldSz cx="9144000" cy="6858000"/>'
        "</p:presentation>"
    ).encode()

    pres_rels = [
        f'<Relationship Id="rId1" Type="{_REL_NS}/theme" Target="theme/theme1.xml"/>',
        f'<Relationship Id="rId2" Type="{_REL_NS}/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
        f'<Relationship Id="rId3" Type="{_REL_NS}/notesMaster" Target="notesMasters/notesMaster1.xml"/>',
    ]
    for n in range(1, num_slides + 1):
        pres_rels.append(
            f'<Relationship Id="rId{13 + n}" Type="{_REL_NS}/slide" '
            f'Target="slides/slide{n}.xml"/>'
        )
    parts["ppt/_rels/presentation.xml.rels"] = (
        f'<Relationships xmlns="{_REL_NS.replace("officeDocument/2006", "package/2006")}">'
        + "".join(pres_rels)
        + "</Relationships>"
    ).encode()

    # [Content_Types].xml
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/notesMasters/notesMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/>',
    ]
    for n in range(1, num_slides + 1):
        overrides.append(
            f'<Override PartName="/ppt/slides/slide{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        if rels_overrides:
            overrides.append(
                f'<Override PartName="/ppt/slides/_rels/slide{n}.xml.rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            )
        if n in notes:
            overrides.append(
                f'<Override PartName="/ppt/notesSlides/notesSlide{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            )
    parts["[Content_Types].xml"] = (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + "".join(overrides)
        + "</Types>"
    ).encode()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        # [Content_Types].xml must be first per OPC convention.
        out.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
        for name, data in parts.items():
            out.writestr(name, data)
    return buffer.getvalue()


def _names(chunk: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(chunk)) as z:
        return set(z.namelist())


def _override_partnames(chunk: bytes) -> list[str]:
    import re

    with zipfile.ZipFile(io.BytesIO(chunk)) as z:
        ct = z.read("[Content_Types].xml").decode()
    return [p.lstrip("/") for p in re.findall(r'<Override PartName="([^"]+)"', ct)]


# ---------------------------------------------------------------------------
# Detection / counting
# ---------------------------------------------------------------------------


def test_is_pptx_true_for_pptx():
    assert pptx_utils.is_pptx(build_synthetic_pptx(3)) is True


def test_is_pptx_false_for_non_zip():
    assert pptx_utils.is_pptx(b"%PDF-1.7 not a zip") is False


def test_is_pptx_false_for_zip_without_presentation():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", b"<doc/>")
    assert pptx_utils.is_pptx(buf.getvalue()) is False


def test_is_pptx_accepts_binaryio():
    stream = io.BytesIO(build_synthetic_pptx(2))
    assert pptx_utils.is_pptx(stream) is True


def test_get_pptx_slide_count():
    assert pptx_utils.get_pptx_slide_count(build_synthetic_pptx(7)) == 7


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("num_slides", "split_size"),
    [(10, 3), (10, 5), (1, 2), (20, 20), (368, 20)],
)
def test_chunk_count_and_slide_totals(num_slides, split_size):
    content = build_synthetic_pptx(num_slides)
    chunks = pptx_utils.get_pptx_chunks_in_memory(content, split_size=split_size)

    assert len(chunks) == math.ceil(num_slides / split_size)

    total = 0
    for index, (buf, offset) in enumerate(chunks):
        chunk_bytes = buf.getvalue()
        count = pptx_utils.get_pptx_slide_count(chunk_bytes)
        expected = min(split_size, num_slides - index * split_size)
        assert count == expected
        assert offset == index * split_size
        total += count
    assert total == num_slides


def test_chunks_are_valid_zip_with_no_dangling_overrides():
    content = build_synthetic_pptx(10, rels_overrides=True)
    chunks = pptx_utils.get_pptx_chunks_in_memory(content, split_size=4)

    for buf, _ in chunks:
        chunk_bytes = buf.getvalue()
        names = _names(chunk_bytes)
        # Every content-type Override must point at a part that exists.
        for partname in _override_partnames(chunk_bytes):
            assert partname in names, f"dangling override: {partname}"


def test_chunks_retain_shared_parts_and_drop_other_slides():
    content = build_synthetic_pptx(10)
    chunks = pptx_utils.get_pptx_chunks_in_memory(content, split_size=4)

    first = chunks[0][0].getvalue()
    names = _names(first)
    # Shared parts retained.
    for shared_part in (
        "ppt/slideMasters/slideMaster1.xml",
        "ppt/slideLayouts/slideLayout1.xml",
        "ppt/theme/theme1.xml",
        "ppt/media/image1.png",
        "ppt/notesMasters/notesMaster1.xml",
    ):
        assert shared_part in names
    # Only this chunk's slides (1-4) are present.
    assert "ppt/slides/slide1.xml" in names
    assert "ppt/slides/slide4.xml" in names
    assert "ppt/slides/slide5.xml" not in names
    assert "ppt/slides/_rels/slide5.xml.rels" not in names


def test_notes_slides_follow_their_slides():
    # Slides 2 and 9 have notes.
    content = build_synthetic_pptx(10, notes_for={2, 9})
    chunks = pptx_utils.get_pptx_chunks_in_memory(content, split_size=4)

    # Chunk 0 = slides 1-4 -> keeps notesSlide2, drops notesSlide9.
    chunk0 = _names(chunks[0][0].getvalue())
    assert "ppt/notesSlides/notesSlide2.xml" in chunk0
    assert "ppt/notesSlides/notesSlide9.xml" not in chunk0

    # Chunk 2 = slides 9-10 -> keeps notesSlide9, not notesSlide2.
    chunk2 = _names(chunks[2][0].getvalue())
    assert "ppt/notesSlides/notesSlide9.xml" in chunk2
    assert "ppt/notesSlides/notesSlide2.xml" not in chunk2


def test_page_range_subsetting():
    content = build_synthetic_pptx(10)
    chunks = pptx_utils.get_pptx_chunks_in_memory(
        content, split_size=2, page_start=3, page_end=6
    )
    # Slides 3..6 inclusive -> 4 slides, 2 chunks of 2.
    assert len(chunks) == 2
    assert [offset for _, offset in chunks] == [2, 4]
    assert sum(pptx_utils.get_pptx_slide_count(b.getvalue()) for b, _ in chunks) == 4


def test_chunk_paths_writes_files(tmp_path):
    content = build_synthetic_pptx(7)
    tempdir, chunk_paths = pptx_utils.get_pptx_chunk_paths(
        content, cache_tmp_data_dir=str(tmp_path), split_size=3
    )
    try:
        assert len(chunk_paths) == 3
        for path, _offset in chunk_paths:
            assert Path(path).exists()
            assert pptx_utils.is_pptx(Path(path).read_bytes())
    finally:
        tempdir.cleanup()


# ---------------------------------------------------------------------------
# Hook gating
# ---------------------------------------------------------------------------


def _make_ctx() -> BeforeRequestContext:
    class _Config:
        timeout_ms = None
        retry_config = None

    ctx = BeforeRequestContext.__new__(BeforeRequestContext)
    ctx.operation_id = "partition"
    ctx.config = _Config()
    return ctx


def _run_before_request(strategy: str, split_pdf_page: str, num_slides: int = 30):
    hook = SplitPdfHook()
    hook.client = httpx.Client()
    content = build_synthetic_pptx(num_slides)
    form_data = {
        "files": {
            "filename": "deck.pptx",
            "content_type": pptx_utils.PPTX_CONTENT_TYPE,
            "file": io.BytesIO(content),
        },
        "split_pdf_page": split_pdf_page,
        "strategy": strategy,
    }
    request = httpx.Request(
        "POST",
        "http://localhost:8000/general/v0/general",
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )
    with patch(
        "unstructured_client._hooks.custom.split_pdf_hook.request_utils.get_multipart_stream_fields",
        return_value=form_data,
    ):
        result = hook.before_request(_make_ctx(), request)
    return hook, result


def _is_split(result) -> bool:
    return isinstance(result, httpx.Request) and result.url.path.endswith("/general/docs")


def test_hook_splits_pptx_for_hi_res():
    num_slides = 30
    hook, result = _run_before_request(HI_RES_STRATEGY, "true", num_slides=num_slides)
    assert _is_split(result)
    operation_id = result.headers["operation_id"]
    coros = hook.coroutines_to_execute[operation_id]

    # The hook reuses the PDF default split sizing.
    split_size = get_optimal_split_size(num_slides, DEFAULT_CONCURRENCY_LEVEL)
    assert len(coros) == math.ceil(num_slides / split_size)
    # Page numbers continue contiguously across chunks, starting at 1.
    page_numbers = [c.keywords["page_number"] for c in coros]
    assert page_numbers == list(range(1, num_slides + 1, split_size))
    hook._clear_operation(operation_id)


def test_hook_does_not_split_pptx_for_fast():
    _hook, result = _run_before_request("fast", "true")
    assert not _is_split(result)


def test_hook_does_not_split_pptx_when_flag_false():
    _hook, result = _run_before_request(HI_RES_STRATEGY, "false")
    assert not _is_split(result)


def test_hook_chunk_request_uses_pptx_content_type():
    hook, result = _run_before_request(HI_RES_STRATEGY, "true", num_slides=30)
    operation_id = result.headers["operation_id"]
    chunk_request = hook.coroutines_to_execute[operation_id][0].keywords[
        "pdf_chunk_request"
    ]
    body = chunk_request.read().decode("latin1")
    assert pptx_utils.PPTX_CONTENT_TYPE in body
    assert "deck.pptx" in body
    assert 'name="split_pdf_page"' in body
    hook._clear_operation(operation_id)
