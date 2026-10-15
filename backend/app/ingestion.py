"""Bounded, dependency-free upload classification and page-model contracts."""
from __future__ import annotations

import base64
import re
import posixpath
import struct
import zlib
from xml.etree import ElementTree as ET
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile
from xml.sax.saxutils import unescape
from pypdf import PdfReader

from app.layout import map_layout_elements
from app.pdf_geometry import normalize_pdf_box


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
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            if reader.trailer.get("/Root") is not None and b"%%EOF" in data[-2048:]:
                return max(1, len(reader.pages))
        except Exception:
            # Keep the byte-level hint as a bounded fallback for malformed PDFs.
            pass
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


def clean_extracted_text(value: str) -> str:
    """Turn leaked WordprocessingML/XML markup into readable source text."""
    value = unescape(value)
    value = re.sub(r"<\/?(?:w|a|wp|pic|mc):[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def chunk_extracted_text(value: str, limit: int = 420) -> list[str]:
    """Keep oversized source text reviewable without pretending it is a field."""
    words = value.split()
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > limit:
            chunks.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks or [value]


def simple_pdf_document(data: bytes) -> dict[int, list[dict[str, Any]]]:
    """Extract readable page-level paragraphs with the bundled local PDF reader.

    Layout text is used to retain line and blank-line boundaries where available.
    The reader does not expose trusted boxes through this path, so none are made
    up. This is structural text extraction, not OCR or general layout analysis.
    """
    def legacy_text() -> dict[int, list[dict[str, Any]]]:
        page_markers = list(re.finditer(rb"/Type\s*/Page(?:\s|/|>>)", data))
        segments = [(index + 1, data[marker.start():page_markers[index + 1].start()
                                     if index + 1 < len(page_markers) else len(data)])
                    for index, marker in enumerate(page_markers)] if page_markers else [(1, data)]
        result: dict[int, list[dict[str, Any]]] = {}
        sources = _pdf_sources(data)
        for page_number, segment in segments:
            operands: list[str] = []
            candidates = [segment] if page_markers else sources
            for source in candidates:
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
            fallback = []
            for value in operands:
                raw_value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
                value = clean_extracted_text(raw_value)
                for chunk in chunk_extracted_text(value):
                    if chunk:
                        fallback.append({"id": f"text-{len(fallback) + 1}", "type": "text",
                                         "text": chunk, "raw_text": raw_value,
                                         "role": _layout_role(chunk, len(fallback))})
            if fallback:
                result[page_number] = fallback
        return result

    pages: dict[int, list[dict[str, Any]]] = {}
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.trailer.get("/Root") is None or b"%%EOF" not in data[-2048:]:
            raise ValueError("PDF trailer is incomplete")
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                extracted = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                extracted = ""
            paragraphs: list[str] = []
            lines: list[str] = []
            for line in extracted.splitlines():
                if line.strip():
                    lines.append(line.strip())
                elif lines:
                    paragraphs.append(" ".join(lines))
                    lines = []
            if lines:
                paragraphs.append(" ".join(lines))
            elements: list[dict[str, Any]] = []
            for paragraph in paragraphs:
                value = clean_extracted_text(paragraph)
                for chunk in chunk_extracted_text(value, limit=2000):
                    if not chunk:
                        continue
                    element = {"id": f"p{page_number}-text-{len(elements) + 1}",
                               "type": "text", "text": chunk, "raw_text": paragraph}
                    element["role"] = _layout_role(chunk, len(elements))
                    elements.append(element)
            pages[page_number] = elements
    except Exception:
        # Preserve the old best-effort path for tiny or malformed PDF-like inputs
        # that the upload contract historically accepted. It carries no geometry.
        return legacy_text()
    return pages if any(pages.values()) else legacy_text()


def simple_pdf_text_elements(data: bytes) -> list[dict[str, Any]]:
    """Compatibility wrapper returning page-tagged elements from ``simple_pdf_document``."""
    return [{**element, "page_number": page_number}
            for page_number, elements in simple_pdf_document(data).items()
            for element in elements]


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
    ".docx": (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
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
    digital = (suffix == ".pdf" and _pdf_has_text_operators(data)) or suffix == ".docx"
    return UploadClassification(media_type=expected_type, route="digital" if digital else "scan")


_DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _docx_child(element: ET.Element, name: str) -> ET.Element | None:
    return element.find(f"{{{_DOCX_NS}}}{name}")


def _read_docx_member(archive: ZipFile, name: str, limit: int) -> bytes:
    with archive.open(name, "r") as member:
        return member.read(limit + 1)


def _docx_value(element: ET.Element | None, name: str, default: str = "") -> str:
    if element is None:
        return default
    return str(element.get(f"{{{_DOCX_NS}}}{name}", default))


def _docx_run_text(run: ET.Element) -> str:
    parts: list[str] = []
    for child in run.iter():
        local = child.tag.rsplit("}", 1)[-1]
        if local == "t":
            parts.append(child.text or "")
        elif local == "tab":
            parts.append("\t")
        elif local in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts)


def _docx_run(run: ET.Element, defaults: dict[str, Any] | None = None) -> dict[str, Any] | None:
    text = clean_extracted_text(_docx_run_text(run))
    if not text:
        return None
    props = _docx_child(run, "rPr")
    result: dict[str, Any] = {"text": text, **(defaults or {})}
    for tag, key in (("b", "bold"), ("i", "italic"), ("u", "underline")):
        flag = _docx_child(props, tag) if props is not None else None
        if flag is not None:
            result[key] = _docx_value(flag, "val", "1") not in {"0", "false", "none"}
    fonts = _docx_child(props, "rFonts") if props is not None else None
    family = _docx_value(fonts, "ascii") or _docx_value(fonts, "hAnsi")
    if family and len(family) <= 100:
        result["font_family"] = family
    size = _docx_child(props, "sz") if props is not None else None
    try:
        if size is not None:
            result["font_size"] = round(float(_docx_value(size, "val")) * 2 / 3, 2)
    except ValueError:
        pass
    color = _docx_child(props, "color") if props is not None else None
    color_value = _docx_value(color, "val")
    if re.fullmatch(r"[0-9A-Fa-f]{6}", color_value):
        result["color"] = f"#{color_value.lower()}"
    return result


def _docx_style_formats(archive: ZipFile, names: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if "word/styles.xml" not in names:
        return {}, {}
    raw_xml = _read_docx_member(archive, "word/styles.xml", 2_000_000)
    if len(raw_xml) > 2_000_000 or b"<!DOCTYPE" in raw_xml.upper() or b"<!ENTITY" in raw_xml.upper():
        return {}, {}
    root = ET.fromstring(raw_xml)

    def run_style(props: ET.Element | None) -> dict[str, Any]:
        if props is None:
            return {}
        result: dict[str, Any] = {}
        for tag, key in (("b", "bold"), ("i", "italic"), ("u", "underline")):
            node = _docx_child(props, tag)
            if node is not None:
                result[key] = _docx_value(node, "val", "1") not in {"0", "false", "none"}
        fonts = _docx_child(props, "rFonts")
        family = _docx_value(fonts, "ascii") or _docx_value(fonts, "hAnsi")
        if family and len(family) <= 100:
            result["font_family"] = family
        size = _docx_child(props, "sz")
        try:
            if size is not None:
                result["font_size"] = round(float(_docx_value(size, "val")) * 2 / 3, 2)
        except ValueError:
            pass
        color = _docx_child(props, "color")
        value = _docx_value(color, "val")
        if re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            result["color"] = f"#{value.lower()}"
        return result

    def paragraph_style(props: ET.Element | None) -> dict[str, Any]:
        if props is None:
            return {}
        result: dict[str, Any] = {}
        alignment = _docx_value(_docx_child(props, "jc"), "val")
        if alignment:
            result["alignment"] = "justify" if alignment in {"both", "distribute"} else alignment
        spacing = _docx_child(props, "spacing")
        for source_key, target_key in (("before", "spacing_before"), ("after", "spacing_after"), ("line", "line_spacing")):
            try:
                raw = _docx_value(spacing, source_key)
                if raw:
                    result[target_key] = round(float(raw) / 15, 2)
            except ValueError:
                pass
        indent = _docx_child(props, "ind")
        for source_key, target_key in (("left", "left_indent"), ("right", "right_indent"), ("firstLine", "first_line_indent")):
            try:
                raw = _docx_value(indent, source_key)
                if raw:
                    result[target_key] = round(float(raw) / 15, 2)
            except ValueError:
                pass
        return result

    raw_styles: dict[str, dict[str, Any]] = {}
    for style in root.findall(f"{{{_DOCX_NS}}}style"):
        style_id = style.get(f"{{{_DOCX_NS}}}styleId", "")
        name_node = _docx_child(style, "name")
        based = _docx_child(style, "basedOn")
        if style_id:
            raw_styles[style_id] = {"name": _docx_value(name_node, "val", style_id),
                                    "based_on": _docx_value(based, "val"),
                                    "run": run_style(_docx_child(style, "rPr")),
                                    "paragraph": paragraph_style(_docx_child(style, "pPr"))}
    resolved: dict[str, dict[str, Any]] = {}
    for style_id in raw_styles:
        chain: list[str] = []
        current = style_id
        while current in raw_styles and current not in chain and len(chain) < 12:
            chain.append(current)
            current = str(raw_styles[current]["based_on"])
        style_format: dict[str, Any] = {"run": {}, "paragraph": {}, "name": raw_styles[style_id]["name"]}
        for parent in reversed(chain):
            style_format["run"].update(raw_styles[parent]["run"])
            style_format["paragraph"].update(raw_styles[parent]["paragraph"])
        resolved[style_id] = style_format
    defaults_node = root.find(f"{{{_DOCX_NS}}}docDefaults/{{{_DOCX_NS}}}rPrDefault/{{{_DOCX_NS}}}rPr")
    return resolved, run_style(defaults_node)


def _docx_paragraph(paragraph: ET.Element, index: int,
                    styles: dict[str, dict[str, Any]] | None = None,
                    defaults: dict[str, Any] | None = None) -> dict[str, Any] | None:
    props = _docx_child(paragraph, "pPr")
    style = _docx_child(props, "pStyle") if props is not None else None
    style_id = _docx_value(style, "val")
    style_data = (styles or {}).get(style_id, {})
    style_name = str(style_data.get("name") or style_id.replace("_", " "))
    lower_style = style_id.casefold()
    effective_run_style = {**(defaults or {}), **style_data.get("run", {})}
    runs = [run for child in paragraph.iter() if child.tag == f"{{{_DOCX_NS}}}r"
            if (run := _docx_run(child, effective_run_style)) is not None]
    plain_text = "".join(run["text"] for run in runs).strip()
    if not plain_text:
        return None
    alignment_node = _docx_child(props, "jc") if props is not None else None
    alignment = _docx_value(alignment_node, "val", str(style_data.get("paragraph", {}).get("alignment", "left")))
    if alignment not in {"left", "center", "right", "both", "distribute"}:
        alignment = "left"
    alignment = "justify" if alignment in {"both", "distribute"} else alignment
    num_props = _docx_child(props, "numPr") if props is not None else None
    is_list = num_props is not None or "listbullet" in lower_style or "listnumber" in lower_style
    role = "heading" if lower_style == "title" or "heading" in lower_style or lower_style.startswith("subtitle") else (
        "list_item" if is_list else "text")
    format_data: dict[str, Any] = {**style_data.get("paragraph", {}), "style_id": style_id,
                                   "style_name": style_name, "alignment": alignment}
    spacing = _docx_child(props, "spacing") if props is not None else None
    for source_key, target_key in (("before", "spacing_before"), ("after", "spacing_after"), ("line", "line_spacing")):
        try:
            raw = _docx_value(spacing, source_key)
            if raw:
                format_data[target_key] = round(float(raw) / 15, 2)
        except ValueError:
            pass
    indent = _docx_child(props, "ind") if props is not None else None
    for source_key, target_key in (("left", "left_indent"), ("right", "right_indent"), ("firstLine", "first_line_indent")):
        try:
            raw = _docx_value(indent, source_key)
            if raw:
                format_data[target_key] = round(float(raw) / 15, 2)
        except ValueError:
            pass
    page_break = _docx_child(props, "pageBreakBefore") if props is not None else None
    if page_break is not None and _docx_value(page_break, "val", "1") not in {"0", "false"}:
        format_data["break_before"] = True
    if role == "heading":
        match = re.search(r"([1-9])$", style_id)
        format_data["heading_level"] = int(match.group(1)) if match else (1 if lower_style == "title" else 2)
    if is_list:
        num_fmt = ""
        if num_props is not None:
            num_id = _docx_child(num_props, "numId")
            format_data["num_id"] = _docx_value(num_id, "val")
        format_data["list_style"] = "ordered" if "number" in lower_style else "unordered"
    return {"id": f"paragraph-{index}", "type": "text", "role": role,
            "text": plain_text, "raw_text": plain_text, "runs": runs,
            "paragraph_format": format_data, "box": [72, 72 + index * 18, 540, 86 + index * 18]}


def simple_docx_document(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read bounded DOCX paragraphs, tables and page furniture from OOXML."""
    try:
        with ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            if "word/document.xml" not in names or len(names) > 200 or sum(item.file_size for item in archive.infolist()) > 32_000_000:
                return [], {"warnings": ["The Word file exceeds bounded OOXML package limits."]}
            xml = _read_docx_member(archive, "word/document.xml", 8_000_000)
            if len(xml) > 8_000_000 or b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                return [], {"warnings": ["The Word document XML is oversized or contains a prohibited declaration."]}
            root = ET.fromstring(xml)
            style_formats, default_run_style = _docx_style_formats(archive, names)
            body = root.find(f".//{{{_DOCX_NS}}}body")
            if body is None:
                return [], {"warnings": ["The Word document body could not be read."]}
            elements: list[dict[str, Any]] = []
            paragraph_index = 0
            for child in body:
                local = child.tag.rsplit("}", 1)[-1]
                if local == "p":
                    paragraph_index += 1
                    paragraph = _docx_paragraph(child, paragraph_index, style_formats, default_run_style)
                    if paragraph:
                        elements.append(paragraph)
                elif local == "tbl":
                    rows: list[list[str]] = []
                    for row in child.findall(f"{{{_DOCX_NS}}}tr")[:200]:
                        cells: list[str] = []
                        for cell in row.findall(f"{{{_DOCX_NS}}}tc")[:50]:
                            cell_paragraphs = [_docx_paragraph(p, paragraph_index + idx + 1,
                                                               style_formats, default_run_style)
                                               for idx, p in enumerate(cell.findall(f"{{{_DOCX_NS}}}p"))]
                            cell_text = " ".join(paragraph["text"] for paragraph in cell_paragraphs if paragraph)
                            cells.append(cell_text[:2000])
                        if cells:
                            rows.append(cells)
                    if rows:
                        flat = " | ".join(" | ".join(row) for row in rows)
                        elements.append({"id": f"table-{len([e for e in elements if e['type'] == 'table']) + 1}",
                                         "type": "table", "role": "table", "text": flat[:100_000],
                                         "raw_text": flat[:100_000], "table": {"rows": rows},
                                         "box": [72, 72 + paragraph_index * 18, 540, 90 + paragraph_index * 18]})
            section = body.find(f"{{{_DOCX_NS}}}sectPr")
            page: dict[str, Any] = {}
            relationship_targets: dict[str, str] = {}
            rels_name = "word/_rels/document.xml.rels"
            if rels_name in names:
                rels_xml = _read_docx_member(archive, rels_name, 1_000_000)
                if len(rels_xml) <= 1_000_000 and b"<!DOCTYPE" not in rels_xml.upper() and b"<!ENTITY" not in rels_xml.upper():
                    rels_root = ET.fromstring(rels_xml)
                    for relationship in rels_root:
                        rel_id = relationship.get("Id", "")
                        target = relationship.get("Target", "")
                        if relationship.get("TargetMode") != "External" and rel_id and target:
                            resolved = posixpath.normpath(posixpath.join("word", target))
                            if resolved.startswith("word/") and ".." not in resolved.split("/"):
                                relationship_targets[rel_id] = resolved
            if section is not None:
                size = _docx_child(section, "pgSz")
                margins = _docx_child(section, "pgMar")
                if size is not None:
                    width, height = int(size.get(f"{{{_DOCX_NS}}}w", "0")), int(size.get(f"{{{_DOCX_NS}}}h", "0"))
                    if width > 0 and height > 0:
                        page.update({"size": "Letter" if (width, height) == (12240, 15840) else "A4" if (width, height) == (11906, 16838) else "A4",
                                     "orientation": "landscape" if width > height else "portrait"})
                if margins is not None:
                    for key in ("top", "right", "bottom", "left"):
                        try:
                            page[f"margin_{key}_mm"] = round(int(margins.get(f"{{{_DOCX_NS}}}{key}", "1134")) * 25.4 / 1440, 2)
                        except ValueError:
                            pass
                for reference_name, page_key in (("headerReference", "header"), ("footerReference", "footer")):
                    reference = section.find(f"{{{_DOCX_NS}}}{reference_name}")
                    rel_id = reference.get(f"{{{_REL_NS}}}id", "") if reference is not None else ""
                    part_name = relationship_targets.get(rel_id, "")
                    if part_name in names:
                        part_xml = _read_docx_member(archive, part_name, 1_000_000)
                        if len(part_xml) <= 1_000_000 and b"<!DOCTYPE" not in part_xml.upper() and b"<!ENTITY" not in part_xml.upper():
                            part_root = ET.fromstring(part_xml)
                            text = clean_extracted_text(" ".join(node.text or "" for node in part_root.iter()
                                                                  if node.tag == f"{{{_DOCX_NS}}}t"))
                            if text:
                                page[page_key] = text[:1000]
            warnings: list[str] = []
            image_count = sum(1 for name in names if name.startswith("word/media/"))
            header_images: list[dict[str, Any]] = []
            unsupported_images = image_count
            section_nodes = section if section is not None else ET.Element("section")
            for page_key, part_name in (("header", relationship_targets.get(
                    next((node.get(f"{{{_REL_NS}}}id", "") for node in section_nodes.findall(f"{{{_DOCX_NS}}}headerReference")), ""), "")),
                    ("footer", relationship_targets.get(
                    next((node.get(f"{{{_REL_NS}}}id", "") for node in section_nodes.findall(f"{{{_DOCX_NS}}}footerReference")), ""), ""))):
                if not part_name or part_name not in names:
                    continue
                part_xml = _read_docx_member(archive, part_name, 1_000_000)
                if len(part_xml) > 1_000_000 or b"<!DOCTYPE" in part_xml.upper() or b"<!ENTITY" in part_xml.upper():
                    continue
                part_root = ET.fromstring(part_xml)
                zones: dict[str, list[str]] = {"left": [], "center": [], "right": []}
                for para_index, para in enumerate(node for node in part_root.iter() if node.tag == f"{{{_DOCX_NS}}}p"):
                    parsed = _docx_paragraph(para, para_index + 1, style_formats, default_run_style)
                    if not parsed:
                        continue
                    align = parsed["paragraph_format"].get("alignment", "left")
                    if align not in zones:
                        align = "left"
                    text = parsed["text"]
                    if page_key == "footer" and any(child.tag == f"{{{_DOCX_NS}}}instrText" and "PAGE" in (child.text or "").upper()
                                                      for child in para.iter()):
                        page["show_page_numbers"] = True
                        page["page_number_position"] = "footer-right"
                        text = re.sub(r"\bPage\s*$", "", text, flags=re.IGNORECASE).strip()
                    if text:
                        zones[align].append(text)
                for align, values in zones.items():
                    if values:
                        page[f"{page_key}_{align}"] = " ".join(values)[:1000]
                if any(zones.values()):
                    page.pop(page_key, None)
                if page_key == "header":
                    header_rels_name = posixpath.join(posixpath.dirname(part_name), "_rels",
                                                      posixpath.basename(part_name) + ".rels")
                    header_rels: dict[str, str] = {}
                    if header_rels_name in names:
                        header_rels_xml = _read_docx_member(archive, header_rels_name, 1_000_000)
                        if len(header_rels_xml) <= 1_000_000 and b"<!DOCTYPE" not in header_rels_xml.upper() and b"<!ENTITY" not in header_rels_xml.upper():
                            for relationship in ET.fromstring(header_rels_xml):
                                rel_id, target = relationship.get("Id", ""), relationship.get("Target", "")
                                if relationship.get("TargetMode") != "External" and rel_id and target:
                                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(part_name), target))
                                    if resolved.startswith("word/media/") and ".." not in resolved.split("/"):
                                        header_rels[rel_id] = resolved
                    for drawing in (node for node in part_root.iter() if node.tag.rsplit("}", 1)[-1] == "drawing"):
                        blip = next((node for node in drawing.iter() if node.tag.rsplit("}", 1)[-1] == "blip"), None)
                        rel_id = blip.get(f"{{{_REL_NS}}}embed", "") if blip is not None else ""
                        media_name = header_rels.get(rel_id, "")
                        if not media_name or media_name not in names:
                            continue
                        extension = PurePosixPath(media_name).suffix.casefold()
                        media_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                                      ".gif": "image/gif", ".webp": "image/webp"}.get(extension)
                        image = _read_docx_member(archive, media_name, 1_000_000)
                        signatures = {"image/png": image.startswith(b"\x89PNG\r\n\x1a\n"),
                                      "image/jpeg": image.startswith(b"\xff\xd8\xff"),
                                      "image/gif": image.startswith((b"GIF87a", b"GIF89a")),
                                      "image/webp": len(image) > 12 and image[:4] == b"RIFF" and image[8:12] == b"WEBP"}
                        if not media_type or len(image) > 1_000_000 or not signatures.get(media_type, False):
                            continue
                        properties = next((node for node in drawing.iter() if node.tag.rsplit("}", 1)[-1] == "docPr"), None)
                        extent = next((node for node in drawing.iter() if node.tag.rsplit("}", 1)[-1] == "extent"), None)
                        image_width = 150
                        if extent is not None:
                            try:
                                image_width = max(1, min(600, round(int(extent.get("cx", "0")) / 9525)))
                            except ValueError:
                                pass
                        alt = (properties.get("descr") or properties.get("name") or "Source header image") if properties is not None else "Source header image"
                        header_images.append({"src": f"data:{media_type};base64,{base64.b64encode(image).decode('ascii')}",
                                              "alt": alt[:200], "width": image_width})
            unsupported_images = max(0, image_count - len(header_images))
            if header_images:
                warnings.append("A supported header image is inserted at the start of the editable content; repeating image placement in page furniture is not available.")
            if unsupported_images:
                warnings.append(f"The Word file contains {unsupported_images} embedded image asset(s) whose placement or format is not reconstructed.")
            metadata = {"page": page, "warnings": warnings,
                        "paragraph_count": paragraph_index,
                        "table_count": sum(element["type"] == "table" for element in elements),
                        "embedded_image_count": image_count, "header_images": header_images}
            return elements[:1000], metadata
    except (BadZipFile, KeyError, RuntimeError, ValueError, ET.ParseError, OSError):
        return [], {"warnings": ["The Word file is invalid or could not be safely read."]}


def simple_docx_text_elements(data: bytes) -> list[dict[str, Any]]:
    """Compatibility wrapper for callers that need only extracted DOCX elements."""
    return simple_docx_document(data)[0]


def page_model(document_id: str, filename: str, classification: UploadClassification,
               size_bytes: int, page_count: int = 1,
               elements: list[dict[str, Any]] | None = None,
               dimensions: tuple[int, int] | None = None,
               page_elements: dict[int, list[dict[str, Any]]] | None = None,
               page_routes: list[str] | None = None,
               page_metadata: list[dict[str, Any]] | None = None,
               page_classifications: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    first_page_elements = elements or []
    width, height = dimensions or (None, None)
    if page_elements is None and first_page_elements:
        page_numbers = {element.get("page_number") for element in first_page_elements
                        if isinstance(element.get("page_number"), int)}
        if page_numbers:
            page_elements = {number: [{key: value for key, value in element.items() if key != "page_number"}
                                      for element in first_page_elements if element.get("page_number") == number]
                             for number in page_numbers}
    all_page_elements = page_elements or ({1: first_page_elements} if first_page_elements else {})
    normalized_pages: dict[int, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
    for page_number, raw_elements in all_page_elements.items():
        prepared = []
        metadata = page_metadata[page_number - 1] if page_metadata and page_number <= len(page_metadata) else None
        for element in raw_elements:
            item = dict(element)
            if (metadata and item.get("source_coordinate_system") == "pdf-user-space"
                    and item.get("source_box_pdf_user_space") is not None):
                item["box"] = normalize_pdf_box(item["source_box_pdf_user_space"],
                                                crop_box=metadata["crop_box_pdf_user_space"],
                                                rotation=metadata.get("rotation", 0))
                item["source_box_pdf_user_space"] = list(item["source_box_pdf_user_space"])
                item["source_coordinate_system"] = "pdf-user-space"
            prepared.append(item)
        normalized, layout = map_layout_elements(prepared)
        normalized_pages[page_number] = (normalized, layout)
    return {
        "schema_version": 1,
        "document_id": document_id,
        "source": {"filename": filename, "media_type": classification.media_type,
                   "route": classification.route, "size_bytes": size_bytes},
        "pages": [{"page_number": number, "route": (page_routes[number - 1]
                                                        if page_routes and number <= len(page_routes)
                                                        else classification.route),
                   "width": ((page_metadata[number - 1].get("width_points"))
                             if page_metadata and number <= len(page_metadata) else width),
                   "height": ((page_metadata[number - 1].get("height_points"))
                              if page_metadata and number <= len(page_metadata) else height),
                   "rotation": ((page_metadata[number - 1].get("rotation", 0))
                                if page_metadata and number <= len(page_metadata) else 0),
                   "coordinate_system": "top-left-points",
                   "source_geometry": ({"media_box_pdf_user_space": page_metadata[number - 1].get("media_box_pdf_user_space"),
                                        "crop_box_pdf_user_space": page_metadata[number - 1].get("crop_box_pdf_user_space"),
                                        "original_width_points": page_metadata[number - 1].get("original_width_points"),
                                        "original_height_points": page_metadata[number - 1].get("original_height_points")}
                                       if page_metadata and number <= len(page_metadata) else None),
                   "classification": (page_classifications[number - 1]
                                      if page_classifications and number <= len(page_classifications) else None),
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
            box = ",".join(str(value) for value in (element.get("box") or []))
            lines.append(f"<!-- element:{element.get('id')} page:{page.get('page_number')} box:{box} -->")
            lines.append(str(element.get("text", "")) if element.get("type") != "image"
                         else f"![{element.get('id')}]()")
    return "\n".join(lines) + "\n"
