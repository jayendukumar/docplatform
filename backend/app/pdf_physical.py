"""Bounded multi-parser physical-content extraction for the E22 PDF path."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import struct
import zlib
from io import BytesIO
from typing import Any
from urllib.parse import urlsplit

from pypdf import PdfReader
from pypdf import __version__ as PYPDF_VERSION
from pypdf.generic import ContentStream

from app.pdf_geometry import normalize_pdf_box

_MAX_ELEMENTS_PER_PAGE = 10_000
_MAX_IMAGE_BYTES = 512_000
_MAX_DOCUMENT_ASSET_BYTES = 2_000_000
_MAX_VECTOR_PATHS_PER_PAGE = 2_000
_MAX_VECTOR_COMMANDS_PER_PAGE = 20_000
_MAX_IMAGE_PLACEMENTS_PER_PAGE = 2_000
_MAX_VISUAL_MODEL_BYTES = 2_000_000
_MAX_PARSER_RECORDS_PER_PAGE = 1_000
_MAX_PARSER_TEXT_PER_RECORD = 512
_MAX_PARSER_OBSERVATION_BYTES = 1_000_000
_MAX_CANONICAL_TEXT_BYTES = 750_000
_MAX_CANONICAL_SPAN_TEXT = 20_000
_MAX_EMBEDDED_ATTACHMENTS = 1_000
_MAX_ATTACHMENT_TREE_DEPTH = 16
_MAX_ATTACHMENT_TREE_NODES = 2_000


def _matrix_point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _matrix_multiply(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f)


def _canonical_box(points: list[tuple[float, float]], crop: list[float], rotation: int) -> list[float] | None:
    if not points:
        return None
    raw = [min(p[0] for p in points), min(p[1] for p in points),
           max(p[0] for p in points), max(p[1] for p in points)]
    try:
        return normalize_pdf_box(raw, crop_box=crop, rotation=rotation)
    except ValueError:
        return None


def _line_box(text: str, origin: tuple[float, float], font_size: float,
              crop: list[float], rotation: int) -> list[float] | None:
    """Return no made-up box when source font advances cannot be measured reliably."""
    if not text or not math.isfinite(font_size) or font_size <= 0:
        return None
    return _canonical_box([origin], crop, rotation)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)


def _raw_image_png(stream: Any) -> tuple[bytes, str] | None:
    """Wrap simple unfiltered 8-bit gray/RGB image XObjects as PNG without Pillow."""
    try:
        width, height = int(stream["/Width"]), int(stream["/Height"])
        bits = int(stream["/BitsPerComponent"])
        color = str(stream["/ColorSpace"])
        channels = {"/DeviceGray": 1, "/DeviceRGB": 3}.get(color)
        filters = stream.get("/Filter")
        if isinstance(filters, list):
            return None
        if filters in ("/DCTDecode", "/JPXDecode"):
            raw = stream._data
            media = "image/jpeg" if filters == "/DCTDecode" else "image/jp2"
            return raw, media
        if bits != 8 or channels is None or filters not in (None, "/FlateDecode"):
            return None
        parms = stream.get("/DecodeParms")
        if parms and int(parms.get("/Predictor", 1)) != 1:
            return None
        raw = stream.get_data()
        stride = width * channels
        if width < 1 or height < 1 or len(raw) != stride * height:
            return None
        scanlines = b"".join(b"\x00" + raw[row * stride:(row + 1) * stride] for row in range(height))
        color_type = 0 if channels == 1 else 2
        png = (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8,
                                                                          color_type, 0, 0, 0)) +
               _png_chunk(b"IDAT", zlib.compress(scanlines)) + _png_chunk(b"IEND", b""))
        return png, "image/png"
    except Exception:  # noqa: BLE001 - hostile PDF streams can raise parser-specific exception types.
        return None


def _text(page: Any, page_number: int, crop: list[float], rotation: int,
          include_characters: bool) -> tuple[dict[str, Any], list[str]]:
    spans: list[dict[str, Any]] = []
    diagnostics: list[str] = []

    def visit(text: str, cm: Any, tm: Any, font: Any, font_size: float) -> None:
        if not text:
            return
        try:
            matrix = tuple(float(v) for v in cm[:6])
            text_matrix = tuple(float(v) for v in tm[:6])
            origin = _matrix_point(matrix, text_matrix[4], text_matrix[5])
        except Exception:  # noqa: BLE001 - visitor geometry errors are downgraded to diagnostics.
            origin = (0.0, 0.0)
            diagnostics.append("text_position_unavailable")
        font_name = str(font.get("/BaseFont", "unknown")) if font else "unknown"
        clean_name = font_name.rsplit("+", 1)[-1].lstrip("/")
        descriptor = font.get("/FontDescriptor", {}) if font else {}
        flags = int(descriptor.get("/Flags", 0)) if descriptor else 0
        try:
            raw_size = float(font_size)
            size = round(raw_size, 3) if math.isfinite(raw_size) else None
        except (TypeError, ValueError):
            size = None
        span_index = len(spans)
        span_id = f"p{page_number}/pypdf-{PYPDF_VERSION}/s{span_index}"
        spans.append({"id": span_id, "page_number": page_number, "text": text,
                      "source_order": span_index,
                      "origin_pdf_user_space": [round(origin[0], 3), round(origin[1], 3)],
                      "origin": _canonical_box([origin], crop, rotation)[:2]
                      if _canonical_box([origin], crop, rotation) else None,
                      "box": None, "font": {"family": clean_name, "name": font_name,
                      "size_points": size,
                      "flags": flags, "bold": bool(flags & 262144) or "bold" in clean_name.casefold(),
                      "italic": bool(flags & 64) or "italic" in clean_name.casefold(),
                      "superscript": None, "underline": None, "strikethrough": None,
                      "color_rgb": None},
                      "source_method": "pypdf-text-visitor",
                      "source": {"parser": "pypdf", "version": PYPDF_VERSION,
                                 "span_index": span_index}})
        if "\ufffd" in text or "\x00" in text:
            diagnostics.append(f"text_encoding_suspect:{span_id}")

    try:
        page.extract_text(visitor_text=visit)
    except Exception:  # noqa: BLE001 - parser failures are reported per page.
        diagnostics.append("text_extraction_failed")
    lines: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    chars: list[dict[str, Any]] = []
    character_order = 0
    character_limit_reported = False
    for span in spans:
        span_line_ids: list[str] = []
        span_block_ids: list[str] = []
        for line_index, line_text in enumerate(span["text"].splitlines() or [span["text"]]):
            if not line_text:
                continue
            line_order = len(lines)
            block_order = len(blocks)
            line_id = f"p{page_number}/pypdf-{PYPDF_VERSION}/l{line_order}"
            block_id = f"p{page_number}/pypdf-{PYPDF_VERSION}/b{block_order}"
            lines.append({"id": line_id, "page_number": page_number, "text": line_text,
                          "block_id": block_id, "span_ids": [span["id"]],
                          "source_order": line_order, "box": None,
                          "source": {"parser": "pypdf", "version": PYPDF_VERSION,
                                     "line_index": line_order}})
            span_line_ids.append(line_id)
            span_block_ids.append(block_id)
            blocks.append({"id": block_id,
                           "page_number": page_number, "text": line_text,
                           "line_ids": [line_id], "source_order": block_order, "box": None,
                           "source": {"parser": "pypdf", "version": PYPDF_VERSION,
                                      "block_index": block_order}})
        span["line_ids"] = span_line_ids
        span["block_ids"] = span_block_ids
        span["character_ids"] = [] if include_characters else None
        if include_characters:
            for char in span["text"]:
                if len(chars) >= _MAX_ELEMENTS_PER_PAGE:
                    if not character_limit_reported:
                        diagnostics.append("character_limit_reached")
                        character_limit_reported = True
                    break
                char_id = f"p{page_number}/pypdf-{PYPDF_VERSION}/c{character_order}"
                chars.append({"id": char_id,
                              "page_number": page_number, "text": char,
                              "span_id": span["id"], "source_order": character_order,
                              "box": None,
                              "source": {"parser": "pypdf", "version": PYPDF_VERSION,
                                         "character_index": character_order}})
                span["character_ids"].append(char_id)
                character_order += 1
    if spans and not any(item["box"] for item in spans):
        diagnostics.append("text_bounds_unavailable_from_selected_parser")
    return ({"spans": spans[:_MAX_ELEMENTS_PER_PAGE], "lines": lines[:_MAX_ELEMENTS_PER_PAGE],
             "blocks": blocks[:_MAX_ELEMENTS_PER_PAGE],
             "characters": chars[:_MAX_ELEMENTS_PER_PAGE] if include_characters else None}, diagnostics)


def _pymupdf_canonical_text(data: bytes, *, include_characters: bool
                            ) -> tuple[list[dict[str, Any]] | None, str | None, list[str]]:
    """Build canonical hierarchy from PyMuPDF rawdict without merging parser orderings."""
    from importlib.metadata import version

    try:
        import pymupdf

        parser_version = version("PyMuPDF")
        document = pymupdf.open(stream=data, filetype="pdf")
        page_results: list[dict[str, Any]] = []
        try:
            for page_number, page in enumerate(document, 1):
                # Decorations are painted separately from glyphs in many PDFs. Ask
                # MuPDF to associate these vectors/annotations with extracted text.
                text_flags = pymupdf.TEXTFLAGS_RAWDICT | pymupdf.TEXT_COLLECT_STYLES
                raw = page.get_text("rawdict", flags=text_flags, sort=False)
                decoration_paths = _pymupdf_decoration_paths(page)
                blocks: list[dict[str, Any]] = []
                lines: list[dict[str, Any]] = []
                spans: list[dict[str, Any]] = []
                characters: list[dict[str, Any]] = []
                page_diagnostics: list[str] = []
                line_order = span_order = character_order = 0
                for block_index, raw_block in enumerate(raw.get("blocks", [])):
                    if raw_block.get("type") != 0:
                        continue
                    block_id = f"p{page_number}/pymupdf-{parser_version}/b{block_index}"
                    block_lines: list[str] = []
                    block_line_ids: list[str] = []
                    for line_index, raw_line in enumerate(raw_block.get("lines", [])):
                        line_id = f"{block_id}/l{line_index}"
                        line_spans: list[str] = []
                        line_span_ids: list[str] = []
                        for span_index, raw_span in enumerate(raw_line.get("spans", [])):
                            span_id = f"{line_id}/s{span_index}"
                            raw_chars = raw_span.get("chars", [])
                            raw_text = "".join(str(char.get("c", "")) for char in raw_chars)
                            text = raw_text[:_MAX_CANONICAL_SPAN_TEXT]
                            canonical_chars = raw_chars
                            if include_characters:
                                canonical_chars = []
                                char_text_length = 0
                                for raw_char in raw_chars:
                                    char_text = str(raw_char.get("c", ""))
                                    if char_text_length + len(char_text) > _MAX_CANONICAL_SPAN_TEXT:
                                        break
                                    canonical_chars.append(raw_char)
                                    char_text_length += len(char_text)
                                text = "".join(str(char.get("c", "")) for char in canonical_chars)
                            raw_bbox = [float(value) for value in raw_span.get("bbox", [])]
                            span_box = _pymupdf_box(pymupdf, raw_bbox, page.rotation_matrix,
                                                    float(page.rect.width), float(page.rect.height))
                            raw_origin = raw_span.get("origin")
                            origin = None
                            if raw_origin and len(raw_origin) == 2:
                                point = pymupdf.Point(float(raw_origin[0]), float(raw_origin[1])) * page.rotation_matrix
                                origin = [round(float(point.x), 3), round(float(point.y), 3)]
                            flags = int(raw_span.get("flags", 0))
                            char_flags_value = raw_span.get("char_flags")
                            char_flags = int(char_flags_value) if char_flags_value is not None else None
                            underlined = bool(char_flags & 2) if char_flags is not None else None
                            strikethrough = bool(char_flags & 1) if char_flags is not None else None
                            decoration_candidates = _pymupdf_decoration_candidates(
                                raw_bbox, decoration_paths, float(raw_span.get("size", 0)))
                            char_ids: list[str] | None = [] if include_characters else None
                            span_record = {
                                "id": span_id, "page_number": page_number, "block_id": block_id,
                                "line_id": line_id, "block_ids": [block_id], "line_ids": [line_id],
                                "text": text, "source_order": span_order,
                                "box": span_box, "source_box": raw_bbox or None,
                                "source_origin": [round(float(value), 3) for value in raw_origin]
                                if raw_origin else None,
                                "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                                "origin": origin,
                                "font": {
                                    "family": str(raw_span.get("font", ""))[:256],
                                    "name": str(raw_span.get("font", ""))[:256],
                                    "size_points": round(float(raw_span.get("size", 0)), 3),
                                    "flags": flags, "bold": bool(flags & 16),
                                    "italic": bool(flags & 2), "superscript": bool(flags & 1),
                                    "superscript_source": "pymupdf_computed_flag",
                                    "char_flags": char_flags,
                                    "underline": underlined, "strikethrough": strikethrough,
                                    "color_rgb": _pymupdf_rgb(int(raw_span.get("color", 0))),
                                },
                                "style_evidence": {
                                    "underline": {"source": "pymupdf_char_flags",
                                                  "value": underlined} if underlined is not None else
                                                 {"source": "unknown", "value": None},
                                    "strikethrough": {"source": "pymupdf_char_flags",
                                                      "value": strikethrough} if strikethrough is not None else
                                                     {"source": "unknown", "value": None},
                                    "decoration_candidates": decoration_candidates,
                                },
                                "character_ids": char_ids,
                                "source": {"parser": "pymupdf", "version": parser_version,
                                           "block_index": block_index, "line_index": line_index,
                                           "span_index": span_index},
                                "text_truncated": len(raw_text) > len(text),
                            }
                            spans.append(span_record)
                            line_spans.append(text)
                            line_span_ids.append(span_id)
                            if span_record["text_truncated"]:
                                page_diagnostics.append(f"text_span_truncated:{span_id}")
                            if "\ufffd" in text or "\x00" in text:
                                page_diagnostics.append(f"text_encoding_suspect:{span_id}")
                            if include_characters:
                                for char_index, raw_char in enumerate(canonical_chars):
                                    char_id = f"{span_id}/c{char_index}"
                                    raw_char_box = [float(value) for value in raw_char.get("bbox", [])]
                                    char_box = _pymupdf_box(pymupdf, raw_char_box, page.rotation_matrix,
                                                            float(page.rect.width), float(page.rect.height))
                                    characters.append({
                                        "id": char_id, "page_number": page_number,
                                        "block_id": block_id, "line_id": line_id,
                                        "span_id": span_id, "text": str(raw_char.get("c", "")),
                                        "source_order": character_order, "box": char_box,
                                        "source_box": raw_char_box or None,
                                        "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                                        "source": {"parser": "pymupdf", "version": parser_version,
                                                   "block_index": block_index, "line_index": line_index,
                                                   "span_index": span_index, "character_index": char_index},
                                    })
                                    char_ids.append(char_id)
                                    character_order += 1
                            span_order += 1
                        line_text = "".join(line_spans)
                        raw_line_box = [float(value) for value in raw_line.get("bbox", [])]
                        line_box = _pymupdf_box(pymupdf, raw_line_box, page.rotation_matrix,
                                                float(page.rect.width), float(page.rect.height))
                        lines.append({"id": line_id, "page_number": page_number,
                                      "block_id": block_id, "text": line_text,
                                      "source_order": line_order, "box": line_box,
                                      "source_box": raw_line_box or None,
                                      "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                                      "span_ids": line_span_ids,
                                      "source": {"parser": "pymupdf", "version": parser_version,
                                                 "block_index": block_index, "line_index": line_index}})
                        block_lines.append(line_text)
                        block_line_ids.append(line_id)
                        line_order += 1
                    raw_block_box = [float(value) for value in raw_block.get("bbox", [])]
                    blocks.append({"id": block_id, "page_number": page_number,
                                   "text": "\n".join(block_lines), "source_order": block_index,
                                   "box": _pymupdf_box(pymupdf, raw_block_box, page.rotation_matrix,
                                                       float(page.rect.width), float(page.rect.height)),
                                   "source_box": raw_block_box or None,
                                   "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                                   "line_ids": block_line_ids,
                                   "source": {"parser": "pymupdf", "version": parser_version,
                                              "block_index": block_index}})
                page_results.append({"page_number": page_number, "blocks": blocks, "lines": lines,
                                     "spans": spans,
                                     "characters": characters if include_characters else None,
                                     "diagnostics": page_diagnostics})
        finally:
            document.close()
        if _bound_canonical_hierarchy(page_results):
            diagnostics = ["canonical_text_document_limit_reached"]
        else:
            diagnostics = []
        return page_results, parser_version, diagnostics
    except Exception as exc:  # noqa: BLE001 - preserve the pypdf fallback on optional parser failures.
        return None, None, [f"pymupdf_canonical_text_unavailable:{type(exc).__name__}"]


def _pymupdf_box(pymupdf: Any, box: list[float], matrix: Any,
                 width: float, height: float) -> list[float] | None:
    if len(box) != 4:
        return None
    rect = pymupdf.Rect(*box) * matrix
    x0, y0 = max(0.0, float(rect.x0)), max(0.0, float(rect.y0))
    x1, y1 = min(width, float(rect.x1)), min(height, float(rect.y1))
    if x1 < x0 or y1 < y0:
        return None
    return [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]


def _pymupdf_rgb(value: int) -> list[int]:
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255]


def _pymupdf_decoration_paths(page: Any) -> list[tuple[str, list[float]]]:
    """Return bounded source-coordinate horizontal line/rect candidates."""
    paths: list[tuple[str, list[float]]] = []
    try:
        for drawing in page.get_drawings():
            for item in drawing.get("items", []):
                kind = item[0]
                if kind == "l" and len(item) >= 3:
                    first, second = item[1], item[2]
                    paths.append(("line", [float(first.x), float(first.y),
                                            float(second.x), float(second.y)]))
                elif kind == "re" and len(item) >= 2:
                    rect = item[1]
                    paths.append(("rect", [float(rect.x0), float(rect.y0),
                                            float(rect.x1), float(rect.y1)]))
                if len(paths) >= _MAX_VECTOR_PATHS_PER_PAGE * 8:
                    return paths
    except Exception:  # noqa: BLE001 - unsupported drawings leave style evidence unknown.
        return []
    return paths


def _pymupdf_decoration_candidates(span_box: list[float],
                                  paths: list[tuple[str, list[float]]],
                                  font_size: float) -> list[dict[str, Any]]:
    """Attach geometric candidates without treating nearby rules as certainty."""
    if len(span_box) != 4 or font_size <= 0:
        return []
    x0, y0, x1, y1 = span_box
    width, height = x1 - x0, y1 - y0
    if width <= 0 or height <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    for path_kind, box in paths:
        px0, py0, px1, py1 = box
        path_height = abs(py1 - py0)
        if path_height > max(1.0, height * 0.08):
            continue
        line_y = (py0 + py1) / 2
        line_x0, line_x1 = min(px0, px1), max(px0, px1)
        overlap = max(0.0, min(x1, line_x1) - max(x0, line_x0))
        if overlap / width < 0.5:
            continue
        style = None
        if y1 - height * 0.12 <= line_y <= y1 + min(font_size * 0.35, height * 0.5):
            style = "underline"
        elif y0 + height * 0.35 <= line_y <= y0 + height * 0.65:
            style = "strikethrough"
        if style:
            candidates.append({"style": style, "source": "pymupdf_drawing_geometry_candidate",
                               "geometry": [round(min(px0, px1), 3), round(min(py0, py1), 3),
                                            round(max(px0, px1), 3), round(max(py0, py1), 3)],
                               "path_kind": path_kind,
                               "overlap_fraction": round(overlap / width, 3)})
            if len(candidates) >= 4:
                break
    return candidates


def _pymupdf_json_value(value: Any) -> Any:
    """Convert MuPDF geometry values and drawing commands to JSON primitives."""
    if hasattr(value, "x") and hasattr(value, "y"):
        return [round(float(value.x), 3), round(float(value.y), 3)]
    if all(hasattr(value, key) for key in ("x0", "y0", "x1", "y1")):
        return [round(float(value.x0), 3), round(float(value.y0), 3),
                round(float(value.x1), 3), round(float(value.y1), 3)]
    if all(hasattr(value, key) for key in ("ul", "ur", "ll", "lr")):
        return {key: _pymupdf_json_value(getattr(value, key)) for key in ("ul", "ur", "ll", "lr")}
    if isinstance(value, (tuple, list)):
        return [_pymupdf_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return round(value, 6) if isinstance(value, float) else value
    return str(value)[:256]


def _pymupdf_visual_content(data: bytes, assets: dict[str, dict[str, Any]],
                           asset_bytes: list[int]
                           ) -> tuple[list[dict[str, Any]] | None, str | None, list[str]]:
    """Extract displayed image placements and complete bounded drawing paths."""
    from importlib.metadata import version

    try:
        import pymupdf

        parser_version = version("PyMuPDF")
        document = pymupdf.open(stream=data, filetype="pdf")
        page_results: list[dict[str, Any]] = []
        diagnostics: list[str] = []
        try:
            for page_number, page in enumerate(document, 1):
                page_diagnostics: list[str] = []
                image_records: list[dict[str, Any]] = []
                visual = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT |
                                       pymupdf.TEXT_PRESERVE_IMAGES, sort=False)
                image_blocks = [block for block in visual.get("blocks", [])
                                if block.get("type") == 1]
                if len(image_blocks) > _MAX_IMAGE_PLACEMENTS_PER_PAGE:
                    page_diagnostics.append("pymupdf_image_placement_limit_reached")
                    image_blocks = image_blocks[:_MAX_IMAGE_PLACEMENTS_PER_PAGE]

                def store_asset(payload: Any, ext: str, *, mask: bool = False) -> str | None:
                    if not isinstance(payload, bytes) or not payload:
                        return None
                    digest = hashlib.sha256(payload).hexdigest()
                    asset_id = digest[:32]
                    if asset_id in assets:
                        asset = assets[asset_id]
                        asset.setdefault("source_pages", [])
                        if page_number not in asset["source_pages"]:
                            asset["source_pages"].append(page_number)
                        return asset_id
                    if len(payload) > _MAX_IMAGE_BYTES or asset_bytes[0] + len(payload) > _MAX_DOCUMENT_ASSET_BYTES:
                        page_diagnostics.append("pymupdf_image_asset_limit_reached")
                        return None
                    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "jpx": "image/jp2",
                                  "png": "image/png", "tif": "image/tiff", "tiff": "image/tiff",
                                  "bmp": "image/bmp", "gif": "image/gif", "pnm": "image/x-portable-anymap",
                                  "jxr": "image/vnd.ms-photo"}.get(ext.casefold(), "application/octet-stream")
                    assets[asset_id] = {"id": asset_id, "sha256": digest,
                                        "media_type": media_type, "extension": ext[:16].casefold() or "bin",
                                        "byte_length": len(payload), "data_base64": base64.b64encode(payload).decode("ascii"),
                                        "source_pages": [page_number], "mask": mask}
                    asset_bytes[0] += len(payload)
                    return asset_id

                for placement_index, block in enumerate(image_blocks):
                    image = block.get("image")
                    ext = str(block.get("ext", "bin"))
                    asset_id = store_asset(image, ext)
                    mask_id = store_asset(block.get("mask"), "png", mask=True)
                    raw_bbox = [float(value) for value in block.get("bbox", [])]
                    box = _pymupdf_box(pymupdf, raw_bbox, page.rotation_matrix,
                                       float(page.rect.width), float(page.rect.height))
                    image_records.append({"id": f"p{page_number}/pymupdf-{parser_version}/image-{placement_index}",
                                          "page_number": page_number, "source_page": page_number,
                                          "source_order": int(block.get("number") or placement_index),
                                          "asset_id": asset_id, "mask_asset_id": mask_id,
                                          "sha256": hashlib.sha256(image).hexdigest() if isinstance(image, bytes) else None,
                                          "width_pixels": int(block.get("width", 0)),
                                          "height_pixels": int(block.get("height", 0)),
                                          "colorspace_components": int(block.get("colorspace", 0)),
                                          "bits_per_component": int(block.get("bpc", 0)),
                                          "media_type": {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                                          "jpx": "image/jp2", "png": "image/png",
                                                          "tif": "image/tiff", "tiff": "image/tiff"}.get(ext, None),
                                          "box": box, "source_box": raw_bbox or None,
                                          "source_transform": _pymupdf_json_value(block.get("transform")),
                                          "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                                          "parser": "pymupdf", "parser_version": parser_version})

                vector_records: list[dict[str, Any]] = []
                command_count = 0
                try:
                    drawings = page.get_drawings(extended=True)
                except TypeError:  # Compatibility with PyMuPDF builds without extended paths.
                    drawings = page.get_drawings()
                    page_diagnostics.append("pymupdf_extended_drawing_paths_unavailable")
                for path_index, drawing in enumerate(drawings):
                    items = drawing.get("items", [])
                    if len(vector_records) >= _MAX_VECTOR_PATHS_PER_PAGE or \
                            command_count + len(items) > _MAX_VECTOR_COMMANDS_PER_PAGE:
                        page_diagnostics.append("pymupdf_vector_command_limit_reached")
                        break
                    command_count += len(items)
                    raw_rect = _pymupdf_json_value(drawing.get("rect"))
                    vector_records.append({
                        "id": f"p{page_number}/pymupdf-{parser_version}/vector-{path_index}",
                        "page_number": page_number, "source_page": page_number,
                        "source_order": int(drawing.get("seqno") or path_index),
                        "box": _pymupdf_box(pymupdf, raw_rect if isinstance(raw_rect, list) else [],
                                             page.rotation_matrix, float(page.rect.width),
                                             float(page.rect.height)),
                        "source_box": raw_rect,
                        "source_coordinate_space": "pymupdf-unrotated-page-points-top-left",
                        "items": _pymupdf_json_value(items),
                        "item_count": len(items), "color": _pymupdf_json_value(drawing.get("color")),
                        "fill": _pymupdf_json_value(drawing.get("fill")),
                        "width_points": _pymupdf_json_value(drawing.get("width")),
                        "dashes": _pymupdf_json_value(drawing.get("dashes")),
                        "line_cap": _pymupdf_json_value(drawing.get("lineCap")),
                        "line_join": _pymupdf_json_value(drawing.get("lineJoin")),
                        "close_path": bool(drawing.get("closePath", False)),
                        "even_odd": drawing.get("even_odd"), "opacity": drawing.get("opacity"),
                        "stroke_opacity": drawing.get("stroke_opacity"),
                        "fill_opacity": drawing.get("fill_opacity"),
                        "type": drawing.get("type"), "sequence_number": drawing.get("seqno"),
                        "level": drawing.get("level"), "layer": drawing.get("layer"),
                        "scissor": _pymupdf_json_value(drawing.get("scissor")),
                        "parser": "pymupdf", "parser_version": parser_version,
                    })
                page_results.append({"page_number": page_number, "images": image_records,
                                     "vector_graphics": vector_records,
                                     "diagnostics": page_diagnostics})
        finally:
            document.close()
        return page_results, parser_version, diagnostics
    except Exception as exc:  # noqa: BLE001 - retain the pypdf visual adapter on optional failures.
        return None, None, [f"pymupdf_visual_content_unavailable:{type(exc).__name__}"]


def _bound_canonical_hierarchy(pages: list[dict[str, Any]]) -> bool:
    """Prune optional characters and trailing source subtrees to a document byte budget."""
    def size() -> int:
        payload = [{key: page[key] for key in ("blocks", "lines", "spans", "characters")}
                   for page in pages]
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    if size() <= _MAX_CANONICAL_TEXT_BYTES:
        return False
    truncated = False
    for page in reversed(pages):
        if page["characters"] is not None:
            page["characters"] = []
            for span in page["spans"]:
                span["character_ids"] = None
            page["diagnostics"].append("canonical_characters_truncated_document_limit")
            truncated = True
            if size() <= _MAX_CANONICAL_TEXT_BYTES:
                return truncated
    for page in reversed(pages):
        for key in ("blocks", "lines", "spans", "characters"):
            if page[key] is not None:
                page[key] = []
        page["diagnostics"].append("canonical_text_page_truncated_document_limit")
        truncated = True
        if size() <= _MAX_CANONICAL_TEXT_BYTES:
            return truncated
    if truncated and pages:
        pages[-1]["diagnostics"].append("canonical_text_document_limit_reached")
    return truncated


def _bound_visual_model(pages: list[dict[str, Any]]) -> bool:
    """Trim whole trailing visual records when the document-wide model is too large."""
    def size() -> int:
        payload = [{"images": page.get("images", []),
                    "vector_graphics": page.get("vector_graphics", [])} for page in pages]
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    if size() <= _MAX_VISUAL_MODEL_BYTES:
        return False
    for page in reversed(pages):
        while page.get("vector_graphics") and size() > _MAX_VISUAL_MODEL_BYTES:
            page["vector_graphics"].pop()
            page.setdefault("diagnostics", []).append("visual_model_document_limit_reached")
        if size() <= _MAX_VISUAL_MODEL_BYTES:
            return True
    for page in reversed(pages):
        while page.get("images") and size() > _MAX_VISUAL_MODEL_BYTES:
            page["images"].pop()
            page.setdefault("diagnostics", []).append("visual_model_document_limit_reached")
        if size() <= _MAX_VISUAL_MODEL_BYTES:
            return True
    return True


def _images_and_vectors(page: Any, page_number: int, crop: list[float], rotation: int,
                        assets: dict[str, dict[str, Any]], asset_bytes: list[int]
                        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    images: list[dict[str, Any]] = []
    vectors: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    contents = page.get_contents()
    if contents is None:
        return images, vectors, diagnostics
    resources = page.get("/Resources", {})
    xobjects = resources.get("/XObject", {}) if hasattr(resources, "get") else {}
    try:
        operations = ContentStream(contents, page.pdf).operations
    except Exception:  # noqa: BLE001 - malformed content streams are diagnostic, not fatal.
        return images, vectors, ["content_stream_unavailable"]
    identity = (1., 0., 0., 1., 0., 0.)
    matrix = identity
    stack: list[tuple[float, ...]] = []
    path_points: list[tuple[float, float]] = []
    pending_vectors: list[dict[str, Any]] = []
    stroke: Any = None
    fill: Any = None
    line_width = 1.0

    def finish_path(operator: bytes) -> None:
        if not path_points:
            return
        if len(pending_vectors) >= _MAX_VECTOR_PATHS_PER_PAGE:
            diagnostics.append("vector_path_limit_reached")
            path_points.clear()
            return
        pending_vectors.append({"id": f"p{page_number}-vector-{len(pending_vectors) + 1}",
                                "box": _canonical_box(path_points, crop, rotation),
                                "path_points_pdf_user_space": [[round(x, 3), round(y, 3)]
                                                                 for x, y in path_points[:512]],
                                "stroke_color": stroke, "fill_color": fill,
                                "stroke_width_points": round(line_width, 3),
                                "paint_operator": operator.decode("ascii", "replace"),
                                "source_order": current_operator_index,
                                "source_page": page_number})
        path_points.clear()

    for current_operator_index, (operands, operator) in enumerate(operations):
        try:
            if operator == b"q":
                stack.append(matrix)
            elif operator == b"Q":
                matrix = stack.pop() if stack else identity
            elif operator == b"cm" and len(operands) == 6:
                matrix = _matrix_multiply(matrix, tuple(float(v) for v in operands))
            elif operator == b"w" and operands:
                line_width = float(operands[0])
            elif operator in {b"RG", b"rg"}:
                color = [round(float(v), 4) for v in operands[:3]]
                if operator == b"RG": stroke = color
                else: fill = color
            elif operator in {b"G", b"g"}:
                color = [round(float(operands[0]), 4)] * 3
                if operator == b"G": stroke = color
                else: fill = color
            elif operator in {b"K", b"k"}:
                c, m, y, k = (float(v) for v in operands[:4])
                color = [round(1 - min(1, c * (1-k) + k), 4),
                         round(1 - min(1, m * (1-k) + k), 4),
                         round(1 - min(1, y * (1-k) + k), 4)]
                if operator == b"K": stroke = color
                else: fill = color
            elif operator == b"m" and len(operands) >= 2 or operator == b"l" and len(operands) >= 2:
                path_points.append(_matrix_point(matrix, float(operands[0]), float(operands[1])))
            elif operator == b"c" and len(operands) >= 6:
                path_points.extend(_matrix_point(matrix, float(operands[i]), float(operands[i+1]))
                                   for i in (0, 2, 4))
            elif operator in {b"v", b"y"} and len(operands) >= 4:
                path_points.extend(_matrix_point(matrix, float(operands[i]), float(operands[i+1]))
                                   for i in (0, 2))
            elif operator == b"re" and len(operands) >= 4:
                x, y, w, h = (float(v) for v in operands[:4])
                path_points.extend(_matrix_point(matrix, px, py) for px, py in
                                   ((x, y), (x+w, y), (x+w, y+h), (x, y+h)))
            elif operator in {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"}:
                finish_path(operator)
            elif operator == b"n":
                path_points.clear()
            elif operator == b"Do" and operands and xobjects:
                name = operands[0]
                obj = xobjects[name]
                if obj.get("/Subtype") != "/Image":
                    continue
                p0 = _matrix_point(matrix, 0, 0)
                p1 = _matrix_point(matrix, 1, 0)
                p2 = _matrix_point(matrix, 0, 1)
                p3 = _matrix_point(matrix, 1, 1)
                source_hash = None
                asset_id = None
                payload = _raw_image_png(obj)
                if payload:
                    binary, media_type = payload
                    source_hash = hashlib.sha256(binary).hexdigest()
                    asset_id = source_hash[:32]
                    if asset_id not in assets and len(binary) <= _MAX_IMAGE_BYTES and \
                            asset_bytes[0] + len(binary) <= _MAX_DOCUMENT_ASSET_BYTES:
                        extension = {"image/png": "png", "image/jpeg": "jpg", "image/jp2": "jp2"}.get(media_type, "bin")
                        assets[asset_id] = {"id": asset_id, "sha256": source_hash,
                                            "media_type": media_type, "extension": extension,
                                            "byte_length": len(binary),
                                            "data_base64": base64.b64encode(binary).decode("ascii")}
                        asset_bytes[0] += len(binary)
                    elif asset_id not in assets:
                        diagnostics.append(f"image_asset_limit_or_encoding_unavailable:{name}")
                images.append({"id": f"p{page_number}-image-{len(images) + 1}",
                               "resource_name": str(name), "asset_id": asset_id,
                               "sha256": source_hash,
                               "width_pixels": int(obj.get("/Width", 0)),
                               "height_pixels": int(obj.get("/Height", 0)),
                               "box": _canonical_box([p0, p1, p2, p3], crop, rotation),
                               "source_page": page_number, "source_order": current_operator_index})
        except Exception:  # noqa: BLE001 - unsupported operators are isolated and reported.
            diagnostics.append("unsupported_content_operator")
    finish_path(b"end")
    vectors = pending_vectors
    return images, vectors, diagnostics


def _safe_uri(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or len(value) > 2048:
        return None, "invalid_uri"
    parts = urlsplit(value.strip())
    if parts.scheme.casefold() not in {"http", "https", "mailto"}:
        return None, "unsupported_uri_scheme"
    if parts.scheme.casefold() in {"http", "https"} and not parts.hostname:
        return None, "invalid_uri"
    return value.strip(), None


def _deref_pdf_object(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _filespec_id(value: Any, fallback: str) -> str:
    reference = getattr(value, "indirect_reference", None)
    if reference is None and hasattr(value, "idnum"):
        reference = value
    object_number = getattr(reference, "idnum", None)
    return f"pdf-filespec-{object_number}" if object_number is not None else fallback


def _file_attachment_metadata(file_spec: Any) -> dict[str, Any]:
    """Read bounded file-spec metadata without reading/decompressing the stream."""
    spec = _deref_pdf_object(file_spec)
    spec = spec if hasattr(spec, "get") else {}
    embedded_files = _deref_pdf_object(spec.get("/EF", {}))
    embedded = None
    if hasattr(embedded_files, "get"):
        embedded_ref = embedded_files.get("/UF") or embedded_files.get("/F")
        if embedded_ref is not None:
            embedded = _deref_pdf_object(embedded_ref)
    params = _deref_pdf_object(embedded.get("/Params", {}) if hasattr(embedded, "get") else {})
    size = params.get("/Size") if hasattr(params, "get") else None
    try:
        declared_size = max(0, int(size)) if size is not None else None
    except (TypeError, ValueError, OverflowError):
        declared_size = None
    def text(value: Any, limit: int = 512) -> str | None:
        if value is None:
            return None
        return str(value).strip()[:limit] or None

    media_type = text(embedded.get("/Subtype")) if hasattr(embedded, "get") else None
    if media_type:
        media_type = re.sub(r"#([0-9A-Fa-f]{2})",
                            lambda match: chr(int(match.group(1), 16)), media_type.lstrip("/"))
    return {"filename": text(spec.get("/UF") or spec.get("/F")),
            "description": text(spec.get("/Desc")),
            "relationship": text(spec.get("/AFRelationship"), 64),
            "media_type": media_type,
            "declared_size_bytes": declared_size,
            "creation_date": text(params.get("/CreationDate")) if hasattr(params, "get") else None,
            "modification_date": text(params.get("/ModDate")) if hasattr(params, "get") else None,
            "payload_extracted": False}


def _document_embedded_files(reader: PdfReader
                             ) -> tuple[list[dict[str, Any]], list[str]]:
    """Walk the catalog EmbeddedFiles name tree with depth/node/entry limits."""
    attachments: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    try:
        catalog = _deref_pdf_object(reader.trailer.get("/Root", {}))
        names = _deref_pdf_object(catalog.get("/Names", {})) if hasattr(catalog, "get") else {}
        root = _deref_pdf_object(names.get("/EmbeddedFiles", {})) if hasattr(names, "get") else {}
    except Exception:  # noqa: BLE001 - malformed attachment trees remain isolated.
        return attachments, ["embedded_file_name_tree_unavailable"]
    if not hasattr(root, "get") or not root:
        return attachments, diagnostics

    visited: set[tuple[str, int]] = set()
    node_count = 0

    def walk(node_ref: Any, depth: int) -> None:
        nonlocal node_count
        if depth > _MAX_ATTACHMENT_TREE_DEPTH:
            diagnostics.append("embedded_file_tree_depth_limit_reached")
            return
        reference = getattr(node_ref, "indirect_reference", None)
        if reference is None and hasattr(node_ref, "idnum"):
            reference = node_ref
        identity = ("xref", int(reference.idnum)) if getattr(reference, "idnum", None) is not None \
            else ("direct", id(node_ref))
        if identity in visited:
            diagnostics.append("embedded_file_tree_cycle_or_duplicate_node")
            return
        visited.add(identity)
        node_count += 1
        if node_count > _MAX_ATTACHMENT_TREE_NODES:
            diagnostics.append("embedded_file_tree_node_limit_reached")
            return
        try:
            node = _deref_pdf_object(node_ref)
            if not hasattr(node, "get"):
                diagnostics.append("embedded_file_tree_node_invalid")
                return
            pairs = _deref_pdf_object(node.get("/Names", [])) or []
            if not isinstance(pairs, (list, tuple)) or len(pairs) % 2:
                diagnostics.append("embedded_file_tree_names_invalid")
            else:
                for offset in range(0, len(pairs) - 1, 2):
                    if len(attachments) >= _MAX_EMBEDDED_ATTACHMENTS:
                        diagnostics.append("embedded_file_attachment_limit_reached")
                        return
                    name = str(pairs[offset])[:512]
                    file_spec = pairs[offset + 1]
                    entry_index = len(attachments)
                    attachments.append({"id": _filespec_id(file_spec, f"embedded-file-{entry_index}"),
                                        "source": "document_embedded_files_name_tree",
                                        "name_tree_key": name,
                                        "file_attachment": _file_attachment_metadata(file_spec)})
            kids = _deref_pdf_object(node.get("/Kids", [])) or []
            if isinstance(kids, (list, tuple)):
                for child in kids:
                    walk(child, depth + 1)
            elif kids:
                diagnostics.append("embedded_file_tree_kids_invalid")
        except Exception:  # noqa: BLE001 - malformed nodes do not prevent other navigation data.
            diagnostics.append("embedded_file_tree_node_parse_failed")

    walk(root, 0)
    return attachments, list(dict.fromkeys(diagnostics))


def _navigation(reader: PdfReader) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    links: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    attachments, attachment_diagnostics = _document_embedded_files(reader)
    unsupported: list[dict[str, Any]] = []
    diagnostics: list[str] = list(attachment_diagnostics)
    for page_number, page in enumerate(reader.pages, 1):
        crop = [float(v) for v in page.cropbox]
        rotation = int(page.get("/Rotate", 0)) % 360
        for index, ref in enumerate(page.get("/Annots") or []):
            try:
                annot = ref.get_object()
                subtype = str(annot.get("/Subtype", "unknown")).lstrip("/")
                rect = [float(v) for v in annot.get("/Rect", [])]
                box = normalize_pdf_box(rect, crop_box=crop, rotation=rotation) if len(rect) == 4 else None
                common = {"id": f"p{page_number}-annot-{index+1}", "page_number": page_number,
                          "subtype": subtype, "box": box,
                          "contents": str(annot.get("/Contents", ""))[:10_000] or None,
                          "author": str(annot.get("/T", ""))[:512] or None,
                          "subject": str(annot.get("/Subj", ""))[:512] or None,
                          "modified": str(annot.get("/M", ""))[:128] or None}
                action = annot.get("/A")
                action = action.get_object() if action else {}
                if subtype == "Link":
                    target: dict[str, Any] = {}
                    if action.get("/URI") is not None:
                        uri, issue = _safe_uri(str(action["/URI"]))
                        if uri:
                            target["uri"] = uri
                        elif issue:
                            target["unsupported_reason"] = issue
                    elif annot.get("/Dest") is not None or action.get("/D") is not None:
                        destination = annot.get("/Dest", action.get("/D"))
                        try:
                            if isinstance(destination, (list, tuple)):
                                page_number = reader.get_page_number(destination[0])
                            elif isinstance(destination, str):
                                named = reader.named_destinations.get(destination)
                                page_number = reader.get_destination_page_number(named) if named else None
                            else:
                                page_number = reader.get_destination_page_number(destination)
                            if page_number is None:
                                raise ValueError("destination page not found")
                            target["page_number"] = int(page_number) + 1
                        except Exception:  # noqa: BLE001 - unresolved destinations are reported, never executed.
                            target["unsupported_reason"] = "unresolved_internal_destination"
                    else:
                        target["unsupported_reason"] = "unsupported_link_action"
                    links.append({**common, "target": target})
                if subtype == "FileAttachment":
                    spec = annot.get("/FS")
                    if spec is not None:
                        common["file_attachment"] = {
                            "id": _filespec_id(spec, f"annotation-file-p{page_number}-{index}"),
                            **_file_attachment_metadata(spec)}
                supported = {"Text", "FreeText", "Highlight", "Underline", "StrikeOut", "Squiggly", "Link", "Popup", "FileAttachment"}
                if subtype in supported:
                    annotations.append(common)
                else:
                    unsupported.append({"page_number": page_number, "subtype": subtype,
                                        "reason": "annotation type is not extracted"})
            except Exception:  # noqa: BLE001 - malformed annotations are isolated and reported.
                diagnostics.append(f"annotation_parse_failed:p{page_number}:{index+1}")
    bookmarks: list[dict[str, Any]] = []
    def walk(items: list[Any], level: int = 0) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            try:
                page_index = reader.get_destination_page_number(item)
                bookmarks.append({"title": str(item.title)[:1024], "level": level,
                                  "page_number": int(page_index) + 1 if page_index is not None else None})
            except Exception:  # noqa: BLE001 - malformed outline entries are isolated and reported.
                diagnostics.append("outline_destination_unavailable")
    try:
        walk(reader.outline)
    except Exception:  # noqa: BLE001 - outline parser errors are represented as diagnostics.
        diagnostics.append("outline_parse_failed")
    return links, annotations, bookmarks, attachments, unsupported, diagnostics


def _alternate_parser_observations(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """Collect bounded, parser-attributed observations without merging unlike geometries."""
    from importlib.metadata import version

    observations: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(BytesIO(data)) as pdf:
            for index, page in enumerate(pdf.pages):
                tables = page.find_tables()[:10]
                observations.append({"page_number": index + 1, "parser": "pdfplumber",
                                     "parser_version": version("pdfplumber"),
                                     "coordinate_space": "pdfplumber page coordinates; points; top-left origin",
                                     "character_count": len(page.chars),
                                     "characters": [{"text": str(c.get("text", ""))[:16],
                                                     "bbox": [round(float(c[k]), 3) for k in ("x0", "top", "x1", "bottom")],
                                                     "font": str(c.get("fontname", ""))[:256],
                                                     "size_points": round(float(c.get("size", 0)), 3)}
                                                    for c in page.chars[:_MAX_PARSER_RECORDS_PER_PAGE]],
                                     "tables": [{"bbox": [round(float(v), 3) for v in table.bbox],
                                                 "row_count": len(table.rows),
                                                 "cells": [[None if cell is None else
                                                            [round(float(v), 3) for v in cell]
                                                           for cell in row.cells[:20]]
                                                           for row in table.rows[:25]]}
                                                for table in tables]})
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(f"pdfplumber_unavailable_or_failed:{type(exc).__name__}")

    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTChar, LTFigure, LTTextBox, LTTextLine

        for page_number, layout in enumerate(extract_pages(BytesIO(data)), 1):
            counts = {"text_boxes": 0, "text_lines": 0, "characters": 0, "figures": 0}
            boxes: list[dict[str, Any]] = []
            def visit(item: Any, *, _counts: dict[str, int] = counts,
                      _boxes: list[dict[str, Any]] = boxes) -> None:
                if isinstance(item, LTTextBox):
                    _counts["text_boxes"] += 1
                    if len(_boxes) < _MAX_PARSER_RECORDS_PER_PAGE:
                        _boxes.append({"text": item.get_text()[:_MAX_PARSER_TEXT_PER_RECORD],
                                       "bbox": [round(float(v), 3) for v in item.bbox]})
                elif isinstance(item, LTTextLine):
                    _counts["text_lines"] += 1
                elif isinstance(item, LTChar):
                    _counts["characters"] += 1
                elif isinstance(item, LTFigure):
                    _counts["figures"] += 1
                if hasattr(item, "__iter__"):
                    for child in item:
                        visit(child)
            visit(layout)
            observations.append({"page_number": page_number, "parser": "pdfminer.six",
                                 "parser_version": version("pdfminer.six"),
                                 "coordinate_space": "pdfminer layout coordinates; PDF user space",
                                 **counts, "text_boxes": boxes})
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(f"pdfminer_six_unavailable_or_failed:{type(exc).__name__}")
    return observations, diagnostics


def _bound_parser_observations(observations: list[dict[str, Any]]) -> bool:
    """Keep optional cross-parser detail under a document-wide output budget."""
    if len(json.dumps(observations, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) <= \
            _MAX_PARSER_OBSERVATION_BYTES:
        return False
    truncated = False
    for observation in reversed(observations):
        for key in ("characters", "text_spans", "text_boxes", "tables", "drawings"):
            value = observation.get(key)
            if isinstance(value, list) and value:
                observation[key] = []
                observation["details_truncated"] = True
                truncated = True
                if len(json.dumps(observations, ensure_ascii=False,
                                  separators=(",", ":")).encode("utf-8")) <= \
                        _MAX_PARSER_OBSERVATION_BYTES:
                    return truncated
    return truncated


def extract_pdf_physical(data: bytes, *, include_characters: bool = False) -> dict[str, Any]:
    """Return bounded physical structure plus separately storable image payloads."""
    reader = PdfReader(BytesIO(data), strict=True)
    assets: dict[str, dict[str, Any]] = {}
    asset_bytes = [0]
    pymupdf_visual_pages, pymupdf_visual_version, pymupdf_visual_diagnostics = \
        _pymupdf_visual_content(data, assets, asset_bytes)
    if pymupdf_visual_pages is None:
        # A failed optional-parser pass may have registered some assets before
        # failing; discard that partial result before using the pypdf fallback.
        assets.clear()
        asset_bytes[0] = 0
    pages: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, 1):
        crop = [float(v) for v in page.cropbox]
        rotation = int(page.get("/Rotate", 0)) % 360
        text, text_diagnostics = _text(page, page_number, crop, rotation, include_characters)
        if pymupdf_visual_pages is not None and page_number <= len(pymupdf_visual_pages):
            visual_page = pymupdf_visual_pages[page_number - 1]
            images, vectors = visual_page["images"], visual_page["vector_graphics"]
            visual_diagnostics = visual_page["diagnostics"]
        else:
            images, vectors, visual_diagnostics = _images_and_vectors(
                page, page_number, crop, rotation, assets, asset_bytes)
        pages.append({"page_number": page_number, **text, "images": images,
                      "vector_graphics": vectors,
                      "diagnostics": list(dict.fromkeys(text_diagnostics + visual_diagnostics))})
    links, annotations, bookmarks, attachments, unsupported, navigation_diagnostics = _navigation(reader)
    canonical_pages, pymupdf_version, canonical_diagnostics = _pymupdf_canonical_text(
        data, include_characters=include_characters)
    if canonical_pages is not None:
        for page in pages:
            canonical = canonical_pages[page["page_number"] - 1]
            page.update({key: canonical[key] for key in ("blocks", "lines", "spans", "characters")})
            page["diagnostics"] = [item for item in page["diagnostics"]
                                   if not item.startswith("text_")]
            page["diagnostics"] = list(dict.fromkeys(page["diagnostics"] + canonical["diagnostics"]))
    elif _bound_canonical_hierarchy(pages):
        canonical_diagnostics.append("canonical_text_document_limit_reached")
    visual_model_truncated = _bound_visual_model(pages)
    referenced_asset_ids = {asset_id for page in pages for image in page.get("images", [])
                            for asset_id in (image.get("asset_id"), image.get("mask_asset_id"))
                            if asset_id}
    assets = {asset_id: asset for asset_id, asset in assets.items()
              if asset_id in referenced_asset_ids}
    observations, parser_diagnostics = _alternate_parser_observations(data)
    if _bound_parser_observations(observations):
        parser_diagnostics.append("parser_observation_document_limit_reached")
    for page in pages:
        page["parser_observations"] = [item for item in observations
                                       if item.get("page_number") == page["page_number"]]
    parser_versions = {"pypdf": PYPDF_VERSION}
    if pymupdf_version or pymupdf_visual_version:
        parser_versions["pymupdf"] = pymupdf_visual_version or pymupdf_version
    for observation in observations:
        parser_versions[observation["parser"]] = observation["parser_version"]
    return {"schema_version": 2, "engine": {"id": "pypdf", "version": PYPDF_VERSION},
            "canonical_text_engine": {"id": "pymupdf", "version": pymupdf_version}
            if pymupdf_version else {"id": "pypdf", "version": PYPDF_VERSION},
            "parsers": [{"id": parser_id, "version": parser_version}
                        for parser_id, parser_version in parser_versions.items()],
            "pages": pages, "links": links, "annotations": annotations,
            "bookmarks": bookmarks, "attachments": attachments, "unsupported": unsupported,
            "assets": list(assets.values()),
            "diagnostics": navigation_diagnostics + canonical_diagnostics +
                           pymupdf_visual_diagnostics + parser_diagnostics +
                           (["visual_model_document_limit_reached"] if visual_model_truncated else [])}
