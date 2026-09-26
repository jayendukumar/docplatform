"""Merge validated PDF page backgrounds behind generated foreground pages."""
from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader, PdfWriter, Transformation


class PdfBackgroundError(ValueError):
    pass


def merge_pdf_background(foreground: bytes, background: bytes, *, max_bytes: int) -> bytes:
    if not foreground.startswith(b"%PDF-") or not background.startswith(b"%PDF-"):
        raise PdfBackgroundError("foreground and background must be PDF documents")
    if len(background) > max_bytes:
        raise PdfBackgroundError("PDF background exceeds the configured size limit")
    try:
        foreground_reader = PdfReader(BytesIO(foreground), strict=True)
        background_reader = PdfReader(BytesIO(background), strict=True)
        if not foreground_reader.pages or not background_reader.pages:
            raise PdfBackgroundError("PDF background and foreground must contain pages")
        writer = PdfWriter()
        for index, page in enumerate(foreground_reader.pages):
            background_page = background_reader.pages[min(index, len(background_reader.pages) - 1)]
            foreground_width = float(page.mediabox.width)
            foreground_height = float(page.mediabox.height)
            background_width = float(background_page.mediabox.width)
            background_height = float(background_page.mediabox.height)
            if min(foreground_width, foreground_height, background_width, background_height) <= 0:
                raise PdfBackgroundError("PDF pages must have positive dimensions")
            scale = max(foreground_width / background_width, foreground_height / background_height)
            offset_x = (foreground_width - background_width * scale) / 2
            offset_y = (foreground_height - background_height * scale) / 2
            page.merge_transformed_page(background_page, Transformation().scale(scale).translate(offset_x, offset_y), over=False)
            writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        result = output.getvalue()
    except PdfBackgroundError:
        raise
    except Exception as exc:
        raise PdfBackgroundError("PDF background could not be parsed or merged") from exc
    if len(result) > max_bytes or not result.startswith(b"%PDF-"):
        raise PdfBackgroundError("merged PDF background output is invalid or too large")
    return result
