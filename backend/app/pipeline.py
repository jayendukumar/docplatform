"""Typed, replaceable contracts for the document processing pipeline."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """A processing stage failed with a safe, user-facing reason."""

    def __init__(self, stage: str, code: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.message = message


class ProcessingArtifact(BaseModel):
    """Versioned data passed between independently replaceable stages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: int = 1
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=100)
    content: bytes = Field(repr=False)
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    classification: dict[str, Any] = Field(default_factory=dict)
    normalized: dict[str, Any] = Field(default_factory=dict)
    extracted: dict[str, Any] = Field(default_factory=dict)
    exported: dict[str, Any] = Field(default_factory=dict)


ArtifactT = TypeVar("ArtifactT")


class ProcessingStage(Protocol[ArtifactT]):
    """A single pipeline operation with a stable, independently callable contract."""

    stage_id: str

    def process(self, artifact: ArtifactT) -> ArtifactT: ...


class IngestionValidator(ProcessingStage[ProcessingArtifact], Protocol):
    stage_id: str


class DocumentClassifier(ProcessingStage[ProcessingArtifact], Protocol):
    stage_id: str


class DocumentNormalizer(ProcessingStage[ProcessingArtifact], Protocol):
    stage_id: str


class ContentExtractor(ProcessingStage[ProcessingArtifact], Protocol):
    stage_id: str


class ResultExporter(ProcessingStage[ProcessingArtifact], Protocol):
    stage_id: str


def run_pipeline(artifact: ArtifactT, stages: Sequence[ProcessingStage[ArtifactT]]) -> ArtifactT:
    """Run registered stages in order; callers may also invoke any stage directly."""
    result = artifact
    for stage in stages:
        logger.info("processing_stage_started", extra={"processing_stage": stage.stage_id})
        try:
            result = stage.process(result)
        except PipelineError:
            logger.warning("processing_stage_rejected", extra={"processing_stage": stage.stage_id})
            raise
        except Exception as exc:
            logger.error("processing_stage_failed", extra={
                "processing_stage": stage.stage_id,
                "error_type": type(exc).__name__,
            })
            raise PipelineError(stage.stage_id, "stage_failed",
                                f"Document processing failed during {stage.stage_id}") from exc
        logger.info("processing_stage_completed", extra={"processing_stage": stage.stage_id})
    return result
