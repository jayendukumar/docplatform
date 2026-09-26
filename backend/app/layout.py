"""Validated, dependency-free mapping for the layout-engine-v1 PageModel boundary."""
from __future__ import annotations

import math
import re
from typing import Any


class LayoutEngineError(ValueError):
    """Raised when a layout adapter returns an incompatible normalized result."""


_LIST_ITEM_RE = re.compile(r"^(?:[-*•£▪]|\(?\d{1,3}[.)])\s+")
_TABLE_ROW_RE = re.compile(r"[^|]+(?:\|[^|]+){2,}")
_ROLES = {"text", "heading", "list_item", "table_row", "table", "image"}


def _layout_role(text: str, index: int) -> str:
    value = text.strip()
    if value.startswith(("# ", "## ", "### ")):
        return "heading"
    if _LIST_ITEM_RE.match(value):
        return "list_item"
    if _TABLE_ROW_RE.fullmatch(value):
        return "table_row"
    if index > 0 and len(value) <= 120 and value.upper() == value and any(char.isalpha() for char in value):
        return "heading"
    return "text"


def _box(value: Any, path: str) -> list[float | int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise LayoutEngineError(f"{path}.box must contain four coordinates")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item)
           for item in value):
        raise LayoutEngineError(f"{path}.box coordinates must be finite numbers")
    left, top, right, bottom = value
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise LayoutEngineError(f"{path}.box must be a positive top-left rectangle")
    return value


def map_layout_elements(elements: Any, path: str = "elements") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize bounded elements and derive deterministic layout metadata."""
    if not isinstance(elements, list) or len(elements) > 10_000:
        raise LayoutEngineError(f"{path} must contain at most 10000 elements")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    headings: list[str] = []
    lists: list[str] = []
    table_rows: list[str] = []
    for index, raw in enumerate(elements):
        if not isinstance(raw, dict):
            raise LayoutEngineError(f"{path}[{index}] must be an object")
        element_id = raw.get("id")
        if not isinstance(element_id, str) or not element_id or len(element_id) > 160 or element_id in seen:
            raise LayoutEngineError(f"{path}[{index}].id must be unique and bounded")
        seen.add(element_id)
        element_type = raw.get("type", "text")
        if element_type not in {"text", "image", "table", "list"}:
            raise LayoutEngineError(f"{path}[{index}].type is unsupported")
        text = raw.get("text", "")
        if not isinstance(text, str) or len(text) > 1_000_000:
            raise LayoutEngineError(f"{path}[{index}].text is invalid")
        item = dict(raw)
        item["type"] = element_type
        item["text"] = text
        item["box"] = _box(raw.get("box"), f"{path}[{index}]")
        role = raw.get("role")
        if role is None:
            role = _layout_role(text, index) if element_type == "text" else element_type
        if role not in _ROLES:
            raise LayoutEngineError(f"{path}[{index}].role is unsupported")
        item["role"] = role
        normalized.append(item)
        if role == "heading":
            headings.append(element_id)
        elif role == "list_item":
            lists.append(element_id)
        elif role == "table_row":
            table_rows.append(element_id)
    return normalized, {"reading_order": [item["id"] for item in normalized],
                        "headings": headings, "lists": lists,
                        "tables": [{"row_ids": table_rows}] if table_rows else []}


def map_layout_output(result: Any) -> dict[str, Any]:
    """Map a normalized layout-engine-v1 result into a validated PageModel fragment.

    This intentionally accepts normalized adapter output rather than importing Docling
    or another parser. Engine-specific conversion and execution remain separate gates.
    """
    if not isinstance(result, dict) or result.get("schema_version") != 1:
        raise LayoutEngineError("layout result must use schema_version 1")
    pages = result.get("pages")
    if not isinstance(pages, list) or not pages or len(pages) > 500:
        raise LayoutEngineError("layout result pages must contain between 1 and 500 pages")
    mapped_pages: list[dict[str, Any]] = []
    for index, raw_page in enumerate(pages):
        if not isinstance(raw_page, dict):
            raise LayoutEngineError(f"pages[{index}] must be an object")
        page_number = raw_page.get("page_number", index + 1)
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
            raise LayoutEngineError(f"pages[{index}].page_number is invalid")
        elements, derived_layout = map_layout_elements(raw_page.get("elements", []), f"pages[{index}]")
        layout = raw_page.get("layout", derived_layout)
        if not isinstance(layout, dict):
            raise LayoutEngineError(f"pages[{index}].layout must be an object")
        mapped_pages.append({"page_number": page_number, "width": raw_page.get("width"),
                             "height": raw_page.get("height"), "rotation": raw_page.get("rotation", 0),
                             "coordinate_system": raw_page.get("coordinate_system", "top-left-points"),
                             "elements": elements, "layout": layout})
    return {"schema_version": 1, "pages": mapped_pages}
