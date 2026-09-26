"""Bounded PDF post-processing for TOC page references."""
from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject


_ANCHOR_MARKER = re.compile(r"__DOCPLATFORM_ANCHOR_([A-Za-z][A-Za-z0-9_-]{0,63})__")


class PdfTocError(ValueError):
    pass


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
            contents = page.get("/Contents")
            content_array = contents if isinstance(contents, ArrayObject) else ArrayObject([contents])
            content_array.append(stream_ref)
            page[NameObject("/Contents")] = content_array
        output = BytesIO()
        writer.write(output)
        result = output.getvalue()
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise PdfTocError(f"TOC page-number overlay failed: {exc}") from None
    if len(result) > max_bytes:
        raise PdfTocError("TOC output exceeds the configured size limit")
    return result
