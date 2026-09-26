"""Bounded, dependency-free upload classification and page-model contracts."""
from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from app.layout import map_layout_elements


class IngestionInputError(ValueError):
    pass


@dataclass(frozen=True)
class UploadClassification:
    media_type: str
    route: str


_MAX_PDF_STREAM_BYTES = 1_000_000
_MAX_PDF_DECOMPRESSED_BYTES = 4_000_000
_MAX_PDF_DECOMPRESSED_TOTAL = 16_000_000


def count_pages(filename: str, data: bytes) -> int:
    """Return a conservative page count without parsing or executing a document.

    The count is used only for the configured ingestion limit and progress
    contract. PDF object dictionaries are intentionally treated as a hint;
    image uploads are single-page inputs at this stage.
    """
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if suffix == ".pdf":
        matches = re.findall(rb"/Type\s*/Page(?:\s|/|>>)", data)
        return max(1, len(matches))
    return 1


def _pdf_sources(data: bytes) -> list[bytes]:
    """Return the original bytes and bounded Flate streams for routing/extraction."""
    sources = [data]
    total = 0
    pattern = re.compile(rb"/Filter\s*/FlateDecode(?:(?!endobj).){0,1024}?stream\r?\n", re.DOTALL)
    for match in pattern.finditer(data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        compressed = data[start:end].rstrip(b"\r\n")
        if not compressed or len(compressed) > _MAX_PDF_STREAM_BYTES:
            continue
        try:
            decoder = zlib.decompressobj()
            inflated = decoder.decompress(compressed, _MAX_PDF_DECOMPRESSED_BYTES + 1)
            if len(inflated) > _MAX_PDF_DECOMPRESSED_BYTES or not decoder.eof:
                continue
            inflated += decoder.flush()
        except zlib.error:
            continue
        if len(inflated) > _MAX_PDF_DECOMPRESSED_BYTES or total + len(inflated) > _MAX_PDF_DECOMPRESSED_TOTAL:
            continue
        total += len(inflated)
        sources.append(inflated)
    return sources


def simple_pdf_text_elements(data: bytes) -> list[dict[str, Any]]:
    """Extract only uncomplicated ``(text) Tj`` operators for the contract path.

    This is intentionally not a PDF parser. Complex strings, fonts, transforms,
    and layout relationships remain delegated to the future isolated layout
    engine.
    """
    elements: list[dict[str, Any]] = []
    operands: list[str] = []
    for source in _pdf_sources(data):
        operands.extend(match.group(1).decode("latin-1", errors="replace")
                        for match in re.finditer(rb"\(([^()]*)\)\s*Tj", source))
        for match in re.finditer(rb"(?<!<)<([0-9A-Fa-f\s]+)>\s*Tj", source):
            try:
                encoded = bytes.fromhex(re.sub(rb"\s+", b"", match.group(1)).decode("ascii"))
                operands.append(encoded.decode(
                    "utf-16-be" if len(encoded) >= 2 and encoded.startswith(b"\xfe\xff") else "latin-1",
                    errors="replace"))
            except (ValueError, UnicodeDecodeError):
                continue
    for index, value in enumerate(operands):
        value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
        if not value.strip():
            continue
        top = 72 + index * 18
        elements.append({"id": f"text-{index + 1}", "type": "text", "text": value,
                         "box": [72, top, 540, top + 14]})
    return elements


_LIST_ITEM_RE = re.compile(r"^(?:[-*•‣▪]|\(?\d{1,3}[.)])\s+")
_TABLE_ROW_RE = re.compile(r"[^|]+(?:\|[^|]+){2,}")


def _layout_role(text: str, index: int) -> str:
    """Classify explicit, low-risk layout markers in the bounded text path."""
    value = text.strip()
    if value.startswith(("# ", "## ", "### ")):
        return "heading"
    if _LIST_ITEM_RE.match(value):
        return "list_item"
    if _TABLE_ROW_RE.fullmatch(value):
        return "table_row"
    # A short all-caps line is a useful heading signal for simple exports, but
    # keep the rule conservative so ordinary prose is not relabelled.
    if index > 0 and len(value) <= 120 and value.upper() == value and any(char.isalpha() for char in value):
        return "heading"
    return "text"


def annotate_layout(elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Add deterministic reading-order and role metadata to known elements.

    This is a bounded contract aid for simple digital text. It is deliberately
    heuristic and does not claim document layout analysis, table segmentation,
    or reading-order correctness for arbitrary PDFs.
    """
    reading_order = [str(element["id"]) for element in elements]
    headings = []
    lists = []
    table_rows = []
    for index, element in enumerate(elements):
        if element.get("type") != "text":
            continue
        role = _layout_role(str(element.get("text", "")), index)
        element["role"] = role
        if role == "heading":
            headings.append(element["id"])
        elif role == "list_item":
            lists.append(element["id"])
        elif role == "table_row":
            table_rows.append(element["id"])
    tables = [{"row_ids": table_rows}] if table_rows else []
    return {"reading_order": reading_order, "headings": headings, "lists": lists, "tables": tables}


def _pdf_has_text_operators(data: bytes) -> bool:
    """Recognize bounded uncompressed PDF text operands for routing only."""
    return any(re.search(rb"\((?:[^()]|\\.)*\)\s*Tj", source) or
               re.search(rb"(?<!<)<[0-9A-Fa-f\s]+>\s*Tj", source) or
               re.search(rb"\[[^\]]*\]\s*TJ", source)
               for source in _pdf_sources(data))


def detect_page_routes(data: bytes, page_count: int, default_route: str) -> list[str]:
    """Classify conservatively detectable PDF pages as ``digital`` or ``scan``.

    This uses only bounded text-operator evidence inside simple page-object
    spans. If page boundaries cannot be associated reliably, it returns the
    document route for every page rather than inventing page-level certainty.
    It is routing evidence, not a general PDF parser.
    """
    if page_count < 1 or not data.startswith(b"%PDF-"):
        return [default_route] * max(1, page_count)
    markers = [match.start() for match in re.finditer(rb"/Type\s*/Page(?:\s|/|>>)", data)]
    if len(markers) != page_count:
        return [default_route] * page_count
    routes: list[str] = []
    for index, start in enumerate(markers):
        end = markers[index + 1] if index + 1 < len(markers) else len(data)
        routes.append("digital" if _pdf_has_text_operators(data[start:end]) else "scan")
    return routes


def image_dimensions(data: bytes, media_type: str) -> tuple[int, int] | None:
    """Read bounded pixel dimensions from supported raster headers only."""
    if media_type == "image/png" and len(data) >= 24 and data[12:16] == b"IHDR":
        width, height = struct.unpack(">II", data[16:24])
        return (width, height) if width and height else None
    if media_type == "image/jpeg" and data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 4 <= len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(data):
                break
            segment_length = struct.unpack(">H", data[offset:offset + 2])[0]
            if segment_length < 2 or offset + segment_length > len(data):
                break
            if (marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) |
                    set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0))) and segment_length >= 7:
                height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
                return (width, height) if width and height else None
            offset += segment_length
    if media_type == "image/tiff" and len(data) >= 8:
        endian = data[:2]
        if endian not in {b"II", b"MM"}:
            return None
        order = "<" if endian == b"II" else ">"
        if struct.unpack(order + "H", data[2:4])[0] != 42:
            return None
        ifd_offset = struct.unpack(order + "I", data[4:8])[0]
        if ifd_offset + 2 > len(data):
            return None
        count = struct.unpack(order + "H", data[ifd_offset:ifd_offset + 2])[0]
        for index in range(min(count, 256)):
            entry = ifd_offset + 2 + index * 12
            if entry + 12 > len(data):
                break
            tag, value_type, value_count = struct.unpack(order + "HHI", data[entry:entry + 8])
            if tag not in {256, 257} or value_count != 1 or value_type not in {3, 4}:
                continue
            if value_type == 3:
                value = struct.unpack(order + "H", data[entry + 8:entry + 10])[0]
            else:
                value = struct.unpack(order + "I", data[entry + 8:entry + 12])[0]
            if value <= 0:
                return None
            # TIFF dimensions are collected below from the two tags.
            dimensions = {tag: value}
            for other_index in range(index + 1, min(count, 256)):
                other = ifd_offset + 2 + other_index * 12
                if other + 12 > len(data):
                    break
                other_tag, other_type, other_count = struct.unpack(order + "HHI", data[other:other + 8])
                if other_tag not in {256, 257} or other_count != 1 or other_type not in {3, 4}:
                    continue
                other_value = (struct.unpack(order + "H", data[other + 8:other + 10])[0]
                               if other_type == 3 else struct.unpack(order + "I", data[other + 8:other + 12])[0])
                dimensions[other_tag] = other_value
            if 256 in dimensions and 257 in dimensions and dimensions[256] > 0 and dimensions[257] > 0:
                return dimensions[256], dimensions[257]
    return None


_SIGNATURES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
    ".tif": (None, "image/tiff"),
    ".tiff": (None, "image/tiff"),
}


def classify_upload(filename: str, content_type: str, data: bytes) -> UploadClassification:
    safe_name = PurePosixPath(filename.replace("\\", "/")).name
    suffix = PurePosixPath(safe_name).suffix.lower()
    signature = _SIGNATURES.get(suffix)
    if signature is None:
        raise IngestionInputError("Supported uploads are PDF, PNG, JPEG, or TIFF")
    expected_signature, expected_type = signature
    if expected_signature is not None and not data.startswith(expected_signature):
        raise IngestionInputError("File content does not match its declared type")
    if suffix in {".tif", ".tiff"} and not (data.startswith((b"II*\x00", b"MM\x00*"))):
        raise IngestionInputError("File content does not match its declared type")
    media_type = expected_type if content_type in {"", "application/octet-stream"} else content_type
    if media_type != expected_type:
        raise IngestionInputError("Content type does not match the file extension")
    # A PDF containing text operators is eligible for the digital-text path. This
    # is routing evidence only; it is not a PDF parser or OCR implementation.
    digital = suffix == ".pdf" and _pdf_has_text_operators(data)
    return UploadClassification(media_type=expected_type, route="digital" if digital else "scan")


def page_model(document_id: str, filename: str, classification: UploadClassification,
               size_bytes: int, page_count: int = 1,
               elements: list[dict[str, Any]] | None = None,
               dimensions: tuple[int, int] | None = None,
               page_elements: dict[int, list[dict[str, Any]]] | None = None,
               page_routes: list[str] | None = None) -> dict[str, Any]:
    first_page_elements = elements or []
    width, height = dimensions or (None, None)
    all_page_elements = page_elements or ({1: first_page_elements} if first_page_elements else {})
    normalized_pages: dict[int, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
    for page_number, raw_elements in all_page_elements.items():
        normalized, layout = map_layout_elements(raw_elements)
        normalized_pages[page_number] = (normalized, layout)
    return {
        "schema_version": 1,
        "document_id": document_id,
        "source": {"filename": filename, "media_type": classification.media_type,
                   "route": classification.route, "size_bytes": size_bytes},
        "pages": [{"page_number": number, "route": (page_routes[number - 1]
                                                        if page_routes and number <= len(page_routes)
                                                        else classification.route),
                   "width": width, "height": height, "rotation": 0,
                   "coordinate_system": "top-left-points",
                   "elements": normalized_pages.get(number, ([], {}))[0],
                   "layout": normalized_pages.get(number, ([], {"reading_order": [], "headings": [],
                                                                    "lists": [], "tables": []}))[1]}
                  for number in range(1, page_count + 1)],
    }


def markdown_for(model: dict[str, Any]) -> str:
    """Produce Markdown with explicit source comments for each known element."""
    lines = [f"<!-- document:{model['document_id']} schema:{model['schema_version']} -->"]
    for page in model.get("pages", []):
        for element in page.get("elements", []):
            box = ",".join(str(value) for value in element.get("box", []))
            lines.append(f"<!-- element:{element.get('id')} page:{page.get('page_number')} box:{box} -->")
            lines.append(str(element.get("text", "")) if element.get("type") != "image"
                         else f"![{element.get('id')}]()")
    return "\n".join(lines) + "\n"
