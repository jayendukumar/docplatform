"""Conservative per-page PDF classification with inspectable evidence."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.generic import ContentStream


@dataclass(frozen=True)
class PageClassificationThresholds:
    min_text_characters: int = 20
    scan_image_coverage: float = 0.65
    mixed_image_coverage: float = 0.05

    def __post_init__(self) -> None:
        if self.min_text_characters < 0:
            raise ValueError("min_text_characters must be non-negative")
        if not 0 <= self.mixed_image_coverage <= self.scan_image_coverage <= 1:
            raise ValueError("image coverage thresholds must be ordered between 0 and 1")


def _multiply(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*l+e, b*k+d*l+f)


def _image_coverage(page: Any, page_area: float) -> tuple[float, int]:
    """Estimate placed image area from image XObject Do operators and their CTMs."""
    if page_area <= 0 or page.get_contents() is None:
        return 0.0, 0
    resources = page.get("/Resources", {})
    xobjects = resources.get("/XObject", {}) if hasattr(resources, "get") else {}
    try:
        content = ContentStream(page.get_contents(), page.pdf)
    except Exception:
        return 0.0, 0
    identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    matrix = identity
    stack: list[tuple[float, ...]] = []
    area = 0.0
    count = 0
    for operands, operator in content.operations:
        if operator == b"q":
            stack.append(matrix)
        elif operator == b"Q":
            matrix = stack.pop() if stack else identity
        elif operator == b"cm" and len(operands) == 6:
            matrix = _multiply(matrix, tuple(float(v) for v in operands))
        elif operator == b"Do" and operands and xobjects:
            try:
                obj = xobjects[operands[0]]
                if obj.get("/Subtype") == "/Image":
                    count += 1
                    area += abs(matrix[0] * matrix[3] - matrix[1] * matrix[2])
            except Exception:
                continue
    return min(1.0, area / page_area), count


def classify_pdf_pages(data: bytes, thresholds: PageClassificationThresholds | None = None) -> list[dict[str, Any]]:
    """Return per-page kind and evidence metrics; does not imply OCR/layout support."""
    limits = thresholds or PageClassificationThresholds()
    reader = PdfReader(BytesIO(data), strict=True)
    results: list[dict[str, Any]] = []
    for number, page in enumerate(reader.pages, 1):
        crop = page.cropbox
        rotation = int(page.get("/Rotate", 0)) % 360
        width, height = float(crop.width), float(crop.height)
        text = page.extract_text() or ""
        characters = sum(not char.isspace() for char in text)
        coverage, placements = _image_coverage(page, width * height)
        if coverage >= limits.scan_image_coverage and characters < limits.min_text_characters:
            kind = "scanned"
        elif coverage >= limits.mixed_image_coverage and placements and characters >= limits.min_text_characters:
            kind = "mixed-content"
        elif characters > 0:
            kind = "native-text"
        else:
            kind = "scanned"
        results.append({"page_number": number, "classification": kind,
                        "metrics": {"text_character_count": characters,
                                    "text_character_coverage": None,
                                    "image_coverage": round(coverage, 6),
                                    "image_placement_count": placements,
                                    "page_area_points": round(width * height, 3)},
                        "thresholds": {"min_text_characters": limits.min_text_characters,
                                       "scan_image_coverage": limits.scan_image_coverage,
                                       "mixed_image_coverage": limits.mixed_image_coverage},
                        "evidence": ["pypdf extracted character count", "image XObject placement transforms"],
                        "rotation": rotation})
    return results
