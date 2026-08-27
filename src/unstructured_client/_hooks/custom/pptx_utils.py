from __future__ import annotations

import io
import logging
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from typing import BinaryIO, Generator, Optional, Tuple, Union

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.validation_errors import FileValidationError

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

PPTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)

# Canonical OOXML package part names for a PresentationML package.
_PRESENTATION_PART = "ppt/presentation.xml"
_PRESENTATION_RELS_PART = "ppt/_rels/presentation.xml.rels"
_CONTENT_TYPES_PART = "[Content_Types].xml"

# A slide id entry in presentation.xml, e.g. <p:sldId id="256" r:id="rId14"/>
_SLD_ID_RE = re.compile(rb"<p:sldId\b[^>]*?/>")
# A relationship entry in a .rels part, e.g.
# <Relationship Id="rId14" Type=".../slide" Target="slides/slide1.xml"/>
_RELATIONSHIP_RE = re.compile(rb"<Relationship\b[^>]*?/>")
# A content-types Override entry, e.g.
# <Override PartName="/ppt/slides/slide1.xml" ContentType="..."/>
_OVERRIDE_RE = re.compile(rb"<Override\b[^>]*?/>")

_SLIDE_PART_RE = re.compile(r"^ppt/slides/slide\d+\.xml$")
_SLIDE_RELS_PART_RE = re.compile(r"^ppt/slides/_rels/slide\d+\.xml\.rels$")
_NOTES_PART_RE = re.compile(r"^ppt/notesSlides/notesSlide\d+\.xml$")
_NOTES_RELS_PART_RE = re.compile(r"^ppt/notesSlides/_rels/notesSlide\d+\.xml\.rels$")


class PPTXValidationError(FileValidationError):
    """Exception for PPTX validation errors."""

    def __init__(self, message: str):
        super().__init__(message, file_type="PPTX")


def _as_bytes(pptx_file: Union[BinaryIO, bytes]) -> bytes:
    if isinstance(pptx_file, bytes):
        return pptx_file
    pptx_file.seek(0)
    return pptx_file.read()


def is_pptx(pptx_file: Union[BinaryIO, bytes]) -> bool:
    """Return True if the given file is an OOXML PresentationML package (.pptx).

    Detection is based on the package structure (a zip containing
    ``ppt/presentation.xml``) rather than the filename or declared content type,
    so it correctly rejects legacy ``.ppt`` (OLE) files, which are not zips.
    """
    try:
        content = _as_bytes(pptx_file)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return _PRESENTATION_PART in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _attr(entry: bytes, name: str) -> Optional[str]:
    match = re.search(rb'\b' + name.encode() + rb'="([^"]*)"', entry)
    return match.group(1).decode() if match else None


def _slide_id_entries(presentation_xml: bytes) -> list[tuple[bytes, str]]:
    """Ordered ``(raw <p:sldId/> element, r:id)`` pairs from presentation.xml."""
    entries: list[tuple[bytes, str]] = []
    for match in _SLD_ID_RE.finditer(presentation_xml):
        entry = match.group(0)
        r_id = _attr(entry, "r:id")
        if r_id is not None:
            entries.append((entry, r_id))
    return entries


def get_pptx_slide_count(pptx_file: Union[BinaryIO, bytes]) -> int:
    """Return the number of slides referenced in the presentation."""
    content = _as_bytes(pptx_file)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        presentation_xml = archive.read(_PRESENTATION_PART)
    return len(_slide_id_entries(presentation_xml))


def _rid_to_target(rels_xml: bytes, type_suffix: str) -> dict[str, str]:
    """Map relationship ``Id`` -> ``Target`` for relationships whose Type ends
    with ``type_suffix`` (e.g. ``"/slide"``)."""
    mapping: dict[str, str] = {}
    for match in _RELATIONSHIP_RE.finditer(rels_xml):
        entry = match.group(0)
        rel_type = _attr(entry, "Type")
        if rel_type is None or not rel_type.endswith(type_suffix):
            continue
        r_id = _attr(entry, "Id")
        target = _attr(entry, "Target")
        if r_id is not None and target is not None:
            mapping[r_id] = target
    return mapping


def _normalize_target(target: str, base_dir: str) -> str:
    """Resolve a relationship Target (relative to ``base_dir``) into a package
    part name (posix, no leading slash). Collapses ``..`` segments so e.g.
    ``../notesSlides/notesSlide2.xml`` from ``ppt/slides`` becomes
    ``ppt/notesSlides/notesSlide2.xml``."""
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, target)).lstrip("/")


def _rels_part_for(part_name: str) -> str:
    parent = Path(part_name).parent.as_posix()
    name = Path(part_name).name
    return f"{parent}/_rels/{name}.rels"


def _slide_part_for_rels(rels_part: str) -> str:
    # ppt/slides/_rels/slide1.xml.rels -> ppt/slides/slide1.xml
    parent = Path(rels_part).parent.parent.as_posix()
    name = Path(rels_part).name[: -len(".rels")]
    return f"{parent}/{name}"


def _filter_xml_elements(
    xml: bytes, pattern: re.Pattern[bytes], should_drop
) -> bytes:
    """Remove every element matched by ``pattern`` for which ``should_drop(entry)``
    returns True, leaving the rest of the document byte-for-byte intact."""
    return pattern.sub(
        lambda m: b"" if should_drop(m.group(0)) else m.group(0), xml
    )


class _PptxPackage:
    """Reads a pptx package once and produces minimal per-chunk sub-decks.

    Each chunk keeps every shared part (masters, layouts, themes, notes master,
    media, docProps, ...) unchanged and retains only the slides in the chunk plus
    the notes slides they reference. presentation.xml, its rels, and
    [Content_Types].xml are rewritten so they reference only the kept parts.
    """

    def __init__(self, content: bytes):
        self._content = content
        self._archive = zipfile.ZipFile(io.BytesIO(content))
        self._names = set(self._archive.namelist())

        self._presentation_xml = self._archive.read(_PRESENTATION_PART)
        self._presentation_rels = self._archive.read(_PRESENTATION_RELS_PART)
        self._content_types = self._archive.read(_CONTENT_TYPES_PART)

        self._slide_ids = _slide_id_entries(self._presentation_xml)
        # r:id -> slide part name, in slide order
        rid_to_slide = _rid_to_target(self._presentation_rels, "/slide")
        self._ordered_slides: list[tuple[str, str]] = []  # (r:id, slide part)
        for _entry, r_id in self._slide_ids:
            target = rid_to_slide.get(r_id)
            if target is None:
                continue
            self._ordered_slides.append(
                (r_id, _normalize_target(target, "ppt"))
            )

        # slide part -> notes part it references (if any)
        self._slide_to_notes: dict[str, str] = {}
        for _r_id, slide_part in self._ordered_slides:
            rels_part = _rels_part_for(slide_part)
            if rels_part not in self._names:
                continue
            notes = _rid_to_target(self._archive.read(rels_part), "/notesSlide")
            slide_dir = Path(slide_part).parent.as_posix()
            for notes_target in notes.values():
                self._slide_to_notes[slide_part] = _normalize_target(
                    notes_target, slide_dir
                )
                break

    @property
    def slide_count(self) -> int:
        return len(self._ordered_slides)

    def close(self) -> None:
        self._archive.close()

    def _build_chunk(self, start: int, end: int) -> bytes:
        """Build a sub-deck containing slides ``[start, end)`` (zero-based)."""
        chunk_slides = self._ordered_slides[start:end]
        kept_rids = {r_id for r_id, _ in chunk_slides}
        kept_slide_parts = {part for _, part in chunk_slides}
        kept_notes_parts = {
            self._slide_to_notes[part]
            for part in kept_slide_parts
            if part in self._slide_to_notes
        }

        def is_dropped(name: str) -> bool:
            if _SLIDE_PART_RE.match(name):
                return name not in kept_slide_parts
            if _SLIDE_RELS_PART_RE.match(name):
                return _slide_part_for_rels(name) not in kept_slide_parts
            if _NOTES_PART_RE.match(name):
                return name not in kept_notes_parts
            if _NOTES_RELS_PART_RE.match(name):
                return _slide_part_for_rels(name) not in kept_notes_parts
            return False

        new_presentation_xml = _filter_xml_elements(
            self._presentation_xml,
            _SLD_ID_RE,
            lambda entry: _attr(entry, "r:id") not in kept_rids,
        )
        new_presentation_rels = _filter_xml_elements(
            self._presentation_rels,
            _RELATIONSHIP_RE,
            lambda entry: (
                (_attr(entry, "Type") or "").endswith("/slide")
                and _attr(entry, "Id") not in kept_rids
            ),
        )
        # Some packages declare an <Override> for every part (even .rels parts)
        # rather than relying on <Default Extension="rels">. Drop the override
        # for any part we are not writing so nothing dangles.
        dropped_part_names = {name for name in self._names if is_dropped(name)}
        new_content_types = _filter_xml_elements(
            self._content_types,
            _OVERRIDE_RE,
            lambda entry: (_attr(entry, "PartName") or "").lstrip("/")
            in dropped_part_names,
        )

        rewrites = {
            _PRESENTATION_PART: new_presentation_xml,
            _PRESENTATION_RELS_PART: new_presentation_rels,
            _CONTENT_TYPES_PART: new_content_types,
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
            for item in self._archive.infolist():
                name = item.filename
                if is_dropped(name):
                    continue
                data = rewrites.get(name)
                if data is None:
                    data = self._archive.read(name)
                # Build a fresh ZipInfo per entry: writestr mutates the
                # passed ZipInfo's header_offset, and reusing the source
                # archive's ZipInfo objects would corrupt its central
                # directory for the next chunk.
                zinfo = zipfile.ZipInfo(filename=name, date_time=item.date_time)
                zinfo.compress_type = item.compress_type
                zinfo.external_attr = item.external_attr
                out.writestr(zinfo, data)
        buffer.seek(0)
        return buffer.getvalue()

    def iter_chunks(
        self, split_size: int, page_start: int, page_end: Optional[int]
    ) -> Generator[Tuple[bytes, int], None, None]:
        """Yield ``(chunk_bytes, zero_based_slide_offset)`` for each sub-deck.

        ``page_start``/``page_end`` are 1-based, inclusive slide numbers matching
        the PDF page-range semantics.
        """
        offset = page_start - 1
        offset_end = page_end if page_end else self.slide_count
        while offset < offset_end:
            end = min(offset + split_size, offset_end)
            yield self._build_chunk(offset, end), offset
            offset += split_size


def get_pptx_chunks_in_memory(
    pptx_content: bytes,
    split_size: int = 1,
    page_start: int = 1,
    page_end: Optional[int] = None,
) -> list[Tuple[BinaryIO, int]]:
    """Split a pptx into in-memory sub-deck buffers, mirroring
    ``SplitPdfHook._get_pdf_chunks_in_memory``.

    Returns a list of ``(BytesIO, zero_based_slide_offset)`` tuples.
    """
    package = _PptxPackage(pptx_content)
    try:
        return [
            (io.BytesIO(chunk_bytes), offset)
            for chunk_bytes, offset in package.iter_chunks(
                split_size, page_start, page_end
            )
        ]
    finally:
        package.close()


def get_pptx_chunk_paths(
    pptx_content: bytes,
    cache_tmp_data_dir: str,
    split_size: int = 1,
    page_start: int = 1,
    page_end: Optional[int] = None,
) -> Tuple[tempfile.TemporaryDirectory, list[Tuple[Path, int]]]:
    """Split a pptx into sub-deck files on disk, mirroring
    ``SplitPdfHook._get_pdf_chunk_paths``.

    Returns the owning ``TemporaryDirectory`` (so the caller can track it for
    cleanup) and a list of ``(Path, zero_based_slide_offset)`` tuples.
    """
    tempdir = tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
        dir=cache_tmp_data_dir, prefix="unstructured_client_"
    )
    tempdir_path = Path(tempdir.name)

    package = _PptxPackage(pptx_content)
    chunk_paths: list[Tuple[Path, int]] = []
    try:
        for chunk_no, (chunk_bytes, offset) in enumerate(
            package.iter_chunks(split_size, page_start, page_end), start=1
        ):
            chunk_path = tempdir_path / f"chunk_{chunk_no}.pptx"
            chunk_path.write_bytes(chunk_bytes)
            chunk_paths.append((chunk_path, offset))
    finally:
        package.close()

    return tempdir, chunk_paths
