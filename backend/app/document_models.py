"""Versioned E22 logical and combined document contracts."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BBoxModel(BaseModel):
    """Top-left point coordinates in the displayed, cropped page space."""

    model_config = ConfigDict(extra="forbid")

    box: list[float] | None = None


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1, max_length=128)
    score: float = Field(ge=0, le=1)
    facts: list[str] = Field(default_factory=list, max_length=32)
    source_element_ids: list[str] = Field(default_factory=list, max_length=5000)


class ReadingOrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    element_id: str = Field(min_length=1, max_length=256)
    element_type: Literal["text_block", "image", "vector", "table"]
    original_source_order: int | None = None
    region_id: str | None = None
    column_id: str | None = None
    evidence: EvidenceModel


class LayoutRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    type: Literal["text_region", "spanning_region", "visual_region", "table_region", "whitespace_separator"]
    box: list[float] | None = None
    child_element_ids: list[str] = Field(default_factory=list, max_length=20000)
    parent_region_id: str | None = None
    column_id: str | None = None
    evidence: EvidenceModel


class LayoutColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    index: int = Field(ge=0)
    box: list[float]
    text_block_ids: list[str] = Field(default_factory=list, max_length=10000)
    evidence: EvidenceModel


class LayoutPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    regions: list[LayoutRegion] = Field(default_factory=list, max_length=10000)
    columns: list[LayoutColumn] = Field(default_factory=list, max_length=64)
    whitespace_separators: list[list[float]] = Field(default_factory=list, max_length=64)
    reading_order: list[ReadingOrderItem] = Field(default_factory=list, max_length=20000)
    original_order: list[str] = Field(default_factory=list, max_length=20000)
    diagnostics: list[str] = Field(default_factory=list, max_length=1000)


class StyleRun(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    source_span_ids: list[str] = Field(default_factory=list)
    font: dict[str, Any] = Field(default_factory=dict)


class LogicalParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    type: Literal["title", "heading", "paragraph", "list_item", "header", "footer", "page_number", "caption"]
    text: str
    box: list[float] | None = None
    page_number: int = Field(ge=1)
    source_line_ids: list[str] = Field(default_factory=list, max_length=10000)
    source_span_ids: list[str] = Field(default_factory=list, max_length=20000)
    original_source_order: list[int] = Field(default_factory=list, max_length=10000)
    style_runs: list[StyleRun] = Field(default_factory=list, max_length=20000)
    heading_level: int | None = Field(default=None, ge=1, le=6)
    list_id: str | None = None
    list_level: int | None = Field(default=None, ge=0, le=32)
    list_marker: str | None = None
    section_id: str | None = None
    continuation_id: str | None = None
    associations: list[dict[str, Any]] = Field(default_factory=list, max_length=128)
    evidence: EvidenceModel


class LogicalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    title: str
    level: int = Field(ge=1, le=6)
    parent_id: str | None = None
    child_section_ids: list[str] = Field(default_factory=list, max_length=10000)
    paragraph_ids: list[str] = Field(default_factory=list, max_length=20000)
    page_numbers: list[int] = Field(default_factory=list, max_length=10000)
    source_element_ids: list[str] = Field(default_factory=list, max_length=20000)
    evidence: EvidenceModel


class ListItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_id: str
    marker: str
    level: int = Field(ge=0, le=32)
    ordinal: int | None = Field(default=None, ge=1)
    source_element_ids: list[str] = Field(default_factory=list, max_length=10000)


class LogicalList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ordered: bool
    marker_kind: Literal["bullet", "decimal", "alphabetic", "roman", "unknown"]
    page_numbers: list[int] = Field(default_factory=list)
    items: list[ListItemModel] = Field(default_factory=list, max_length=20000)
    evidence: EvidenceModel


class TableCellModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int = Field(ge=0)
    column: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    text: str | None = None
    box: list[float] | None = None
    source_span_ids: list[str] = Field(default_factory=list)
    merged_continuation: bool = False


class TableSegmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    continuation_group_id: str | None = None
    page_number: int = Field(ge=1)
    box: list[float] | None = None
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    cells: list[TableCellModel] = Field(default_factory=list, max_length=100000)
    header_row_indices: list[int] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)
    detection_method: str
    status: Literal["extracted", "candidate", "unsupported"]
    diagnostics: list[str] = Field(default_factory=list)
    evidence: EvidenceModel


class LogicalPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    title_id: str | None = None
    paragraph_ids: list[str] = Field(default_factory=list)
    heading_ids: list[str] = Field(default_factory=list)
    list_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    header_ids: list[str] = Field(default_factory=list)
    footer_ids: list[str] = Field(default_factory=list)
    page_number_ids: list[str] = Field(default_factory=list)
    visual_candidates: list[dict[str, Any]] = Field(default_factory=list)
    captions: list[dict[str, Any]] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class LogicalDocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    schema_id: Literal["e22-logical-document"] = "e22-logical-document"
    analysis_engine: dict[str, str]
    configuration: dict[str, Any] = Field(default_factory=dict)
    pages: list[LogicalPage]
    layout_pages: list[LayoutPage]
    paragraphs: list[LogicalParagraph]
    sections: list[LogicalSection]
    lists: list[LogicalList]
    tables: list[TableSegmentModel]
    diagnostics: list[str] = Field(default_factory=list)


class PhysicalContentModel(BaseModel):
    """Stable top-level contract for the existing additive physical model."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal[2]
    engine: dict[str, str]
    canonical_text_engine: dict[str, str]
    parsers: list[dict[str, str]]
    pages: list[dict[str, Any]]
    links: list[dict[str, Any]]
    annotations: list[dict[str, Any]]
    bookmarks: list[dict[str, Any]]
    attachments: list[dict[str, Any]]
    unsupported: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    diagnostics: list[str]


class CanonicalDocumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    schema_id: Literal["e22-canonical-document"] = "e22-canonical-document"
    source: dict[str, Any]
    processing: dict[str, Any] = Field(default_factory=dict)
    physical_content: PhysicalContentModel
    logical_content: LogicalDocumentModel
