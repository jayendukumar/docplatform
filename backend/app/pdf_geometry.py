"""PDF user-space geometry mapped to the PageModel top-left point convention."""
from __future__ import annotations

from typing import Iterable


def normalize_pdf_box(box: Iterable[float], *, crop_box: Iterable[float], rotation: int) -> list[float]:
    """Transform a source PDF box (bottom-left origin) to cropped, rotated top-left points."""
    x0, y0, x1, y1 = (float(value) for value in box)
    cx0, cy0, cx1, cy1 = (float(value) for value in crop_box)
    angle = int(rotation) % 360
    if angle not in {0, 90, 180, 270}:
        raise ValueError("PDF page rotation must be 0, 90, 180, or 270 degrees")
    width, height = cx1 - cx0, cy1 - cy0
    if width <= 0 or height <= 0:
        raise ValueError("PDF crop box must have positive dimensions")

    def point(x: float, y: float) -> tuple[float, float]:
        x -= cx0
        y -= cy0
        if angle == 0:
            return x, height - y
        if angle == 90:
            return y, x
        if angle == 180:
            return width - x, y
        return height - y, width - x

    points = [point(x, y) for x in (x0, x1) for y in (y0, y1)]
    return [round(min(p[0] for p in points), 3), round(min(p[1] for p in points), 3),
            round(max(p[0] for p in points), 3), round(max(p[1] for p in points), 3)]


def display_size(crop_box: Iterable[float], rotation: int) -> tuple[float, float]:
    x0, y0, x1, y1 = (float(value) for value in crop_box)
    width, height = x1 - x0, y1 - y0
    return (height, width) if int(rotation) % 180 else (width, height)
