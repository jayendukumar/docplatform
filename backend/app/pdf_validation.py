"""Strict, bounded PDF inspection intended to run in an isolated worker."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pypdf import PdfReader

from app.pipeline import PipelineError, ProcessingArtifact
from app.pdf_geometry import display_size


def _metadata_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:512] or None


def inspect_pdf(artifact: ProcessingArtifact, *, max_pages: int) -> ProcessingArtifact:
    """Validate structure/encryption and return stable hash plus conservative metadata."""
    data = artifact.content
    if artifact.media_type != "application/pdf" or not data.startswith(b"%PDF-"):
        raise PipelineError("validate_pdf", "invalid_pdf_signature", "The uploaded file is not a PDF")
    if b"%%EOF" not in data[-2048:]:
        raise PipelineError("validate_pdf", "pdf_eof_missing", "The PDF is incomplete or malformed")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise PipelineError("validate_pdf", "pdf_encrypted", "Password-protected PDFs are not supported")
        if reader.trailer.get("/Root") is None:
            raise PipelineError("validate_pdf", "pdf_catalog_missing", "The PDF is malformed: document catalog is missing")
        pages = reader.pages
        page_count = len(pages)
        if page_count < 1:
            raise PipelineError("validate_pdf", "pdf_has_no_pages", "The PDF contains no pages")
        if page_count > max_pages:
            raise PipelineError("validate_pdf", "page_limit_exceeded", "Upload exceeds the configured page limit")
        page_metadata = []
        for number, page in enumerate(pages, start=1):
            box = page.mediabox
            crop = page.cropbox
            rotation = int(page.get("/Rotate", 0)) % 360
            display_width, display_height = display_size(crop, rotation)
            page_metadata.append({
                "page_number": number,
                "width_points": round(display_width, 3),
                "height_points": round(display_height, 3),
                "rotation": rotation,
                "coordinate_system": "top-left-points",
                "media_box_pdf_user_space": [round(float(v), 3) for v in box],
                "crop_box_pdf_user_space": [round(float(v), 3) for v in crop],
                "original_width_points": round(float(box.width), 3),
                "original_height_points": round(float(box.height), 3),
            })
        raw_metadata = reader.metadata
        metadata = {
            "page_count": page_count,
            "pages": page_metadata,
            "title": _metadata_text(raw_metadata.title if raw_metadata else None),
            "author": _metadata_text(raw_metadata.author if raw_metadata else None),
            "creator": _metadata_text(raw_metadata.creator if raw_metadata else None),
            "producer": _metadata_text(raw_metadata.producer if raw_metadata else None),
            "creation_date": _metadata_text(raw_metadata.creation_date if raw_metadata else None),
            "modification_date": _metadata_text(raw_metadata.modification_date if raw_metadata else None),
        }
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError("validate_pdf", "pdf_malformed", "The PDF is malformed or unsupported") from exc
    return artifact.model_copy(update={"sha256": hashlib.sha256(data).hexdigest(), "metadata": metadata})


@dataclass(frozen=True)
class PdfValidationStage:
    """Replaceable PDF validation stage implementing the pipeline contract."""

    max_pages: int
    stage_id: str = "validate_pdf"

    def process(self, artifact: ProcessingArtifact) -> ProcessingArtifact:
        return inspect_pdf(artifact, max_pages=self.max_pages)
