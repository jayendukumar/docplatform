"""Bounded PDF post-processing for TOC page references."""
from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject

_ANCHOR_MARKER = re.compile(r"__DOCPLATFORM_ANCHOR_([A-Za-z][A-Za-z0-9_-]{0,63})__")


class PdfTocError(ValueError):
    pass


class PdfPageNumberError(ValueError):
    pass


def _append_overlay(writer: PdfWriter, page: Any, stream_ref: Any, isolated: set[int]) -> None:
    """Append an overlay stream after wrapping the page's original content in q/Q once (DD-429).

    Chromium leaves a scaling and y-flipping CTM active at the end of its content stream; without the
    q/Q isolation an appended overlay inherited it and was drawn at about 2 pt near the top-left corner.
    """
    contents = page.get("/Contents")
    content_array = contents if isinstance(contents, ArrayObject) else ArrayObject([contents] if contents is not None else [])
    if id(page) not in isolated:
        save, restore = DecodedStreamObject(), DecodedStreamObject()
        save.set_data(b"q\n")
        restore.set_data(b"\nQ\n")
        content_array.insert(0, writer._add_object(save))
        content_array.append(writer._add_object(restore))
        isolated.add(id(page))
    content_array.append(stream_ref)
    page[NameObject("/Contents")] = content_array


def add_page_numbers(pdf: bytes, margin_bottom_mm: float, margin_right_mm: float, max_bytes: int) -> bytes:
    """Overlay stable physical page numbers because Chromium does not resolve counter(page)."""
    if not pdf.startswith(b"%PDF-"):
        raise PdfPageNumberError("page-number input must be PDF")
    if len(pdf) > max_bytes:
        raise PdfPageNumberError("page-number input exceeds the configured size limit")
    try:
        reader = PdfReader(BytesIO(pdf), strict=False)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        if reader.metadata:
            writer.add_metadata({str(key): str(value) for key, value in reader.metadata.items() if value is not None})
        font_ref = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }))
        isolated: set[int] = set()
        bottom = max(12.0, float(margin_bottom_mm) * 72.0 / 25.4 / 2.0)
        right = max(12.0, float(margin_right_mm) * 72.0 / 25.4)
        for page_number, page in enumerate(writer.pages, start=1):
            width = float(page.mediabox.width)
            text = str(page_number)
            x = max(12.0, width - right - 18.0)
            stream = DecodedStreamObject()
            stream.set_data(f"BT /DPF1 9 Tf 1 0 0 1 {x:g} {bottom:g} Tm ({text}) Tj ET".encode())
            stream_ref = writer._add_object(stream)
            resources = page["/Resources"].get_object()
            fonts = resources.get("/Font")
            if fonts is None:
                fonts = DictionaryObject()
                resources[NameObject("/Font")] = fonts
            fonts[NameObject("/DPF1")] = font_ref
            _append_overlay(writer, page, stream_ref, isolated)
        output = BytesIO()
        writer.write(output)
        result = output.getvalue()
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise PdfPageNumberError(f"page-number overlay failed: {exc}") from None
    if len(result) > max_bytes:
        raise PdfPageNumberError("page-number output exceeds the configured size limit")
    return result


def add_toc_page_numbers(pdf: bytes, max_bytes: int) -> bytes:
    """Overlay physical page numbers beside same-document TOC link annotations."""
    if not pdf.startswith(b"%PDF-"):
        raise PdfTocError("TOC input must be PDF")
    if len(pdf) > max_bytes:
        raise PdfTocError("TOC input exceeds the configured size limit")
    try:
        reader = PdfReader(BytesIO(pdf), strict=False)
        anchor_pages: dict[str, int] = {}
        for page_number, page in enumerate(reader.pages, start=1):
            for anchor in _ANCHOR_MARKER.findall(page.extract_text() or ""):
                anchor_pages.setdefault(anchor, page_number)
        placements: list[tuple[int, float, float, int]] = []
        for page_index, page in enumerate(reader.pages):
            for annotation_ref in page.get("/Annots") or []:
                annotation = annotation_ref.get_object()
                if annotation.get("/Subtype") != "/Link":
                    continue
                destination = annotation.get("/Dest")
                rect = annotation.get("/Rect")
                anchor = str(destination).lstrip("/") if destination is not None else ""
                if anchor not in anchor_pages or not isinstance(rect, (list, tuple)) or len(rect) < 4:
                    continue
                placements.append((page_index, float(rect[2]) + 5, float(rect[1]) + 1, anchor_pages[anchor]))
        if not placements:
            return pdf
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        font_ref = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }))
        isolated = set()
        for page_index, x, y, page_number in placements:
            page = writer.pages[page_index]
            resources = page["/Resources"].get_object()
            fonts = resources.get("/Font")
            if fonts is None:
                fonts = DictionaryObject()
                resources[NameObject("/Font")] = fonts
            fonts[NameObject("/DPF1")] = font_ref
            stream = DecodedStreamObject()
            stream.set_data(f"BT /DPF1 9 Tf 1 0 0 1 {x:g} {y:g} Tm ({page_number}) Tj ET".encode())
            stream_ref = writer._add_object(stream)
            _append_overlay(writer, page, stream_ref, isolated)
        output = BytesIO()
        writer.write(output)
        result = output.getvalue()
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise PdfTocError(f"TOC page-number overlay failed: {exc}") from None
    if len(result) > max_bytes:
        raise PdfTocError("TOC output exceeds the configured size limit")
    return result
