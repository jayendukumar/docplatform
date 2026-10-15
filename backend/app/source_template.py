"""Deterministic interpretation and declarative draft generation for E21."""
from __future__ import annotations

import re
from typing import Any


def interpret_page_model(page_model: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    by_kind: dict[str, int] = {}
    for page in page_model.get("pages", []):
        for element in page.get("elements", []):
            text = str(element.get("text", ""))
            item_id = f"p{page.get('page_number', 1)}-{element.get('id', len(items) + 1)}"
            role = str(element.get("role", ""))
            element_type = str(element.get("type", "text"))
            box = element.get("box") or []
            if element_type == "table" or role == "table":
                kind = "table"
            elif re.search(r"\{\{[^{}]+\}\}", text):
                kind = "variable"
            elif re.search(r"(?:^|\s)[=≈≠≤≥∑∫√]|\b[A-Za-z]\s*\^\s*\d", text):
                kind = "formula"
            elif element_type == "image":
                kind = "image"
            elif role == "table_row":
                kind = "table_row"
            elif role == "heading" and page.get("page_number") == 1 and box and box[1] < 160:
                kind = "header"
            elif role == "heading":
                kind = "heading"
            elif role == "list_item":
                kind = "list_item"
            else:
                kind = "paragraph"
            review_required = kind in {"variable", "formula", "image"}
            status = "suggested" if review_required else "auto_accepted"
            by_kind[kind] = by_kind.get(kind, 0) + 1
            item = {"id": item_id, "kind": kind, "original_value": str(element.get("raw_text", text)),
                          "normalized_value": text, "status": "suggested",
                          "review_required": review_required,
                          "confidence": 0.65 if review_required else 0.9,
                          "provenance": {"page_number": page.get("page_number"),
                                         "element_id": element.get("id"),
                                         "box": element.get("box")},
                          "source_version": page_model.get("schema_version", 1)}
            if element_type == "table" and isinstance(element.get("table"), dict):
                item["table"] = element["table"]
            if isinstance(element.get("runs"), list):
                item["runs"] = element["runs"]
            if isinstance(element.get("paragraph_format"), dict):
                item["paragraph_format"] = element["paragraph_format"]
            items.append(item)
    warnings: list[str] = []
    if any("<w:" in str(item.get("original_value", "")) for item in items):
        warnings.append("Embedded document markup was removed from the displayed text; verify the affected content before approval.")
    if not items:
        warnings.append("No text, table rows, or images were extracted from this document.")
        if page_model.get("processing", {}).get("route") == "scan":
            warnings.append("This document appears to be scanned or image-only. Configure a local OCR adapter before retrying.")
    for item in items:
        if not item["review_required"]:
            item["status"] = "auto_accepted"
    auto_accepted = sum(item["status"] == "auto_accepted" for item in items)
    review_count = len(items) - auto_accepted
    source_document = page_model.get("source_document", {})
    warnings.extend(source_document.get("warnings", []) if isinstance(source_document, dict) else [])
    return {"contract": "source-interpretation-v1", "page_count": len(page_model.get("pages", [])),
            "items": items, "unsupported_features": unsupported, "warnings": warnings,
            "source_document": source_document,
            "status": "ready" if items else "needs_review",
            "summary": {"pages": len(page_model.get("pages", [])), "elements": len(items),
                        "ready": auto_accepted, "review_required": review_count,
                        "by_kind": by_kind},
            "engine": {"id": "bounded-local-page-model", "version": "1"},
            "limitations": ["Complex PDF/DOCX layout and font fidelity require review.",
                            "This interpretation is a draft suggestion, not an extraction guarantee."]}


def approved_items(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    legacy_fixed = "summary" not in interpretation and any(
        item.get("kind") == "fixed" and item.get("status") == "suggested"
        for item in interpretation.get("items", [])
    )
    return [item for item in interpretation.get("items", [])
            if item.get("status") in {"approved", "auto_accepted", "corrected"}
            or (legacy_fixed and item.get("kind") == "fixed" and item.get("status") == "suggested")]


def template_from_interpretation(interpretation: dict[str, Any], name: str) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    sample_data: dict[str, Any] = {}
    source_document = interpretation.get("source_document", {})
    page = dict(source_document.get("page", {})) if isinstance(source_document, dict) else {}
    items = approved_items(interpretation)
    if isinstance(source_document, dict):
        for image in source_document.get("header_images", []):
            if isinstance(image, dict) and isinstance(image.get("src"), str):
                blocks.append({"type": "image", "src": image["src"],
                               "alt": str(image.get("alt", "Source header image"))[:200],
                               "width": max(1, min(600, int(image.get("width", 150)))),
                               "align": "left", "source_role": "header_image"})

    def flush_list(values: list[str], ordered: bool) -> None:
        if values:
            blocks.append({"type": "list", "list_style": "ordered" if ordered else "unordered",
                           "static_items": values, "source_item_ids": []})

    pending_list: list[str] = []
    pending_ordered = False
    for item in items:
        value = str(item.get("normalized_value", ""))
        if item.get("kind") == "list_item":
            paragraph_format = item.get("paragraph_format") or {}
            ordered = paragraph_format.get("list_style") == "ordered"
            if pending_list and ordered != pending_ordered:
                flush_list(pending_list, pending_ordered)
                pending_list = []
            pending_ordered = ordered
            pending_list.append(value)
            continue
        flush_list(pending_list, pending_ordered)
        pending_list = []
        if item.get("kind") == "table":
            table = item.get("table") or {}
            rows = table.get("rows") if isinstance(table, dict) else None
            if isinstance(rows, list) and rows:
                column_count = max((len(row) for row in rows if isinstance(row, list)), default=0)
                if column_count:
                    table_index = sum(1 for block in blocks if block.get("type") == "table") + 1
                    path = f"source_table_{table_index}"
                    header = [str(cell)[:200] for cell in (rows[0] if isinstance(rows[0], list) else [])]
                    header += [f"Column {i + 1}" for i in range(len(header), column_count)]
                    sample_data[path] = [
                        {f"c{column + 1}": str(row[column])[:2000] if column < len(row) else ""
                         for column in range(column_count)}
                        for row in rows[1:] if isinstance(row, list)
                    ]
                    blocks.append({"type": "table", "items": path,
                                   "columns": [{"header": header[column], "path": f"c{column + 1}"}
                                               for column in range(column_count)],
                                   "show_header": True, "source_item_id": item["id"]})
                    continue
        if item.get("kind") == "image":
            blocks.append({"type": "text", "text": "[Source image requires asset review]", "source_item_id": item["id"]})
            continue
        if not isinstance(item.get("runs"), list) and not isinstance(item.get("paragraph_format"), dict):
            blocks.append({"type": "text", "text": value, "source_item_id": item["id"]})
            continue
        paragraph_format = item.get("paragraph_format") or {}
        runs = item.get("runs") or [{"text": value}]
        heading_level = paragraph_format.get("heading_level")
        rich_runs = []
        for run in runs:
            style = {key: run[key] for key in ("font_family", "font_size", "color", "bold", "italic", "underline")
                     if key in run}
            if heading_level and not any(key in style for key in ("font_size", "bold")):
                style.update({"font_size": max(18, 30 - int(heading_level) * 3), "bold": True})
            rich_runs.append({"type": "text", "text": str(run.get("text", "")), **({"style": style} if style else {})})
        paragraph = {"align": paragraph_format.get("alignment", "left"), "runs": rich_runs}
        block: dict[str, Any] = {"type": "rich_text", "paragraphs": [paragraph], "source_item_id": item["id"]}
        for source_key, target_key in (("break_before", "break_before"),
                                       ("spacing_before", "paragraph_spacing_before"),
                                       ("spacing_after", "paragraph_spacing_after"),
                                       ("left_indent", "left_indent"),
                                       ("right_indent", "right_indent"),
                                       ("first_line_indent", "first_line_indent")):
            if source_key in paragraph_format:
                block[target_key] = paragraph_format[source_key]
        blocks.append(block)
    flush_list(pending_list, pending_ordered)
    if "size" not in page:
        page["size"] = "A4"
    if "orientation" not in page:
        page["orientation"] = "portrait"
    page.setdefault("show_page_numbers", False)
    return {"schema_version": 1, "name": name, "page": page, "blocks": blocks,
            "sample_data": sample_data,
            "source_generation": {"contract": "source-template-generation-v1",
                                   "interpretation_version": interpretation.get("engine", {}).get("version", "1"),
                                   "approved_item_ids": [item["id"] for item in approved_items(interpretation)]}}
