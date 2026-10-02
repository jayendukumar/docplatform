"""Raster (visual) comparison of source and candidate PDFs (E16-06, DD-420).

Pages are rendered offline with pypdfium2 (fidelity tooling only, DD-419),
thresholded to ink masks and compared exactly and within a positional
tolerance. Pixel arithmetic uses Python big integers over 0/1 byte masks, so
no NumPy or Pillow is needed. Optional diff images are indexed PNGs:
white = no ink, grey = matching ink, red = source ink with no candidate ink
nearby (missing), blue = candidate ink with no source ink nearby (extra).

Scores are diagnostics; they do not establish native-reader or visual approval.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

VISUAL_VERSION = "fidelity-visual-v1"
DEFAULT_DPI = 72
DEFAULT_TOLERANCE_MM = 1.0
INK_THRESHOLD = 160
CELL_MM = 10.0
TOP_CELLS = 5
MAX_PAGES = 500
MM_PER_INCH = 25.4

_INK = bytes(1 if value < INK_THRESHOLD else 0 for value in range(256))
_PALETTE = bytes((255, 255, 255, 220, 40, 40, 40, 90, 220, 90, 90, 90))  # none, missing, extra, matched


def rasterizer_status() -> str:
    try:
        import pypdfium2  # noqa: F401
    except ImportError:
        return "unavailable-no-rasterizer"
    return "available"


def _render(data: bytes, dpi: int) -> list[tuple[int, int, bytes]]:
    import pypdfium2

    document = pypdfium2.PdfDocument(data)
    try:
        if len(document) > MAX_PAGES:
            raise ValueError(f"PDF exceeds {MAX_PAGES} pages")
        pages = []
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=dpi / 72, grayscale=True)
            width, height, stride = bitmap.width, bitmap.height, bitmap.stride
            buffer = bytes(bitmap.buffer)
            rows = buffer if stride == width else b"".join(
                buffer[row * stride:row * stride + width] for row in range(height))
            pages.append((width, height, rows.translate(_INK)))
            bitmap.close()
            page.close()
        return pages
    finally:
        document.close()


class _Mask:
    """A 0/1 byte mask with ``pad`` zero columns each side, held as a big integer."""

    def __init__(self, mask: bytes, width: int, height: int, crop_width: int, crop_height: int, pad: int) -> None:
        self.width, self.height, self.pad = crop_width, crop_height, pad
        self.row = crop_width + 2 * pad
        blank = bytes(pad)
        padded = b"".join(blank + mask[r * width:r * width + crop_width] + blank for r in range(crop_height))
        self.value = int.from_bytes(padded, "big")
        self.length = len(padded)

    def count(self, value: int | None = None) -> int:
        return (self.value if value is None else value).bit_count()

    def dilate(self, radius: int) -> int:
        horizontal = self.value
        for step in range(1, radius + 1):
            horizontal |= (self.value << (8 * step)) | (self.value >> (8 * step))
        result = horizontal
        for step in range(1, radius + 1):
            shift = 8 * self.row * step
            result |= (horizontal << shift) | (horizontal >> shift)
        return result & ((1 << (8 * self.length)) - 1)

    def ones(self) -> int:
        return int.from_bytes(b"\x01" * self.length, "big")

    def to_bytes(self, value: int) -> bytes:
        return value.to_bytes(self.length, "big")


def _write_png(path: Path, width: int, height: int, indexed_rows: bytes, row_length: int, pad: int) -> None:
    raw = b"".join(b"\x00" + indexed_rows[r * row_length + pad:r * row_length + pad + width] for r in range(height))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
                     + chunk(b"PLTE", _PALETTE) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _cells(missing: bytes, extra: bytes, mask: _Mask, dpi: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the worst cells and the full grid of per-cell missing/extra pixel counts."""
    cell = max(1, round(CELL_MM / MM_PER_INCH * dpi))
    found = []
    grid_missing: list[list[int]] = []
    grid_extra: list[list[int]] = []
    for top in range(0, mask.height, cell):
        bottom = min(mask.height, top + cell)
        grid_missing.append([])
        grid_extra.append([])
        for left in range(0, mask.width, cell):
            right = min(mask.width, left + cell)
            missing_count = extra_count = 0
            for row in range(top, bottom):
                start = row * mask.row + mask.pad
                missing_count += missing[start + left:start + right].count(1)
                extra_count += extra[start + left:start + right].count(1)
            grid_missing[-1].append(missing_count)
            grid_extra[-1].append(extra_count)
            if missing_count or extra_count:
                scale = MM_PER_INCH / dpi
                found.append({"box_mm": [round(left * scale, 1), round(top * scale, 1),
                                         round(right * scale, 1), round(bottom * scale, 1)],
                              "missing_px": missing_count, "extra_px": extra_count})
    found.sort(key=lambda c: -(c["missing_px"] + c["extra_px"]))
    grid = {"cell_mm": round(cell * MM_PER_INCH / dpi, 3), "missing_px": grid_missing, "extra_px": grid_extra}
    return found[:TOP_CELLS], grid


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _f1(recall: float | None, precision: float | None) -> float | None:
    if recall is None or precision is None:
        return None
    return round(2 * recall * precision / (recall + precision), 4) if recall + precision else 0.0


def compare_visual(source: bytes, candidate: bytes, *, dpi: int = DEFAULT_DPI,
                   tolerance_mm: float = DEFAULT_TOLERANCE_MM, diff_dir: Path | None = None) -> dict[str, Any]:
    """Compare rendered pages; returns per-page and summary ink-overlap metrics."""
    if rasterizer_status() != "available":
        return {"contract": VISUAL_VERSION, "status": "unavailable-no-rasterizer", "pages": [], "summary": None}
    if not 18 <= dpi <= 300:
        raise ValueError("dpi must be between 18 and 300")
    radius = max(0, round(tolerance_mm / MM_PER_INCH * dpi))
    source_pages, candidate_pages = _render(source, dpi), _render(candidate, dpi)
    pages: list[dict[str, Any]] = []
    totals = {"source": 0, "candidate": 0, "near_source": 0, "near_candidate": 0}
    for index in range(max(len(source_pages), len(candidate_pages))):
        if index >= len(source_pages) or index >= len(candidate_pages):
            pages.append({"page_number": index + 1, "status": "missing-in-" + ("source" if index >= len(source_pages) else "candidate")})
            continue
        (sw, sh, smask), (cw, ch, cmask) = source_pages[index], candidate_pages[index]
        width, height = min(sw, cw), min(sh, ch)
        a = _Mask(smask, sw, sh, width, height, radius)
        b = _Mask(cmask, cw, ch, width, height, radius)
        dilated_a, dilated_b = a.dilate(radius), b.dilate(radius)
        ones = a.ones()
        source_ink, candidate_ink = a.count(), b.count()
        exact = a.count(a.value & b.value)
        union = a.count(a.value | b.value)
        source_near = a.count(a.value & dilated_b)       # source ink with candidate ink nearby
        candidate_near = b.count(b.value & dilated_a)    # candidate ink with source ink nearby
        recall, precision = _ratio(source_near, source_ink), _ratio(candidate_near, candidate_ink)
        f1 = _f1(recall, precision)
        missing_value = a.value & (ones ^ dilated_b)
        extra_value = b.value & (ones ^ dilated_a)
        missing, extra = a.to_bytes(missing_value), a.to_bytes(extra_value)
        worst, grid = _cells(missing, extra, a, dpi)
        entry = {"page_number": index + 1, "status": "compared",
                 "size_px": {"source": [sw, sh], "candidate": [cw, ch], "compared": [width, height]},
                 "ink_px": {"source": source_ink, "candidate": candidate_ink},
                 "ink_ratio": _ratio(candidate_ink, source_ink),
                 "exact_iou": _ratio(exact, union),
                 "tolerant": {"recall": recall, "precision": precision, "f1": f1},
                 "worst_cells": worst, "cell_grid": grid}
        if diff_dir is not None:
            matched = (a.value | b.value) & (ones ^ (missing_value | extra_value))
            indexed = a.to_bytes(missing_value + 2 * extra_value + 3 * (matched & ones))
            image = diff_dir / f"page-{index + 1:03d}.png"
            _write_png(image, width, height, indexed, a.row, radius)
            entry["diff_image"] = str(image)
        pages.append(entry)
        totals["source"] += source_ink
        totals["candidate"] += candidate_ink
        totals["near_source"] += source_near
        totals["near_candidate"] += candidate_near
    compared = [p for p in pages if p["status"] == "compared"]
    recall = _ratio(totals["near_source"], totals["source"])
    precision = _ratio(totals["near_candidate"], totals["candidate"])
    f1 = _f1(recall, precision)
    page_f1 = [p["tolerant"]["f1"] for p in compared if p["tolerant"]["f1"] is not None]
    return {
        "contract": VISUAL_VERSION, "status": "compared",
        "settings": {"renderer": "pypdfium2", "dpi": dpi, "tolerance_mm": tolerance_mm, "tolerance_px": radius,
                     "ink_threshold": INK_THRESHOLD, "cell_mm": CELL_MM},
        "summary": {"pages_compared": len(compared),
                    "page_size_mismatches": [p["page_number"] for p in compared
                                             if p["size_px"]["source"] != p["size_px"]["candidate"]],
                    "ink_ratio": _ratio(totals["candidate"], totals["source"]),
                    "tolerant": {"recall": recall, "precision": precision, "f1": f1},
                    "page_f1": {"mean": round(sum(page_f1) / len(page_f1), 4) if page_f1 else None,
                                "min": min(page_f1) if page_f1 else None,
                                "pages_below_0_5": [p["page_number"] for p in compared
                                                    if p["tolerant"]["f1"] is not None and p["tolerant"]["f1"] < 0.5]}},
        "pages": pages,
        "limitations": ["Single-engine raster (PDFium); not native-reader or second-engine evidence.",
                        "Binary ink masks ignore colour and grey levels above the threshold."],
    }
