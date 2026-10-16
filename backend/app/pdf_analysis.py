"""Deterministic, source-linked layout and logical analysis for E22 PDF data."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from statistics import median
from typing import Any

from app.document_models import (
    CanonicalDocumentModel,
    EvidenceModel,
    LayoutColumn,
    LayoutPage,
    LayoutRegion,
    ListItemModel,
    LogicalDocumentModel,
    LogicalList,
    LogicalPage,
    LogicalParagraph,
    LogicalSection,
    ReadingOrderItem,
    StyleRun,
    TableSegmentModel,
)

ANALYSIS_VERSION = "e22-layout-rules/1.0"
_NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?|[IVXLCDM]+[.)])\s+\S", re.IGNORECASE)
_CAPTION = re.compile(r"^(figure|fig\.|table|chart|diagram)\s+([A-Z0-9.\-]+)\b", re.IGNORECASE)
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?\d{1,5}(?:\s+(?:of|/)\s+\d{1,5})?$", re.IGNORECASE)
_LIST_MARKER = re.compile(
    r"^\s*(?P<marker>(?:[-*+•▪◦‣])|(?:\(?\d{1,4}[.)])|(?:\(?[A-Za-z][.)])|(?:\(?[IVXLCDMivxlcdm]+[.)]))\s+(?P<text>.+)$"
)


def _box(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        values = [float(item) for item in value]
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(item) for item in values) or values[2] < values[0] or values[3] < values[1]:
        return None
    return values


def _overlap(left: list[float], right: list[float]) -> float:
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    area = width * height
    union = max(0.0, (left[2] - left[0]) * (left[3] - left[1])) + \
        max(0.0, (right[2] - right[0]) * (right[3] - right[1])) - area
    return area / union if union else 0.0


def _inside(inner: list[float], outer: list[float], tolerance: float = 0.0) -> bool:
    return (inner[0] >= outer[0] - tolerance and inner[1] >= outer[1] - tolerance
            and inner[2] <= outer[2] + tolerance and inner[3] <= outer[3] + tolerance)


def _source_span_ids(block: dict[str, Any], lines_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(span_id for line_id in block.get("line_ids", [])
                              for span_id in lines_by_id.get(line_id, {}).get("span_ids", [])))


def _column_partition(blocks: list[dict[str, Any]], width: float) -> tuple[list[float], list[list[float]]]:
    """Find broad vertical whitespace corridors and derive two/three columns."""
    boxed = [item for item in blocks if item.get("box") and
             (item["box"][2] - item["box"][0]) < width * 0.62]
    if width <= 0 or len(boxed) < 4:
        return [], [[0.0, 0.0, max(width, 0.0), 0.0]]
    step = max(2.0, width / 400.0)
    samples = [width * 0.025 + step * index for index in range(
        max(1, int((width * 0.95) / step)))]
    empty = [x for x in samples if not any(item["box"][0] <= x <= item["box"][2] for item in boxed)]
    runs: list[list[float]] = []
    for x in empty:
        if not runs or x - runs[-1][1] > step * 1.6:
            runs.append([x, x])
        else:
            runs[-1][1] = x
    corridors: list[list[float]] = []
    min_gap = max(20.0, width * 0.035)
    for start, end in runs:
        if end - start < min_gap:
            continue
        center = (start + end) / 2
        left = [item for item in boxed if item["box"][2] < center]
        right = [item for item in boxed if item["box"][0] > center]
        if len(left) >= 2 and len(right) >= 2:
            corridors.append([start, end])
    # Keep non-overlapping corridors, preferring the widest when sampling merges noise.
    selected: list[list[float]] = []
    for corridor in sorted(corridors, key=lambda item: item[1] - item[0], reverse=True):
        if all(corridor[1] < existing[0] or corridor[0] > existing[1] for existing in selected):
            selected.append(corridor)
    selected.sort()
    boundaries = [(left + right) / 2 for left, right in selected[:2]]
    if not boundaries:
        return [], [[0.0, 0.0, width, 0.0]]
    xs = [0.0, *boundaries, width]
    columns = [[xs[index], 0.0, xs[index + 1], 0.0] for index in range(len(xs) - 1)]
    return boundaries, columns


def _assign_column(box: list[float] | None, boundaries: list[float]) -> int | None:
    if not box or not boundaries:
        return 0 if not boundaries else None
    if any(box[0] < boundary < box[2] for boundary in boundaries):
        return None
    center = (box[0] + box[2]) / 2
    for index, boundary in enumerate(boundaries):
        if center < boundary:
            return index
    return len(boundaries)


def _table_text_similarity(left: str, right: str) -> float:
    a = re.sub(r"\W+", "", left.casefold())
    b = re.sub(r"\W+", "", right.casefold())
    if not a or not b:
        return 0.0
    return 2 * sum((Counter(a) & Counter(b)).values()) / (len(a) + len(b))


def extract_pdf_tables(data: bytes, physical_content: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Extract bounded table cell grids where optional PyMuPDF supports them."""
    try:
        import pymupdf

        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - optional table parsing must not break physical extraction.
        return [], [f"table_engine_unavailable:{type(exc).__name__}"]
    extracted: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    try:
        for page_index, page in enumerate(document, 1):
            if len(extracted) >= 500:
                diagnostics.append("table_document_limit_reached")
                break
            page_content = physical_content.get("pages", [])[page_index - 1]
            spans = page_content.get("spans", [])
            blocks = page_content.get("blocks", [])
            try:
                finder = page.find_tables(strategy="lines")
                method = "pymupdf-find-tables-lines"
            except Exception:  # noqa: BLE001 - optional parser versions fail with different exception types
                finder = None
            if finder is None or not finder.tables:
                try:
                    finder = page.find_tables(strategy="text")
                    method = "pymupdf-find-tables-text"
                except Exception as exc:  # noqa: BLE001
                    diagnostics.append(f"table_page_unavailable:{page_index}:{type(exc).__name__}")
                    continue
            seen_boxes: list[list[float]] = []
            for table_index, table in enumerate(finder.tables[:100]):
                if len(extracted) >= 500:
                    diagnostics.append("table_document_limit_reached")
                    break
                raw_table_box = pymupdf.Rect(*table.bbox)
                display_table_box = raw_table_box * page.rotation_matrix
                box = [round(max(0.0, float(display_table_box.x0)), 3),
                       round(max(0.0, float(display_table_box.y0)), 3),
                       round(min(float(page.rect.width), float(display_table_box.x1)), 3),
                       round(min(float(page.rect.height), float(display_table_box.y1)), 3)]
                if any(_overlap(box, old) > 0.85 for old in seen_boxes):
                    continue
                seen_boxes.append(box)
                try:
                    raw_rows = table.extract()
                    rows = raw_rows if isinstance(raw_rows, list) else []
                except Exception:  # noqa: BLE001 - malformed individual table should not discard other pages
                    rows = []
                row_count = min(len(rows), 5000)
                col_count = min(int(getattr(table, "col_count", 0) or 0), 256)
                row_bounds = list(getattr(table, "rows", []))[:row_count]
                all_cells = [cell for row in row_bounds for cell in getattr(row, "cells", [])
                             if cell is not None]
                x_edges = sorted({round(float(cell[i]), 3) for cell in all_cells for i in (0, 2)})
                y_edges = sorted({round(float(cell[i]), 3) for cell in all_cells for i in (1, 3)})
                source_spans = [span for span in spans if _box(span.get("box")) and _overlap(box, span["box"]) > 0]
                source_span_ids = [span["id"] for span in source_spans if isinstance(span.get("id"), str)]
                source_block_ids = [block["id"] for block in blocks if _box(block.get("box"))
                                    and _overlap(box, block["box"]) > 0]
                cells: list[dict[str, Any]] = []
                merged_covered: list[list[float]] = []
                for row_number, row in enumerate(row_bounds):
                    row_cells = getattr(row, "cells", [])
                    for column_number, raw_cell in enumerate(row_cells[:col_count]):
                        text = rows[row_number][column_number] if row_number < len(rows) and \
                            column_number < len(rows[row_number]) else None
                        if raw_cell is None:
                            # A null cell may be empty or covered by a merged neighbour.
                            covered = any(previous[1] <= (y_edges[row_number] if row_number < len(y_edges) else 0)
                                          and previous[0] < (x_edges[column_number + 1]
                                                              if column_number + 1 < len(x_edges) else 0)
                                          for previous in merged_covered)
                            cells.append({"row": row_number, "column": column_number,
                                          "row_span": 1, "column_span": 1, "text": None,
                                          "box": None, "source_span_ids": [],
                                          "merged_continuation": covered})
                            continue
                        cell_rect = pymupdf.Rect(*raw_cell) * page.rotation_matrix
                        cell_box = [round(float(cell_rect.x0), 3), round(float(cell_rect.y0), 3),
                                    round(float(cell_rect.x1), 3), round(float(cell_rect.y1), 3)]
                        overlaps = [span for span in spans if _box(span.get("box")) and
                                    _overlap(cell_box, span["box"]) >= 0.15]
                        cell_source_ids = [span["id"] for span in overlaps if isinstance(span.get("id"), str)]
                        row_span = max(1, sum(1 for edge in y_edges if cell_box[1] <= edge < cell_box[3]))
                        col_span = max(1, sum(1 for edge in x_edges if cell_box[0] <= edge < cell_box[2]))
                        if row_span > 1 or col_span > 1:
                            merged_covered.append(cell_box)
                        cells.append({"row": row_number, "column": column_number,
                                      "row_span": min(row_span, 64), "column_span": min(col_span, 64),
                                      "text": str(text).strip() if text is not None else None,
                                      "box": cell_box, "source_span_ids": cell_source_ids,
                                      "merged_continuation": False})
                try:
                    header = getattr(table, "header", None)
                    header_rows = [0] if header and getattr(header, "names", None) else []
                except Exception:  # noqa: BLE001 - header metadata differs across PyMuPDF releases
                    header_rows = []
                extracted.append({"id": f"p{page_index}/table-detect-v1/t{table_index}",
                                  "page_number": page_index, "box": box,
                                  "row_count": row_count, "column_count": col_count,
                                  "cells": cells[:100000], "header_row_indices": header_rows,
                                  "source_block_ids": source_block_ids,
                                  "source_span_ids": source_span_ids,
                                  "detection_method": method, "status": "extracted",
                                  "diagnostics": [], "evidence": {
                                      "rule_id": "table.pymupdf.find-tables.v1", "score": 0.85,
                                      "facts": [f"{row_count} rows", f"{col_count} columns", method],
                                      "source_element_ids": source_block_ids + source_span_ids}})
    finally:
        document.close()
    return extracted, diagnostics


def _page_layout(page_number: int, page: dict[str, Any], page_meta: dict[str, Any],
                 tables: list[dict[str, Any]]) -> tuple[LayoutPage, list[dict[str, Any]]]:
    blocks = [item for item in page.get("blocks", []) if isinstance(item, dict) and item.get("id")]
    width = float(page_meta.get("width") or page_meta.get("width_points") or 0)
    height = float(page_meta.get("height") or page_meta.get("height_points") or 0)
    diagnostics: list[str] = []
    boundaries, column_boxes = _column_partition(blocks, width)
    if any(not _box(block.get("box")) for block in blocks):
        diagnostics.append("layout_geometry_unavailable_for_some_text_blocks")
    if width <= 0 or height <= 0:
        diagnostics.append("page_dimensions_unavailable")
        width = max(((_box(block.get("box")) or [0, 0, 0, 0])[2] for block in blocks), default=0.0)
        height = max(((_box(block.get("box")) or [0, 0, 0, 0])[3] for block in blocks), default=0.0)
    column_models: list[LayoutColumn] = []
    for index, box in enumerate(column_boxes):
        assigned = [block["id"] for block in blocks if _assign_column(_box(block.get("box")), boundaries) == index]
        column_models.append(LayoutColumn(
            id=f"p{page_number}/layout-v1/column-{index}", index=index,
            box=[box[0], 0.0, box[2], height], text_block_ids=assigned,
            evidence=EvidenceModel(rule_id="layout.vertical-whitespace-corridor.v1",
                                   score=0.7 if boundaries else 0.5,
                                   facts=["column inferred from block geometry" if boundaries else "single-column fallback"],
                                   source_element_ids=assigned)))
    columns_by_index = {item.index: item.id for item in column_models}
    regions: list[LayoutRegion] = []
    column_region_ids: dict[int, str] = {}
    spanning_blocks: list[dict[str, Any]] = []
    for block in blocks:
        assigned = _assign_column(_box(block.get("box")), boundaries)
        if assigned is None:
            spanning_blocks.append(block)
    for index, column in enumerate(column_models):
        child_ids = [block["id"] for block in blocks if _assign_column(_box(block.get("box")), boundaries) == index]
        region_id = f"p{page_number}/layout-v1/region-column-{index}"
        column_region_ids[index] = region_id
        regions.append(LayoutRegion(id=region_id, type="text_region", box=column.box,
                                    child_element_ids=child_ids, column_id=column.id,
                                    evidence=EvidenceModel(rule_id="layout.group-by-column.v1", score=0.65,
                                                          facts=["blocks grouped by horizontal corridor"],
                                                          source_element_ids=child_ids)))
    for index, block in enumerate(spanning_blocks):
        region_id = f"p{page_number}/layout-v1/region-spanning-{index}"
        regions.append(LayoutRegion(id=region_id, type="spanning_region", box=_box(block.get("box")),
                                    child_element_ids=[block["id"]],
                                    evidence=EvidenceModel(rule_id="layout.block-crosses-column.v1", score=0.8,
                                                          facts=["block crosses a detected corridor"],
                                                          source_element_ids=[block["id"]])))
    for index, corridor in enumerate(boundaries):
        left = max(0.0, corridor - max(10.0, width * 0.02))
        right = min(width, corridor + max(10.0, width * 0.02))
        regions.append(LayoutRegion(id=f"p{page_number}/layout-v1/region-whitespace-{index}",
                                    type="whitespace_separator", box=[left, 0.0, right, height],
                                    evidence=EvidenceModel(rule_id="layout.whitespace-corridor.v1", score=0.7,
                                                          facts=["no text block crosses the corridor"])))
    visuals: list[dict[str, Any]] = []
    for kind, key in (("image", "images"), ("vector", "vector_graphics")):
        for item in page.get(key, [])[:20000]:
            item_box = _box(item.get("box"))
            item_id = item.get("id")
            if not item_box or not isinstance(item_id, str):
                continue
            area = max(0.0, item_box[2] - item_box[0]) * max(0.0, item_box[3] - item_box[1])
            fraction = area / max(1.0, width * height)
            classification = "chart_candidate" if kind == "image" and 0.08 <= fraction <= 0.9 else \
                "diagram_candidate" if kind == "vector" and int(item.get("item_count", 0)) >= 6 else "unknown_region"
            candidate = {"id": f"p{page_number}/visual-v1/{kind}-{len(visuals)}", "type": classification,
                         "source_object_type": kind, "source_element_id": item_id, "box": item_box,
                         "asset_id": item.get("asset_id") if kind == "image" else None,
                         "semantics": None, "evidence": {"rule_id": "visual.object-preserved.v1",
                             "score": 0.5, "facts": ["visual object preserved; semantic content not inferred"],
                             "source_element_ids": [item_id]}}
            visuals.append(candidate)
            region_id = f"p{page_number}/layout-v1/region-visual-{len(visuals) - 1}"
            regions.append(LayoutRegion(id=region_id, type="visual_region", box=item_box,
                                        child_element_ids=[item_id],
                                        evidence=EvidenceModel(rule_id="layout.visual-object.v1", score=0.7,
                                                              facts=[f"source {kind} object bounds"],
                                                              source_element_ids=[item_id])))
    for table in tables:
        if table.get("page_number") != page_number or not _box(table.get("box")):
            continue
        source_ids = [str(item) for item in table.get("source_block_ids", [])]
        regions.append(LayoutRegion(id=f"p{page_number}/layout-v1/region-{table['id']}",
                                    type="table_region", box=table["box"], child_element_ids=source_ids,
                                    evidence=EvidenceModel(rule_id="layout.table-bounds.v1", score=0.85,
                                                          facts=[table.get("detection_method", "table candidate")],
                                                          source_element_ids=source_ids)))
    # A spanning object separates vertical reading segments. Inside a segment,
    # preserve column-major order; original source order remains alongside it.
    separators = sorted(((_box(item.get("box")) or [0, 0, 0, 0])[1], item["id"])
                        for item in spanning_blocks)

    def order_key(item: dict[str, Any]) -> tuple[int, int, float, float, int]:
        box = _box(item.get("box")) or [0.0, 0.0, 0.0, 0.0]
        segment = sum(1 for y, _ in separators if y < box[1])
        column = _assign_column(box if _box(item.get("box")) else None, boundaries)
        return (segment, -1 if column is None else column, box[1], box[0],
                int(item.get("source_order", 0) or 0))

    reading_objects: list[dict[str, Any]] = []
    for block in blocks:
        reading_objects.append({"id": block["id"], "kind": "text_block", **block})
    for kind, key in (("image", "images"), ("vector", "vector_graphics")):
        reading_objects.extend({"id": item["id"], "kind": kind, **item} for item in page.get(key, [])
                               if isinstance(item, dict) and item.get("id"))
    reading_objects.extend({"id": item["id"], "kind": "table", **item} for item in tables
                           if item.get("page_number") == page_number)
    reading_objects = reading_objects[:20000]
    ordered = sorted(reading_objects, key=order_key)
    region_for_element = {element_id: region.id for region in regions for element_id in region.child_element_ids}
    block_source = {item["id"]: int(item.get("source_order", 0) or 0) for item in reading_objects}
    reading_order = [ReadingOrderItem(
        index=index, element_id=item["id"], element_type=item["kind"],
        original_source_order=block_source.get(item["id"]),
        region_id=region_for_element.get(item["id"]),
        column_id=columns_by_index.get(_assign_column(_box(item.get("box")), boundaries)),
        evidence=EvidenceModel(rule_id="reading-order.segment-column-y.v1", score=0.65,
                              facts=["full-width segments, then column order, then top-to-bottom"],
                              source_element_ids=[item["id"]])) for index, item in enumerate(ordered)]
    original_order = [item["id"] for item in sorted(reading_objects,
                                                    key=lambda item: int(item.get("source_order", 0) or 0))]
    return LayoutPage(page_number=page_number, regions=regions, columns=column_models,
                      whitespace_separators=[[max(0.0, boundary - max(10.0, width * 0.02)), 0.0,
                                              min(width, boundary + max(10.0, width * 0.02)), height]
                                             for boundary in boundaries],
                      reading_order=reading_order, original_order=original_order,
                      diagnostics=diagnostics), visuals


def _find_repeated_furniture(page_lines: list[tuple[int, dict[str, Any], float, float]],
                             page_count: int) -> dict[tuple[int, str], str]:
    occurrences: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for page_number, line, width, height in page_lines:
        box = _box(line.get("box"))
        text = str(line.get("text", "")).strip()
        if not box or not text:
            continue
        normalized = re.sub(r"\b\d+\b", "#", re.sub(r"\s+", " ", text.casefold()))
        if not normalized:
            continue
        top = box[1] / max(height, 1.0)
        bottom = (height - box[3]) / max(height, 1.0)
        position = "header" if top <= 0.12 else "footer" if bottom <= 0.12 else "body"
        occurrences[normalized].append((page_number, position))
    minimum = max(2, math.ceil(page_count * 0.6))
    found: dict[tuple[int, str], str] = {}
    for normalized, values in occurrences.items():
        pages = {page for page, position in values if position != "body"}
        if len(pages) < minimum:
            continue
        for page_number, position in values:
            if position != "body":
                found[(page_number, normalized)] = position
    return found


def _body_font_size(physical_content: dict[str, Any]) -> float | None:
    sizes: list[float] = []
    for page in physical_content.get("pages", []):
        for span in page.get("spans", []):
            try:
                size = float(span.get("font", {}).get("size_points"))
            except (TypeError, ValueError):
                continue
            if math.isfinite(size) and 1 <= size <= 200:
                sizes.extend([size] * min(80, max(1, len(str(span.get("text", ""))) // 4)))
    return median(sizes) if sizes else None


def _heading(text: str, font: dict[str, Any], box: list[float] | None,
             body_size: float | None, page_number: int,
             style_rules: dict[str, Any]) -> tuple[bool, int, EvidenceModel]:
    value = text.strip()
    try:
        size = float(font.get("size_points") or 0)
    except (TypeError, ValueError):
        size = 0.0
    bold = bool(font.get("bold"))
    ratio = size / body_size if body_size else 1.0
    numbered = bool(_NUMBERED_HEADING.match(value))
    prominence = min(1.0, max(0.0, (ratio - 1.0) / 0.65))
    short = 2 <= len(value) <= int(style_rules.get("heading_max_chars", 180))
    score = min(0.98, 0.35 + 0.35 * prominence + (0.18 if numbered else 0) +
                (0.1 if bold else 0) + (0.05 if short else 0))
    is_heading = short and (numbered or ratio >= float(style_rules.get("heading_min_size_ratio", 1.15))
                            or (bold and ratio >= 1.05))
    level = min(6, max(1, round(1 + max(0.0, 1.7 - ratio) * 3)))
    evidence = EvidenceModel(rule_id="logical.heading-prominence-numbering.v1", score=score,
                             facts=[f"font_size_ratio:{ratio:.3f}", f"bold:{str(bold).lower()}",
                                    f"numbered_pattern:{str(numbered).lower()}",
                                    f"page:{page_number}"],
                             source_element_ids=[])
    return is_heading, level, evidence


def analyze_pdf_document(page_model: dict[str, Any], physical_content: dict[str, Any],
                         *, raw_pdf: bytes | None = None,
                         style_rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build bounded layout and logical structures while retaining every source ID."""
    rules = {"heading_min_size_ratio": 1.15, "heading_max_chars": 180,
             "join_hyphenation": False, **(style_rules or {})}
    tables: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    if raw_pdf is not None:
        tables, table_diagnostics = extract_pdf_tables(raw_pdf, physical_content)
        diagnostics.extend(table_diagnostics)
    physical_pages = physical_content.get("pages", [])
    page_models = {int(page.get("page_number", index + 1)): page
                   for index, page in enumerate(page_model.get("pages", []))}
    pages_by_number = {int(page.get("page_number", index + 1)): page
                       for index, page in enumerate(physical_pages)}
    page_count = max(len(physical_pages), len(page_models))
    body_size = _body_font_size(physical_content)
    layout_pages: list[LayoutPage] = []
    visual_by_page: dict[int, list[dict[str, Any]]] = {}
    for page_number in range(1, page_count + 1):
        physical_page = pages_by_number.get(page_number, {"page_number": page_number})
        page_meta = page_models.get(page_number, {})
        page_tables = [table for table in tables if table.get("page_number") == page_number]
        layout, visuals = _page_layout(page_number, physical_page, page_meta, page_tables)
        layout_pages.append(layout)
        visual_by_page[page_number] = visuals
        for table in page_tables:
            table["continuation_group_id"] = None
    # Cross-page table continuations use compatible column counts, edge location and headers.
    previous_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for table in tables:
        previous_by_page[int(table["page_number"])].append(table)
    for page_number in range(2, page_count + 1):
        for current in previous_by_page.get(page_number, []):
            candidates = []
            for previous in previous_by_page.get(page_number - 1, []):
                if previous.get("column_count") != current.get("column_count"):
                    continue
                prev_box, cur_box = _box(previous.get("box")), _box(current.get("box"))
                prev_h = float(page_models.get(page_number - 1, {}).get("height") or 1)
                cur_h = float(page_models.get(page_number, {}).get("height") or 1)
                if not prev_box or not cur_box or prev_box[3] < prev_h * 0.55 or cur_box[1] > cur_h * 0.45:
                    continue
                previous_headers = " ".join(str(previous["cells"][index].get("text") or "")
                                            for index in range(min(previous.get("column_count", 0),
                                                                   len(previous.get("cells", []))))
                                            if previous["cells"][index].get("row") == 0)
                current_headers = " ".join(str(current["cells"][index].get("text") or "")
                                           for index in range(min(current.get("column_count", 0),
                                                                  len(current.get("cells", []))))
                                           if current["cells"][index].get("row") == 0)
                score = _table_text_similarity(previous_headers, current_headers)
                if score >= 0.5 or not previous_headers or not current_headers:
                    candidates.append((score, previous))
            if candidates:
                previous = max(candidates, key=lambda item: item[0])[1]
                group = previous.get("continuation_group_id") or f"table-chain/{previous['id']}"
                previous["continuation_group_id"] = group
                current["continuation_group_id"] = group
                current["diagnostics"].append("table_continues_from_previous_page_candidate")

    page_line_records: list[tuple[int, dict[str, Any], float, float]] = []
    for page_number in range(1, page_count + 1):
        meta = page_models.get(page_number, {})
        width, height = float(meta.get("width") or 0), float(meta.get("height") or 0)
        for line in pages_by_number.get(page_number, {}).get("lines", []):
            page_line_records.append((page_number, line, width, height))
    furniture = _find_repeated_furniture(page_line_records, page_count)
    paragraphs: list[LogicalParagraph] = []
    logical_pages: list[LogicalPage] = []
    sections: list[LogicalSection] = []
    lists: list[LogicalList] = []
    section_stack: list[LogicalSection] = []
    list_sequence = 0
    continuation_previous: LogicalParagraph | None = None
    for page_number in range(1, page_count + 1):
        page = pages_by_number.get(page_number, {"page_number": page_number})
        meta = page_models.get(page_number, {})
        lines = [line for line in page.get("lines", []) if isinstance(line, dict)
                 and isinstance(line.get("id"), str)]
        spans_by_id = {span["id"]: span for span in page.get("spans", [])
                       if isinstance(span, dict) and isinstance(span.get("id"), str)}
        tables_here = [table for table in tables if table.get("page_number") == page_number]
        table_boxes = [(table, _box(table.get("box"))) for table in tables_here if _box(table.get("box"))]
        width, height = float(meta.get("width") or 0), float(meta.get("height") or 0)
        layout = layout_pages[page_number - 1]
        block_order = {item.element_id: item.index for item in layout.reading_order
                       if item.element_type == "text_block"}
        block_column = {item.element_id: item.column_id for item in layout.reading_order
                        if item.element_type == "text_block"}
        lines.sort(key=lambda line: (block_order.get(line.get("block_id"), 10**8),
                                     int(line.get("source_order", 0) or 0)))
        prepared_lines: list[dict[str, Any]] = []
        for line in lines:
            text = str(line.get("text", ""))
            box = _box(line.get("box"))
            table = next((table for table, table_box in table_boxes if box and table_box and
                          _overlap(box, table_box) >= 0.25), None)
            if table is not None:
                table.setdefault("source_line_ids", []).append(line["id"])
                continue
            normalized = re.sub(r"\s+", " ", text.casefold()).strip()
            furniture_type = furniture.get((page_number, re.sub(r"\b\d+\b", "#", normalized)))
            if _PAGE_NUMBER.match(text.strip()) and box and height and \
                    (box[1] < height * 0.18 or box[3] > height * 0.82):
                furniture_type = "page_number"
            span_ids = [item for item in line.get("span_ids", []) if item in spans_by_id]
            line_spans = [spans_by_id[item] for item in span_ids]
            font = (line_spans[0].get("font", {}) if line_spans else {})
            is_heading, level, heading_evidence = _heading(text, font, box, body_size,
                                                           page_number, rules)
            marker_match = _LIST_MARKER.match(text)
            line_type = furniture_type or ("caption" if _CAPTION.match(text.strip()) else
                                           "heading" if is_heading else
                                           "list_item" if marker_match else "paragraph")
            prepared_lines.append({"line": line, "text": text, "box": box,
                                   "span_ids": span_ids, "spans": line_spans,
                                   "font": font, "line_type": line_type,
                                   "heading_level": level if is_heading else None,
                                   "heading_evidence": heading_evidence,
                                   "column_id": block_column.get(line.get("block_id")),
                                   "marker_match": marker_match})
        grouped: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        for item in prepared_lines:
            if item["line_type"] != "paragraph":
                if current:
                    grouped.append(current)
                    current = []
                grouped.append([item])
                continue
            if not current:
                current = [item]
                continue
            previous = current[-1]
            prev_box, next_box = previous["box"], item["box"]
            continuation = False
            if prev_box and next_box and previous["column_id"] == item["column_id"]:
                prev_height = max(1.0, prev_box[3] - prev_box[1])
                gap = next_box[1] - prev_box[3]
                indent_delta = abs(next_box[0] - prev_box[0])
                continuation = gap <= max(8.0, prev_height * 0.8) and indent_delta <= max(18.0, prev_height * 1.5)
            elif not prev_box and not next_box:
                continuation = (previous["line"].get("block_id") == item["line"].get("block_id") and
                                previous["column_id"] == item["column_id"])
            if continuation:
                current.append(item)
            else:
                grouped.append(current)
                current = [item]
        if current:
            grouped.append(current)
        page_paragraphs: list[LogicalParagraph] = []
        for group_index, group in enumerate(grouped):
            page_paragraph_id = f"p{page_number}/logical-v1/paragraph-{group_index}"
            line_texts = [str(item["text"]).strip() for item in group]
            text_parts: list[str] = []
            for line_index, value in enumerate(line_texts):
                if line_index and rules.get("join_hyphenation") and text_parts[-1].endswith("-") and value[:1].islower():
                    text_parts[-1] = text_parts[-1][:-1] + value
                elif text_parts:
                    text_parts[-1] = text_parts[-1] + " " + value
                else:
                    text_parts.append(value)
            text_value = " ".join(text_parts).strip()
            source_lines = [item["line"] for item in group]
            source_span_ids = list(dict.fromkeys(span_id for item in group for span_id in item["span_ids"]))
            boxes = [item["box"] for item in group if item["box"]]
            box = [min(item[0] for item in boxes), min(item[1] for item in boxes),
                   max(item[2] for item in boxes), max(item[3] for item in boxes)] if boxes else None
            source_order = [int(item["line"].get("source_order", index) or 0)
                            for index, item in enumerate(group)]
            line_type = group[0]["line_type"]
            if line_type == "heading":
                paragraph_type = "heading"
                evidence = group[0]["heading_evidence"]
            elif line_type in {"header", "footer", "page_number", "caption"}:
                paragraph_type = line_type
                evidence = EvidenceModel(rule_id=f"logical.repeated-{line_type}.v1", score=0.75,
                                         facts=["position and repeated normalized text"],
                                         source_element_ids=[line["id"] for line in source_lines])
            elif line_type == "list_item":
                paragraph_type = "list_item"
                evidence = EvidenceModel(rule_id="logical.list-marker.v1", score=0.8,
                                         facts=[f"marker:{group[0]['marker_match'].group('marker')}"],
                                         source_element_ids=[line["id"] for line in source_lines])
            else:
                paragraph_type = "paragraph"
                evidence = EvidenceModel(rule_id="logical.line-continuation-geometry.v1",
                                         score=0.7 if len(group) > 1 else 0.55,
                                         facts=[f"joined_lines:{len(group)}",
                                                "geometry unavailable; kept source line separate" if not box else
                                                "same column with bounded line gap and indent"],
                                         source_element_ids=[line["id"] for line in source_lines])
            style_runs: list[StyleRun] = []
            for item in group:
                for span in item["spans"]:
                    style_runs.append(StyleRun(text=str(span.get("text", "")),
                                               source_span_ids=[str(span["id"])],
                                               font=dict(span.get("font", {}))))
            paragraph = LogicalParagraph(
                id=page_paragraph_id, type=paragraph_type, text=text_value, box=box,
                page_number=page_number, source_line_ids=[line["id"] for line in source_lines],
                source_span_ids=source_span_ids, original_source_order=source_order,
                style_runs=style_runs, heading_level=(group[0]["heading_level"]
                                                      if paragraph_type == "heading" else None),
                evidence=evidence)
            page_paragraphs.append(paragraph)
        # First prominent title-like line is distinct from section headings.
        title_candidates = [item for item in page_paragraphs if item.type == "heading" and item.box and
                            item.box[1] <= max(120.0, height * 0.28)]
        if page_number == 1 and title_candidates:
            title = max(title_candidates, key=lambda item: next((
                float(span.get("font", {}).get("size_points") or 0)
                for line in lines if line.get("id") in item.source_line_ids
                for span_id in line.get("span_ids", []) for span in [spans_by_id.get(span_id, {})]), 0.0))
            title.type = "title"
            title.heading_level = None
            title.evidence.rule_id = "logical.document-title-prominence.v1"
            title.evidence.facts.append("first-page heading candidate near page top")
        current_section: LogicalSection | None = None
        page_heading_ids: list[str] = []
        for paragraph in page_paragraphs:
            if paragraph.type == "heading":
                page_heading_ids.append(paragraph.id)
                level = paragraph.heading_level or 1
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                parent = section_stack[-1] if section_stack else None
                section_id = f"section/{paragraph.id}"
                section = LogicalSection(id=section_id, title=paragraph.text, level=level,
                                         parent_id=parent.id if parent else None,
                                         page_numbers=[page_number],
                                         source_element_ids=paragraph.source_line_ids + paragraph.source_span_ids,
                                         evidence=paragraph.evidence)
                if parent:
                    parent.child_section_ids.append(section_id)
                sections.append(section)
                section_stack.append(section)
                current_section = section
                paragraph.section_id = section_id
            elif paragraph.type != "title" and section_stack:
                current_section = section_stack[-1]
                paragraph.section_id = current_section.id
                current_section.paragraph_ids.append(paragraph.id)
                if page_number not in current_section.page_numbers:
                    current_section.page_numbers.append(page_number)
        # Connect page-local segments where the next line is a plausible continuation.
        candidates = [item for item in page_paragraphs if item.type in {"paragraph", "list_item"}]
        if candidates and continuation_previous and continuation_previous.page_number == page_number - 1:
            first = candidates[0]
            prev_text, next_text = continuation_previous.text.rstrip(), first.text.lstrip()
            prev_box, next_box = continuation_previous.box, first.box
            same_column = bool(prev_box and next_box and abs(prev_box[0] - next_box[0]) <= 24)
            looks_open = prev_text.endswith(("-", "—", ",", ";", ":")) or \
                (prev_text and prev_text[-1].islower() and next_text[:1].islower())
            if same_column and looks_open:
                continuation_id = f"continuation/{continuation_previous.id}"
                continuation_previous.continuation_id = continuation_id
                first.continuation_id = continuation_id
                first.evidence.facts.append("continues prior page paragraph candidate")
                first.evidence.rule_id = "logical.cross-page-continuation.v1"
        continuation_previous = candidates[-1] if candidates else None
        page_list_ids: list[str] = []
        previous_list_paragraph: LogicalParagraph | None = None
        # List sequence and indentation are retained; wrapped lines are already in item paragraphs.
        for paragraph in page_paragraphs:
            if paragraph.type != "list_item":
                previous_list_paragraph = None
                continue
            marker_match = _LIST_MARKER.match(paragraph.text)
            marker = marker_match.group("marker") if marker_match else "?"
            content = marker_match.group("text") if marker_match else paragraph.text
            paragraph.text = content
            marker_kind = ("bullet" if marker in {"-", "*", "+", "•", "▪", "◦", "‣"} else
                           "decimal" if re.match(r"\(?\d", marker) else
                           "roman" if re.match(r"\(?[IVXLCDMivxlcdm]+", marker) else
                           "alphabetic" if re.match(r"\(?[A-Za-z]", marker) else "unknown")
            list_sequence += 1
            list_id = f"p{page_number}/logical-v1/list-{list_sequence}"
            x0 = paragraph.box[0] if paragraph.box else 0.0
            baseline_x = min((candidate.box[0] for candidate in page_paragraphs if candidate.box), default=x0)
            level = min(32, max(0, round((x0 - baseline_x) / 18.0)))
            paragraph.list_id = list_id
            paragraph.list_level = level
            paragraph.list_marker = marker
            paragraph.evidence.source_element_ids.extend(paragraph.source_line_ids)
            list_model = LogicalList(id=list_id,
                                     ordered=marker_kind != "bullet",
                                     marker_kind=marker_kind,
                                     page_numbers=[page_number],
                                     items=[ListItemModel(paragraph_id=paragraph.id, marker=marker,
                                                          level=level,
                                                          ordinal=int(re.match(r"\(?\d+", marker).group(0).strip("("))
                                                          if re.match(r"\(?\d+", marker) else None,
                                                          source_element_ids=paragraph.source_line_ids + paragraph.source_span_ids)],
                                     evidence=EvidenceModel(rule_id="logical.list-marker-indent.v1", score=0.8,
                                                           facts=[f"marker_kind:{marker_kind}", f"indent_level:{level}"],
                                                           source_element_ids=paragraph.source_line_ids + paragraph.source_span_ids))
            if (previous_list_paragraph is not None and lists and
                    lists[-1].page_numbers == [page_number] and lists[-1].marker_kind == marker_kind):
                existing = lists[-1]
                existing.items.extend(list_model.items)
                existing.evidence.source_element_ids.extend(
                    item for item in list_model.evidence.source_element_ids
                    if item not in existing.evidence.source_element_ids)
                existing.evidence.facts.append(f"indent_level:{level}")
                paragraph.list_id = existing.id
                if existing.id not in page_list_ids:
                    page_list_ids.append(existing.id)
            else:
                lists.append(list_model)
                page_list_ids.append(list_id)
            previous_list_paragraph = paragraph
        page_visuals = visual_by_page.get(page_number, [])
        page_captions: list[dict[str, Any]] = []
        for paragraph in page_paragraphs:
            if paragraph.type != "caption" or not paragraph.box:
                continue
            match = _CAPTION.match(paragraph.text)
            if not match:
                continue
            candidates: list[tuple[float, str, str, list[float]]] = []
            caption_box = paragraph.box
            for visual in page_visuals:
                visual_box = visual["box"]
                gap = max(0.0, max(visual_box[1] - caption_box[3], caption_box[1] - visual_box[3]))
                horizontal_overlap = max(0.0, min(visual_box[2], caption_box[2]) - max(visual_box[0], caption_box[0]))
                if gap <= 72 and horizontal_overlap >= min(24, (caption_box[2] - caption_box[0]) * 0.25):
                    candidates.append((gap, visual["id"], visual["type"], visual_box))
            for table in tables_here:
                table_box = _box(table.get("box"))
                if not table_box:
                    continue
                gap = max(0.0, max(table_box[1] - caption_box[3], caption_box[1] - table_box[3]))
                overlap_width = max(0.0, min(table_box[2], caption_box[2]) - max(table_box[0], caption_box[0]))
                if gap <= 72 and overlap_width >= min(24, (caption_box[2] - caption_box[0]) * 0.25):
                    candidates.append((gap, table["id"], "table", table_box))
            candidates.sort(key=lambda item: item[0])
            association = {"caption_id": paragraph.id, "label": match.group(0),
                           "object_id": None, "object_type": None,
                           "status": "unmatched", "score": 0.0,
                           "alternatives": [item[1] for item in candidates[:4]]}
            if candidates and candidates[0][0] <= 72:
                ambiguous = len(candidates) > 1 and candidates[1][0] - candidates[0][0] < 8
                association.update({"object_id": None if ambiguous else candidates[0][1],
                                    "object_type": candidates[0][2],
                                    "status": "ambiguous" if ambiguous else "associated",
                                    "score": max(0.0, 1.0 - candidates[0][0] / 90.0)})
            paragraph.associations.append(association)
            page_captions.append(association)
        page_tables_models = [TableSegmentModel.model_validate(item) for item in tables_here]
        page_diagnostics = list(layout.diagnostics)
        if page_number not in pages_by_number:
            page_diagnostics.append("physical_page_unavailable")
        if meta.get("classification", {}).get("classification") == "scanned" and not page.get("ocr_observations"):
            page_diagnostics.append("ocr_not_available_or_not_requested")
        title_id = next((item.id for item in page_paragraphs if item.type == "title"), None)
        logical_page = LogicalPage(
            page_number=page_number, title_id=title_id,
            paragraph_ids=[item.id for item in page_paragraphs],
            heading_ids=[item.id for item in page_paragraphs if item.type == "heading"],
            list_ids=page_list_ids,
            table_ids=[item.id for item in page_tables_models],
            header_ids=[item.id for item in page_paragraphs if item.type == "header"],
            footer_ids=[item.id for item in page_paragraphs if item.type == "footer"],
            page_number_ids=[item.id for item in page_paragraphs if item.type == "page_number"],
            visual_candidates=page_visuals, captions=page_captions,
            forms=[{"id": str(item.get("id")), "type": "form_field", "name": item.get("field_name"),
                    "value": item.get("field_value"), "box": item.get("box"),
                    "source_element_id": item.get("id"), "semantics": "unknown"}
                   for item in physical_content.get("annotations", [])
                   if item.get("subtype") == "Widget" and item.get("page_number") == page_number],
            diagnostics=page_diagnostics)
        logical_pages.append(logical_page)
        paragraphs.extend(page_paragraphs)
    # Empty documents still validate as a page-less model; normal PDF validation rejects 0 pages.
    model = LogicalDocumentModel(
        schema_version=1, schema_id="e22-logical-document",
        analysis_engine={"id": "docplatform-e22-analysis", "version": ANALYSIS_VERSION},
        configuration=rules, pages=logical_pages, layout_pages=layout_pages,
        paragraphs=paragraphs, sections=sections, lists=lists,
        tables=[TableSegmentModel.model_validate(item) for item in tables], diagnostics=diagnostics)
    return model.model_dump(mode="json")


def canonical_document(page_model: dict[str, Any], physical_content: dict[str, Any],
                       logical_content: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete combined E22 envelope without changing stored legacy contracts."""
    return CanonicalDocumentModel(
        schema_version=1, schema_id="e22-canonical-document",
        source=page_model.get("source", {}), processing=page_model.get("processing", {}),
        physical_content=physical_content, logical_content=logical_content).model_dump(mode="json")
