"""Small, deterministic, CPU-only render contract used until E4-01 selects a PDF engine."""
from __future__ import annotations

import base64
import html
import math
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from app.codes import render_code
from app.security import validate_svg_markup
from app.template_logic import (
    MAX_LOOP_ITEMS,
    condition_matches,
    format_value,
    interpolate,
    render_blocks,
    resolve_path,
    translated_text,
    validate_data,
)

SUPPORTED_SCRIPTS = ("arabic", "hebrew", "devanagari", "tamil", "thai", "cjk", "korean", "latin")
SCRIPT_STACKS = {
    "arabic": "Noto Naskh Arabic, Noto Sans Arabic, sans-serif",
    "hebrew": "Noto Sans Hebrew, sans-serif",
    "devanagari": "Noto Sans Devanagari, sans-serif",
    "tamil": "Noto Sans Tamil, sans-serif",
    "thai": "Noto Sans Thai, sans-serif",
    "cjk": "Noto Sans CJK SC, Noto Sans CJK JP, sans-serif",
    "korean": "Noto Sans CJK KR, Noto Sans KR, sans-serif",
    "latin": "Noto Sans, sans-serif",
}

_RANGES = {
    "arabic": ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)),
    "hebrew": ((0x0590, 0x05FF),),
    "devanagari": ((0x0900, 0x097F),),
    "tamil": ((0x0B80, 0x0BFF),),
    "thai": ((0x0E00, 0x0E7F),),
    "cjk": ((0x2E80, 0x9FFF), (0xF900, 0xFAFF)),
    "korean": ((0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)),
}


def script_for(char: str) -> str:
    code = ord(char)
    for script, ranges in _RANGES.items():
        if any(start <= code <= end for start, end in ranges):
            return script
    return "latin"


def scripts_in(text: str) -> list[str]:
    return sorted({script_for(char) for char in text if not char.isspace()})


def _locale_direction(locale: str) -> str:
    language = locale.replace("_", "-").casefold().split("-", 1)[0]
    return "rtl" if language in {"ar", "fa", "he", "ur"} else "ltr"


def _diagnostic_missing_glyphs(texts: list[str]) -> list[str]:
    """Return deterministic warnings for characters outside the bounded script map.

    This is intentionally a diagnostic heuristic, not a font cmap or embedding check.
    Punctuation, combining marks, and symbols commonly covered by the fallback stack
    are not reported; unassigned characters and symbol/emoji characters are surfaced
    for review instead of being presented as known-supported glyphs.
    """
    warnings: set[str] = set()
    for text in texts:
        for char in text:
            category = unicodedata.category(char)
            if category in {"Cn", "So"} and script_for(char) == "latin":
                warnings.add(f"U+{ord(char):04X}")
    return sorted(warnings)


TABLE_BORDERS = {"grid", "horizontal", "none"}
MAX_STATIC_CELL_CHARS = 500
MAX_ROW_STYLES = 50
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")


def _bounded_number(value: Any, low: float, high: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        return None
    return round(float(value), 2)


def _table_styles(block: dict[str, Any]) -> tuple[str, str, str]:
    """Return (table style, shared cell style, header-only style) from bounded table properties (DD-431)."""
    table: list[str] = []
    family = block.get("font_family")
    if isinstance(family, str) and re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", family):
        table.append(f"font-family:{html.escape(family, quote=True)}")
    size = _bounded_number(block.get("font_size"), 8, 96)
    if size is not None:
        table.append(f"font-size:{size:g}px")
    for key, css in (("paragraph_spacing_before", "margin-top"), ("paragraph_spacing_after", "margin-bottom")):
        value = _bounded_number(block.get(key), 0, 240)
        if value is not None:
            table.append(f"{css}:{value:g}px")
    cell: list[str] = []
    # Cell styles are emitted only for properties the template sets, so existing tables keep the stylesheet
    # defaults (1px #cfd9cc grid, 6px padding) and their HTML unchanged.
    if any(key in block for key in ("borders", "border_color", "border_width")):
        cell.extend(_border_styles(block))
    if "cell_padding_x" in block or "cell_padding_y" in block:
        padding_x = _bounded_number(block.get("cell_padding_x", 6), 0, 48)
        padding_y = _bounded_number(block.get("cell_padding_y", 6), 0, 48)
        cell.append(f"padding:{6 if padding_y is None else padding_y:g}px {6 if padding_x is None else padding_x:g}px")
    row_height = _bounded_number(block.get("row_height"), 1, 400)
    if row_height is not None:
        # border-box: the row height includes borders and padding; otherwise each thin rule (rounded up to a
        # device pixel) made every row about 1 px taller than specified (DD-441).
        cell.append(f"box-sizing:border-box;height:{row_height:g}px")
    header: list[str] = []
    header_height = _bounded_number(block.get("header_row_height"), 1, 400)
    if header_height is not None:
        header.append(("" if row_height is not None else "box-sizing:border-box;") + f"height:{header_height:g}px")
    if block.get("header_bold") is False:
        header.append("font-weight:400")
    background = block.get("header_background")
    if isinstance(background, str) and _HEX_COLOR.fullmatch(background):
        header.append(f"background:{background}")
    return ";".join(table), ";".join(cell), ";".join(header)


def _border_styles(block: dict[str, Any]) -> list[str]:
    borders = block.get("borders", "grid") if block.get("borders", "grid") in TABLE_BORDERS else "grid"
    color = block.get("border_color") if isinstance(block.get("border_color"), str) and _HEX_COLOR.fullmatch(
        block["border_color"]) else "#cfd9cc"
    width = _bounded_number(block.get("border_width", 1), 0, 4)
    width = 1.0 if width is None else width
    rule = f"{width:g}px solid {color}"
    if borders == "grid":
        return [f"border:{rule}"]
    if borders == "horizontal":
        return [f"border:0;border-bottom:{rule}"]
    return ["border:0"]


def _row_styles(block: dict[str, Any], count: int) -> dict[int, str]:
    """Map body-row indexes to cell styles from bounded ``row_styles`` entries (DD-447).

    Each entry names a 0-based body row; a negative index counts from the end (-1 is the last row), so a
    totals row can be styled on a bound table whose length varies. Invalid entries, unknown keys and rows
    outside the table are ignored; a later entry for the same row overrides an earlier one per property.
    """
    entries = block.get("row_styles")
    if not isinstance(entries, list):
        return {}
    merged: dict[int, dict[str, str]] = {}
    for entry in entries[:MAX_ROW_STYLES]:
        if not isinstance(entry, dict) or isinstance(entry.get("row"), bool) or not isinstance(entry.get("row"), int):
            continue
        index = entry["row"] + count if entry["row"] < 0 else entry["row"]
        if not 0 <= index < count:
            continue
        styles = merged.setdefault(index, {})
        for key, css, on, off in (("bold", "font-weight", "700", "400"), ("italic", "font-style", "italic", "normal")):
            if isinstance(entry.get(key), bool):
                styles[css] = on if entry[key] else off
        for key, css in (("background", "background"), ("color", "color")):
            if isinstance(entry.get(key), str) and _HEX_COLOR.fullmatch(entry[key]):
                styles[css] = entry[key]
    return {index: ";".join(f"{css}:{value}" for css, value in styles.items()) for index, styles in merged.items() if styles}


def _render_table(block: dict[str, Any], data: Any, locale: str, policy: str,
                  missing: list[str]) -> tuple[str, list[str]]:
    columns = block.get("columns")
    static = block.get("data_mode") == "static"
    if not isinstance(columns, list) or not columns or len(columns) > 50:
        raise ValueError("table.columns must contain between 1 and 50 columns")
    normalized: list[dict[str, Any]] = []
    for column in columns:
        if not isinstance(column, dict) or not isinstance(column.get("header"), str) or (
                not static and not isinstance(column.get("path"), str)):
            raise ValueError("table columns require header and path")
        if column.get("format") not in {None, "text", "number", "currency", "date", "percent"}:
            raise ValueError("unsupported table column format")
        width = column.get("width")
        if width is not None and (isinstance(width, bool) or not isinstance(width, (int, float)) or not 5 <= width <= 100):
            raise ValueError("table column width must be between 5 and 100")
        align = column.get("align") if column.get("align") in {"left", "center", "right"} else None
        normalized.append({"header": column["header"], "path": column.get("path", ""),
                           "format": column.get("format") or "text", "width": width, "align": align})
    body_rows: list[list[str]] = []
    if static:
        # Static rows (DD-431): fixed cell text with {{path}} interpolation, no data array required.
        static_rows = block.get("static_rows")
        if not isinstance(static_rows, list) or len(static_rows) > MAX_LOOP_ITEMS:
            raise ValueError(f"table.static_rows must be an array of at most {MAX_LOOP_ITEMS} rows")
        for raw in static_rows:
            if not isinstance(raw, list) or len(raw) > len(normalized):
                raise ValueError("each static row must be an array with at most one cell per column")
            cells = [str(value)[:MAX_STATIC_CELL_CHARS] if value is not None else "" for value in raw]
            cells += [""] * (len(normalized) - len(cells))
            body_rows.append([interpolate(cell, data, locale, policy,
                                          lambda path: missing.append(path) if path not in missing else None)
                              for cell in cells])
    else:
        items_path = block.get("items")
        if not isinstance(items_path, str) or not items_path:
            raise ValueError("table.items is required")
        items, found = resolve_path(data, items_path)
        if not found or items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError(f"Table source is not an array: {items_path}")
        if len(items) > MAX_LOOP_ITEMS:
            raise ValueError(f"Table exceeds {MAX_LOOP_ITEMS} rows: {items_path}")
        row_condition = block.get("row_condition")
        if row_condition is not None:
            if not isinstance(row_condition, dict) or not isinstance(row_condition.get("path"), str) or not row_condition["path"]:
                raise ValueError("table row_condition requires a path")
            if "equals" not in row_condition:
                raise ValueError("table row_condition requires equals")
            items = [item for item in items if isinstance(item, dict) and condition_matches({"path": row_condition["path"], "equals": row_condition["equals"]}, item, policy)]
        for item in items:
            row: list[str] = []
            for column in normalized:
                value, present = resolve_path(item, column["path"])
                if not present or value is None:
                    if policy == "error":
                        raise ValueError(f"Missing table field: {items_path}.{column['path']}")
                    value = f"[[{items_path}.{column['path']}]]" if policy == "placeholder" else ""
                    if not present and f"{items_path}.{column['path']}" not in missing:
                        missing.append(f"{items_path}.{column['path']}")
                row.append(format_value(value, locale, column["format"]))
            body_rows.append(row)
    table_style, cell_style, header_style = _table_styles(block)

    row_styles = _row_styles(block, len(body_rows))

    def cell_attribute(column: dict[str, Any], header: bool, row_style: str = "") -> str:
        parts = [cell_style] + ([header_style] if header and header_style else []) + [row_style]
        if column["align"]:
            parts.append(f"text-align:{column['align']}")
        joined = ";".join(part for part in parts if part)
        return f' style="{joined}"' if joined else ""

    colgroup = "".join(f"<col style=\"width:{column['width']}%\" />" if column.get("width") is not None else "<col />" for column in normalized)
    show_header = block.get("show_header") is not False
    headers = "".join(f"<th scope=\"col\" dir=\"auto\"{cell_attribute(column, True)}>{html.escape(column['header'])}</th>"
                      for column in normalized)
    # Per-row styles go on each cell, not the <tr>, so they combine with the cell borders and padding (DD-447).
    rows = "".join("<tr>" + "".join(f"<td dir=\"auto\"{cell_attribute(column, False, row_styles.get(index, ''))}>"
                                    f"{html.escape(value)}</td>" for column, value in zip(normalized, row, strict=True))
                   + "</tr>" for index, row in enumerate(body_rows))
    flow = _flow_classes(block)
    spacing = _bounded_number(block.get("header_spacing_after"), 0, 240)
    # Space between the header row and the first body row (DD-445): a borderless, unshaded spacer row inside
    # <thead>, so it repeats with the header on each printed page and leaves collapsed borders untouched.
    spacer = (f'<tr class="table-header-gap" aria-hidden="true"><td colspan="{len(normalized)}" '
              f'style="height:{spacing:g}px;padding:0;border:0;background:none"></td></tr>') if spacing else ""
    head = f"<thead><tr>{headers}</tr>{spacer}</thead>" if show_header else ""
    style_attribute = f' style="{table_style}"' if table_style else ""
    fragment = (f"<table class=\"template-table{(' ' + flow) if flow else ''}\"{style_attribute}><colgroup>{colgroup}</colgroup>"
                f"{head}<tbody>{rows}</tbody></table>")
    return fragment, [value for row in body_rows for value in row] + ([column["header"] for column in normalized] if show_header else [])


def _page_settings(page: Any) -> dict[str, Any]:
    if not isinstance(page, dict):
        page = {}
    size = page.get("size", "A4")
    orientation = page.get("orientation", "portrait")
    if size not in {"A3", "A4", "A5", "Letter"}:
        raise ValueError("page.size must be A3, A4, A5, or Letter")
    if orientation not in {"portrait", "landscape"}:
        raise ValueError("page.orientation must be portrait or landscape")
    legacy_margin = page.get("margin_mm", 20)
    if isinstance(legacy_margin, bool) or not isinstance(legacy_margin, (int, float)) or not 0 <= legacy_margin <= 100:
        raise ValueError("page.margin_mm must be between 0 and 100")
    margins = {}
    for name in ("top", "right", "bottom", "left"):
        value = page.get(f"margin_{name}_mm", legacy_margin)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError(f"page.margin_{name}_mm must be between 0 and 100")
        margins[name] = value
    font_size = page.get("header_footer_font_size", 12)
    if isinstance(font_size, bool) or not isinstance(font_size, (int, float)) or not 6 <= font_size <= 48:
        font_size = 12
    number_format = page.get("page_number_format", "{page}")
    if not isinstance(number_format, str) or not number_format.strip() or len(number_format) > 40:
        number_format = "{page}"
    return {"size": size, "orientation": orientation, "margin_mm": legacy_margin, "margins": margins,
            "header": str(page.get("header", ""))[:500], "footer": str(page.get("footer", ""))[:500],
            "header_align": page.get("header_align") if page.get("header_align") in BOX_ALIGNMENTS else "left",
            "footer_align": page.get("footer_align") if page.get("footer_align") in BOX_ALIGNMENTS else "left",
            "show_page_numbers": page.get("show_page_numbers", False) is True,
            "page_number_position": (page.get("page_number_position")
                                     if page.get("page_number_position") in PAGE_NUMBER_POSITIONS else "footer-right"),
            "page_number_format": number_format,
            "header_footer_font_size": round(float(font_size), 2),
            # DD-437: per-zone texts, distances from the page edge, and header/footer rules.
            "zones": {band: {align: str(page.get(f"{band}_{align}", ""))[:500] for align in BOX_ALIGNMENTS
                             if isinstance(page.get(f"{band}_{align}"), str) and page.get(f"{band}_{align}")}
                      for band in ("header", "footer")},
            "distances": {band: _bounded_number(page.get(f"{band}_distance_mm"), 0, 100) for band in ("header", "footer")},
            "rules": {band: (_bounded_number(page.get(f"{band}_rule_offset_mm", 0), 0, 100) or 0.0)
                      for band in ("header", "footer") if page.get(f"{band}_rule") is True},
            "rule_color": page.get("furniture_rule_color") if isinstance(page.get("furniture_rule_color"), str)
            and _HEX_COLOR.fullmatch(page["furniture_rule_color"]) else "#000000",
            "rule_width": _bounded_number(page.get("furniture_rule_width", 0.75), 0, 4) or 0.75,
            "zone_styles": _zone_styles(page.get("zone_styles")),
            "background": page.get("background", "") if isinstance(page.get("background", ""), str) else ""}


BOX_ALIGNMENTS = ("left", "center", "right")
PAGE_NUMBER_POSITIONS = tuple(f"{band}-{align}" for band in ("header", "footer") for align in BOX_ALIGNMENTS)


def css_string(value: str) -> str:
    """Quote text as a CSS string; everything except plain ASCII letters, digits and spaces is hex-escaped."""
    return '"' + "".join(char if char.isascii() and (char.isalnum() or char == " ") else f"\\{ord(char):x} "
                         for char in value) + '"'


def page_number_content(number_format: str) -> str:
    """CSS ``content`` for a page-number format with ``{page}`` and ``{pages}`` tokens."""
    parts: list[str] = []
    for index, piece in enumerate(re.split(r"(\{page\}|\{pages\})", number_format)):
        if index % 2:
            parts.append("counter(page)" if piece == "{page}" else "counter(pages)")
        elif piece:
            parts.append(css_string(piece))
    return " ".join(parts) or "counter(page)"


ZONES = tuple(f"{band}_{align}" for band in ("header", "footer") for align in BOX_ALIGNMENTS)


def _zone_styles(raw: Any) -> dict[str, dict[str, Any]]:
    """Per-zone furniture styling (DD-439): font size (6-48 px), bold and italic, keyed by zone name."""
    styles: dict[str, dict[str, Any]] = {}
    for zone, value in (raw.items() if isinstance(raw, dict) else []):
        if zone not in ZONES or not isinstance(value, dict):
            continue
        style: dict[str, Any] = {}
        size = _bounded_number(value.get("font_size"), 6, 48)
        if size is not None:
            style["font_size"] = size
        for key in ("bold", "italic"):
            if value.get(key) is True:
                style[key] = True
        if style:
            styles[zone] = style
    return styles


def margin_boxes_css(page: dict[str, Any], zones: dict[str, dict[str, str]], font_family: str) -> str:
    """Running header, footer and page numbers as @page margin boxes (DD-429, DD-437).

    Paged-media engines repeat margin boxes on every page and resolve page counters in them, so the PDF
    needs no post-processing overlay and the content never collides with the body flow. Each band has left,
    centre and right zones; a distance pins text to the page edge instead of centring it in the margin; a
    rule is the bottom (header) or top (footer) border of all three boxes, offset from the content area.
    """
    boxes: dict[str, list[str]] = {}
    for band, side in (("header", "top"), ("footer", "bottom")):
        for align in BOX_ALIGNMENTS:
            if zones[band].get(align):
                boxes.setdefault(f"{side}-{align}", []).append(css_string(zones[band][align]))
    if page["show_page_numbers"]:
        band, align = page["page_number_position"].split("-")
        boxes.setdefault(f"{'top' if band == 'header' else 'bottom'}-{align}", []).append(
            page_number_content(page["page_number_format"]))
    for band, side in (("header", "top"), ("footer", "bottom")):
        if band in page["rules"]:
            for align in BOX_ALIGNMENTS:  # every box carries the border so the rule spans the full width
                boxes.setdefault(f"{side}-{align}", [])
    rules = []
    for box, parts in boxes.items():
        side, align = box.split("-")
        band = "header" if side == "top" else "footer"
        zone_style = page["zone_styles"].get(f"{band}_{align}", {})
        style = [f"content:{' \" \" '.join(parts) if parts else '\"\"'}", f"font-family:{font_family}",
                 f"font-size:{zone_style.get('font_size', page['header_footer_font_size']):g}px", f"text-align:{align}"]
        if zone_style.get("bold"):
            style.append("font-weight:700")
        if zone_style.get("italic"):
            style.append("font-style:italic")
        distance = page["distances"][band]
        if distance is not None:
            style += ([f"vertical-align:top;padding-top:{distance:g}mm"] if side == "top"
                      else [f"vertical-align:bottom;padding-bottom:{distance:g}mm"])
        if band in page["rules"]:
            border = f"{page['rule_width']:g}px solid {page['rule_color']}"
            offset = page["rules"][band]
            style.append(f"border-bottom:{border};margin-bottom:{offset:g}mm" if side == "top"
                         else f"border-top:{border};margin-top:{offset:g}mm")
        rules.append(f"@{box}{{{';'.join(style)};}}")
    return "".join(rules)


def page_number_preview(number_format: str) -> str:
    """Screen-preview text for the page number (page 1 of 1); the PDF uses live counters."""
    return number_format.replace("{pages}", "1").replace("{page}", "1")


def _document_metadata(definition: dict[str, Any]) -> dict[str, str]:
    metadata = definition.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")  # noqa: TRY004
    default_title = definition.get("name", "Document")
    title = metadata.get("title", default_title)
    author = metadata.get("author", "")
    if not isinstance(title, str) or not isinstance(author, str):
        raise ValueError("metadata.title and metadata.author must be strings")  # noqa: TRY004
    return {"title": title[:200], "author": author[:200]}


def _flow_classes(block: dict[str, Any]) -> str:
    classes = []
    if block.get("break_before") is True:
        classes.append("page-break-before")
    if block.get("keep_together") is True:
        classes.append("keep-together")
    return " ".join(classes)


def _offset_style(block: dict[str, Any]) -> str:
    horizontal = block.get("offset_x", 0)
    vertical = block.get("offset_y", 0)
    if isinstance(horizontal, bool) or not isinstance(horizontal, (int, float)):
        horizontal = 0
    if isinstance(vertical, bool) or not isinstance(vertical, (int, float)):
        vertical = 0
    bounded_x = max(-160, min(160, float(horizontal)))
    bounded_y = max(-160, min(160, float(vertical)))
    if bounded_x == 0 and bounded_y == 0:
        return ""
    return f"transform:translate({bounded_x:g}px,{bounded_y:g}px);"


def _layout_style(block: dict[str, Any], scope: str = "all") -> list[str]:
    """Return bounded Word-like layout styles for local/PDF parity.

    ``scope`` selects block-level placement (absolute position, keep-with-next, page break after),
    paragraph-level layout (line height, spacing, indents), or both. Rich-text blocks apply the block
    scope to their section and the paragraph scope to each paragraph, so nothing is applied twice (DD-428).
    """
    styles: list[str] = []
    block_scope, paragraph_scope = scope in {"all", "block"}, scope in {"all", "paragraph"}
    if block_scope and block.get("position_mode") == "absolute":
        x = block.get("position_x", 0)
        y = block.get("position_y", 0)
        if isinstance(x, (int, float)) and not isinstance(x, bool) and isinstance(y, (int, float)) and not isinstance(y, bool):
            unit = "mm" if block.get("position_unit") == "mm" else "px"
            max_x, max_y = (320, 450) if unit == "mm" else (1200, 2000)
            # right:0 gives the block the width from its left edge to the content area's right edge, like a text
            # box; without it the block shrank to its text and centred or right-aligned text could not align (DD-441).
            styles.extend(("position:absolute", f"left:{max(0, min(max_x, float(x))):g}{unit}", f"top:{max(0, min(max_y, float(y))):g}{unit}",
                           "right:0"))
    line_height = block.get("line_height")
    if paragraph_scope and isinstance(line_height, (int, float)) and not isinstance(line_height, bool) and 0.8 <= line_height <= 3:
        styles.append(f"line-height:{float(line_height):g}")
    for key, css in (("paragraph_spacing_before", "margin-top"), ("paragraph_spacing_after", "margin-bottom"),
                     ("first_line_indent", "text-indent"), ("left_indent", "padding-left"), ("right_indent", "padding-right")):
        value = block.get(key)
        minimum = 0 if key in {"paragraph_spacing_before", "paragraph_spacing_after"} else -240
        if paragraph_scope and isinstance(value, (int, float)) and not isinstance(value, bool) and minimum <= value <= 240:
            styles.append(f"{css}:{float(value):g}px")
    if block_scope and block.get("keep_with_next") is True:
        styles.append("break-after:avoid;page-break-after:avoid")
    if block_scope and block.get("break_after") is True:
        styles.append("break-after:page;page-break-after:always")
    return styles


TAB_MARK = ""  # private-use separator between tab segments of rendered rich-text runs
TAB_LEADERS = {"none", "dot", "underscore", "hyphen"}
MAX_TAB_STOPS = 16
ALIGNMENTS = {"left", "center", "right", "justify"}


def tab_stops(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise ``tab_stops`` (DD-426): numbers are left stops; objects carry position/align/leader.

    Positions are CSS px from the paragraph's left indent, as in word processors, bounded to 0-2000;
    0 is the left indent itself, the implicit stop of a hanging indent.
    """
    stops: dict[float, dict[str, Any]] = {}
    raw = block.get("tab_stops")
    for item in raw[:MAX_TAB_STOPS] if isinstance(raw, list) else []:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            item = {"position": item}
        if not isinstance(item, dict):
            continue
        position = item.get("position")
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not 0 <= position <= 2000:
            continue
        align = item.get("align", "left") if item.get("align", "left") in {"left", "right"} else "left"
        leader = item.get("leader", "none") if item.get("leader", "none") in TAB_LEADERS else "none"
        stops[round(float(position), 2)] = {"position": round(float(position), 2), "align": align, "leader": leader}
    return [stops[key] for key in sorted(stops)]


def _tab_box(width: float, left: str, leader: str, right: str = "") -> str:
    fill = f'<span class="tab-fill leader-{leader}"></span>'
    return f'<span class="tab-box" style="width:{width:g}px">{left}{fill}{right}</span>'


def tabbed_html(segments: list[str], stops: list[dict[str, Any]], first_line_px: float = 0.0) -> str:
    """Lay out already-escaped tab segments at stop positions (DD-426).

    The text before a left stop sits in a box that ends at the stop, so the next segment starts there.
    A right stop's box ends at the stop and right-aligns the segment after the tab. Leaders fill the
    space inside the box. Text after the last tab stays inline and wraps with the paragraph's indents.
    Tabs beyond the defined stops remain literal tab characters.
    """
    boundary = first_line_px
    pending = segments[0]
    output: list[str] = []
    remaining = list(stops)
    index = 1
    while index < len(segments):
        while remaining and remaining[0]["position"] <= boundary + 0.5:
            remaining.pop(0)
        if not remaining:
            break
        stop = remaining.pop(0)
        width = stop["position"] - boundary
        if stop["align"] == "right":
            output.append(_tab_box(width, pending, stop["leader"], segments[index]))
            pending = ""
        else:
            output.append(_tab_box(width, pending, stop["leader"]))
            pending = segments[index]
        boundary = stop["position"]
        index += 1
    output.append("\t".join([pending, *segments[index:]]))
    return "".join(output)


def _bounded_media_source(block: dict[str, Any], data: dict[str, Any], locale: str,
                          policy: str, missing: list[str], definition: dict[str, Any]) -> str:
    source = block.get("src", block.get("source", ""))
    if isinstance(source, str) and source.startswith("{{") and source.endswith("}}"):
        path = source[2:-2].strip()
        value, found = resolve_path(data, path)
        if not found or value is None:
            if policy == "error":
                raise ValueError(f"Missing image field: {path}")
            if path not in missing:
                missing.append(path)
            return ""
        source = value
    if not isinstance(source, str) or len(source) > 2_000_000:
        raise ValueError("image.src must be a bounded string")
    if source.startswith("data:image/"):
        if not re.fullmatch(r"data:image/(?:png|jpeg|gif|webp|svg\+xml);base64,[A-Za-z0-9+/=]+", source):
            raise ValueError("image data URI must be base64 PNG, JPEG, GIF, WebP, or SVG")
        if source.startswith("data:image/svg+xml;base64,"):
            encoded = source.split(",", 1)[1]
            try:
                svg = base64.b64decode(encoded, validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                raise ValueError("SVG image data must be valid UTF-8") from None
            validate_svg_markup(svg.encode("utf-8"))
        return source
    parsed = urlparse(source)
    if source.startswith("/api/assets/") and re.fullmatch(r"/api/assets/[0-9a-f]{32}\.(?:png|jpg|gif|webp|svg)", source):
        return source
    allowed_hosts = {str(host).casefold() for host in definition.get("allowed_image_hosts", []) if isinstance(host, str)}
    if parsed.scheme in {"http", "https"} and parsed.hostname and definition.get("allow_external_sources") is True and parsed.hostname.casefold() in allowed_hosts:
        return source
    raise ValueError("image source must be a base64 image or explicitly allowed HTTP(S) URL")


def _render_image(block: dict[str, Any], data: dict[str, Any], locale: str, policy: str,
                  missing: list[str], definition: dict[str, Any]) -> tuple[str, str]:
    source = _bounded_media_source(block, data, locale, policy, missing, definition)
    if not source:
        return "", ""
    alt = str(block.get("alt", "Image"))[:200]
    width = block.get("width", 240)
    height = block.get("height")
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not 1 <= width <= 1200:
        raise ValueError("image.width must be between 1 and 1200")
    image_size = f"width:{width:g}px"
    if isinstance(height, (int, float)) and not isinstance(height, bool) and 1 <= height <= 1200:
        image_size += f";height:{height:g}px"
    align = block.get("align", "left")
    if align not in {"left", "center", "right"}:
        align = "left"
    flow = _flow_classes(block)
    classes = f"template-image image-align-{align}{(' ' + flow) if flow else ''}"
    # Do not rely on text-align for replaced elements.  Some PDF engines
    # preserve the figure's text alignment in HTML preview but position the
    # image at the figure's start edge during pagination.  Explicit margins
    # are stable in both browser and PDF layout and make the intended geometry
    # inspectable in the generated artifact.
    horizontal_margin = {
        "left": "margin-left:0;margin-right:auto;",
        "center": "margin-left:auto;margin-right:auto;",
        "right": "margin-left:auto;margin-right:0;",
    }[align]
    # Keep the geometry on the replaced element itself.  A few PDF engines
    # preserve the figure's text alignment but place an inline image at the
    # figure's start edge; inline margins on a block image avoid that split.
    offset_style = _offset_style(block)
    figure_style = f"text-align:{align}" + (f";{offset_style}" if offset_style else "")
    return f'<figure class="{classes}" style="{figure_style}"><img src="{html.escape(source, quote=True)}" alt="{html.escape(alt, quote=True)}" style="display:block;{horizontal_margin}{image_size}" /></figure>', alt


def _render_code(block: dict[str, Any], data: dict[str, Any], locale: str, policy: str,
                 missing: list[str]) -> tuple[str, str]:
    source = block.get("value", "")
    if isinstance(source, str) and source.startswith("{{") and source.endswith("}}"):
        path = source[2:-2].strip()
        source, found = resolve_path(data, path)
        if not found or source is None:
            if policy == "error":
                raise ValueError(f"Missing code field: {path}")
            if path not in missing:
                missing.append(path)
            return "", ""
    kind = str(block.get("code_type", block.get("type_name", "qr"))).lower()
    svg = render_code(kind, source)
    label = str(block.get("alt", f"{kind} code"))[:200]
    width = block.get("width", 220)
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not 40 <= width <= 1200:
        raise ValueError("code.width must be between 40 and 1200")
    flow = _flow_classes(block)
    classes = f"template-code{(' ' + flow) if flow else ''}"
    return f'<figure class="{classes}" style="width:{width:g}px" role="img" aria-label="{html.escape(label, quote=True)}">{svg}</figure>', label


def _render_chart(block: dict[str, Any], data: Any, locale: str, policy: str,
                  missing: list[str]) -> tuple[str, str]:
    items_path = block.get("items")
    if not isinstance(items_path, str):
        raise ValueError("chart.items is required")
    items, found = resolve_path(data, items_path)
    if not found or not isinstance(items, list) or len(items) > 100:
        items = []
    chart_type = block.get("chart_type", "bar")
    if chart_type not in {"bar", "line", "pie"}:
        raise ValueError("chart.chart_type must be bar, line, or pie")
    orientation = block.get("chart_orientation", "vertical")
    if orientation not in {"vertical", "horizontal"}:
        orientation = "vertical"
    show_legend = block.get("show_legend", True) is not False
    show_grid = block.get("show_grid", True) is not False
    show_points = block.get("show_points", True) is not False
    donut = block.get("donut", False) is True
    label_path = str(block.get("label_path", "label"))
    value_path = str(block.get("value_path", "value"))
    values: list[tuple[str, float]] = []
    for item in items:
        label, label_found = resolve_path(item, label_path)
        value, value_found = resolve_path(item, value_path)
        if not label_found or not value_found:
            missing.append(f"{items_path}.{label_path if not label_found else value_path}")
            continue
        try:
            values.append((str(label), float(value)))
        except (TypeError, ValueError):
            continue
    maximum = max((value for _, value in values), default=1) or 1
    width, height = 600, 300
    shapes = []
    if block.get("chart_title"):
        shapes.append(f'<text x="300" y="20" text-anchor="middle" class="chart-title">{html.escape(str(block["chart_title"])[:120])}</text>')
    if show_grid and chart_type in {"bar", "line"}:
        for grid_y in (70, 120, 170, 220):
            shapes.append(f'<line x1="40" y1="{grid_y}" x2="560" y2="{grid_y}" class="chart-grid" />')
    for index, (label, value) in enumerate(values):
        x = 20 + index * max(40, (width - 40) / max(1, len(values)))
        bar_height = max(1, 190 * value / maximum)
        if chart_type == "bar":
            if orientation == "horizontal":
                bar_width = max(1, 500 * max(0, value) / maximum)
                y = 45 + index * max(24, 170 / max(1, len(values)))
                shapes.append(f'<rect x="40" y="{y:.1f}" width="{bar_width:.1f}" height="18" aria-label="{html.escape(label)} {value:g}" />')
                shapes.append(f'<text x="35" y="{y + 13:.1f}" text-anchor="end">{html.escape(label[:40])}</text>')
            else:
                shapes.append(f'<rect x="{x:.1f}" y="{220 - bar_height:.1f}" width="28" height="{bar_height:.1f}" aria-label="{html.escape(label)} {value:g}" />')
                shapes.append(f'<text x="{x + 14:.1f}" y="240" text-anchor="middle">{html.escape(label[:20])}</text>')
    if chart_type == "line" and values:
        points = " ".join(f"{20 + index * max(40, (width - 40) / max(1, len(values) - 1)):.1f},{220 - max(1, 190 * value / maximum):.1f}" for index, (_, value) in enumerate(values))
        shapes.append(f'<polyline points="{points}" fill="none" stroke="currentColor" stroke-width="3" aria-label="{html.escape(chart_type)} chart" />')
        for index, (label, value) in enumerate(values):
            x = 20 + index * max(40, (width - 40) / max(1, len(values) - 1))
            y = 220 - max(1, 190 * value / maximum)
            if show_points:
                shapes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" aria-label="{html.escape(label)} {value:g}" />')
    if chart_type == "pie" and values:
        total = sum(max(0, value) for _, value in values) or 1
        start = -math.pi / 2
        cx, cy, radius = 300, 130, 100
        for index, (label, value) in enumerate(values):
            sweep = 2 * math.pi * max(0, value) / total
            end = start + sweep
            x1, y1 = cx + radius * math.cos(start), cy + radius * math.sin(start)
            x2, y2 = cx + radius * math.cos(end), cy + radius * math.sin(end)
            large = 1 if sweep > math.pi else 0
            path = f"M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z"
            shapes.append(f'<path d="{path}" aria-label="{html.escape(label)} {value:g}" />')
            start = end
        if donut:
            shapes.append('<circle cx="300" cy="130" r="48" class="chart-donut-hole" />')
    if show_legend and values:
        legend = " · ".join(label[:24] for label, _ in values[:8])
        shapes.append(f'<text x="300" y="280" text-anchor="middle" class="chart-legend">{html.escape(legend)}</text>')
    if block.get("x_axis_label"):
        shapes.append(f'<text x="300" y="258" text-anchor="middle" class="chart-axis-label">{html.escape(str(block["x_axis_label"])[:80])}</text>')
    if block.get("y_axis_label"):
        shapes.append(f'<text x="10" y="150" text-anchor="middle" class="chart-axis-label" transform="rotate(-90 10 150)">{html.escape(str(block["y_axis_label"])[:80])}</text>')
    fragment = f'<figure class="template-chart" role="img" aria-label="{html.escape(str(block.get("alt", chart_type + " chart")), quote=True)}" style="{_offset_style(block)}"><svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{"".join(shapes)}</svg></figure>'
    return fragment, " ".join(label for label, _ in values)


def _render_chart_robust(block: dict[str, Any], data: Any, locale: str, policy: str,
                         missing: list[str]) -> tuple[str, str]:
    """Render the bounded chart contract used by the editor and PDF path.

    The contract is intentionally declarative: a template can select paths,
    series and presentation values, but cannot execute code or inject SVG.
    Flat v1 fields remain the public compatibility surface.
    """
    items_path = block.get("items")
    if not isinstance(items_path, str) or not items_path.strip():
        raise ValueError("chart.items is required")
    if block.get("data_mode", "bound") == "static":
        items = block.get("static_data", [])
    else:
        items, found = resolve_path(data, items_path)
        if not found:
            if items_path not in missing:
                missing.append(items_path)
            items = []
    if not isinstance(items, list) or len(items) > 100:
        items = []
    chart_type = block.get("chart_type", "bar")
    if chart_type not in {"bar", "line", "pie"}:
        raise ValueError("chart.chart_type must be bar, line, or pie")
    orientation = block.get("chart_orientation", "vertical")
    if orientation not in {"vertical", "horizontal"}:
        orientation = "vertical"
    show_legend = block.get("show_legend", True) is not False
    show_grid = block.get("show_grid", True) is not False
    show_points = block.get("show_points", True) is not False
    show_values = block.get("show_values", False) is True
    stacked = block.get("stacked", False) is True
    donut = block.get("donut", False) is True
    label_path = str(block.get("label_path", "label"))
    value_path = str(block.get("value_path", "value"))
    series_path = block.get("series_path")
    series_path = str(series_path) if isinstance(series_path, str) and series_path.strip() else None
    fallback_palette = ["#2f6f63", "#d97941", "#4d78a8", "#8b5e83", "#6a994e", "#c94c4c"]
    palette = block.get("colors", fallback_palette)
    if not isinstance(palette, list):
        palette = fallback_palette
    palette = [str(color) for color in palette if isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color)]
    palette = palette or fallback_palette
    def color(value: Any, fallback: str) -> str:
        return str(value) if isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else fallback
    background = color(block.get("background_color"), "#ffffff")
    grid = color(block.get("grid_color"), "#d9e2df")
    axis = color(block.get("axis_color"), "#203d37")
    series: dict[str, list[tuple[str, float]]] = {}
    categories: list[str] = []
    for item in items:
        label, label_found = resolve_path(item, label_path)
        value, value_found = resolve_path(item, value_path)
        if not label_found or not value_found:
            path = f"{items_path}.{label_path if not label_found else value_path}"
            if path not in missing:
                missing.append(path)
            continue
        try:
            category = str(label)[:80]
            series_name = "Series 1"
            if series_path:
                series_value, series_found = resolve_path(item, series_path)
                if series_found and series_value is not None:
                    series_name = str(series_value)[:80] or "Series 1"
            series.setdefault(series_name, []).append((category, float(value)))
            if category not in categories:
                categories.append(category)
        except (TypeError, ValueError):
            continue
    names = list(series)
    values = [(label, value) for label, value in series.get(names[0], [])] if names else []
    all_values = [value for rows in series.values() for _, value in rows]
    maximum = max(all_values, default=1) or 1
    width, height = 600, 300
    shapes = [f'<rect x="0" y="0" width="{width}" height="{height}" fill="{background}" rx="4" />']
    if block.get("chart_title"):
        shapes.append(f'<text x="300" y="20" text-anchor="middle" class="chart-title">{html.escape(str(block["chart_title"])[:120])}</text>')
    if show_grid and chart_type in {"bar", "line"}:
        for grid_y in (70, 120, 170, 220):
            shapes.append(f'<line x1="40" y1="{grid_y}" x2="560" y2="{grid_y}" stroke="{grid}" class="chart-grid" />')
    if chart_type == "bar":
        if orientation == "horizontal":
            row_height = min(28, 170 / max(1, len(categories)))
            for index, category in enumerate(categories):
                y = 45 + index * max(24, row_height)
                shapes.append(f'<text x="35" y="{y + 13:.1f}" text-anchor="end" fill="{axis}">{html.escape(category[:40])}</text>')
                for series_index, name in enumerate(names):
                    value = next((value for label, value in series[name] if label == category), 0)
                    bar_width = max(0, 500 * max(0, value) / maximum)
                    offset_y = y + series_index * min(18, row_height / max(1, len(names)))
                    bar_height = max(8, min(14, row_height / max(1, len(names))))
                    shapes.append(f'<rect x="40" y="{offset_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{palette[series_index % len(palette)]}" aria-label="{html.escape(name)} {html.escape(category)} {value:g}" />')
                    if show_values:
                        shapes.append(f'<text x="{40 + bar_width + 4:.1f}" y="{offset_y + 11:.1f}" fill="{axis}">{value:g}</text>')
        else:
            slot = 500 / max(1, len(categories))
            bar_width = max(5, min(34, slot / max(1, len(names)) - 4))
            for index, category in enumerate(categories):
                base_x = 40 + index * slot
                stack_height = 0
                for series_index, name in enumerate(names):
                    value = next((value for label, value in series[name] if label == category), 0)
                    bar_height = max(0, 170 * value / maximum)
                    x = base_x + (0 if stacked else series_index * (bar_width + 3))
                    y = 220 - (stack_height + bar_height if stacked else bar_height)
                    shapes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{palette[series_index % len(palette)]}" aria-label="{html.escape(name)} {html.escape(category)} {value:g}" />')
                    if show_values:
                        shapes.append(f'<text x="{x + bar_width / 2:.1f}" y="{max(40, y - 3):.1f}" text-anchor="middle" fill="{axis}">{value:g}</text>')
                    if stacked:
                        stack_height += bar_height
                shapes.append(f'<text x="{base_x + slot / 2:.1f}" y="240" text-anchor="middle" fill="{axis}">{html.escape(category[:20])}</text>')
    elif chart_type == "line" and categories:
        x_step = 520 / max(1, len(categories) - 1)
        for series_index, name in enumerate(names):
            points = []
            for index, category in enumerate(categories):
                value = next((value for label, value in series[name] if label == category), 0)
                points.append(f"{40 + index * x_step:.1f},{220 - max(0, 170 * value / maximum):.1f}")
            series_color = palette[series_index % len(palette)]
            shapes.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{series_color}" stroke-width="3" aria-label="{html.escape(name)} series" />')
            if show_points:
                for index, category in enumerate(categories):
                    value = next((value for label, value in series[name] if label == category), 0)
                    shapes.append(f'<circle cx="{40 + index * x_step:.1f}" cy="{220 - max(0, 170 * value / maximum):.1f}" r="5" fill="{series_color}" aria-label="{html.escape(name)} {html.escape(category)} {value:g}" />')
        for index, category in enumerate(categories):
            shapes.append(f'<text x="{40 + index * x_step:.1f}" y="240" text-anchor="middle" fill="{axis}">{html.escape(category[:20])}</text>')
    elif chart_type == "pie" and values:
        total = sum(max(0, value) for _, value in values) or 1
        start = -math.pi / 2
        cx, cy, radius = 300, 130, 100
        for index, (label, value) in enumerate(values):
            sweep = 2 * math.pi * max(0, value) / total
            end = start + sweep
            x1, y1 = cx + radius * math.cos(start), cy + radius * math.sin(start)
            x2, y2 = cx + radius * math.cos(end), cy + radius * math.sin(end)
            large = 1 if sweep > math.pi else 0
            path = f"M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z"
            shapes.append(f'<path d="{path}" fill="{palette[index % len(palette)]}" aria-label="{html.escape(label)} {value:g}" />')
            start = end
        if donut:
            shapes.append('<circle cx="300" cy="130" r="48" class="chart-donut-hole" />')
    if show_legend and (values or names):
        legend_values = [name for name in (names if chart_type != "pie" else [label for label, _ in values])][:8]
        shapes.append(f'<text x="300" y="280" text-anchor="middle" class="chart-legend" fill="{axis}">{html.escape(" · ".join(legend_values))}</text>')
    if block.get("x_axis_label"):
        shapes.append(f'<text x="300" y="258" text-anchor="middle" class="chart-axis-label">{html.escape(str(block["x_axis_label"])[:80])}</text>')
    if block.get("y_axis_label"):
        shapes.append(f'<text x="10" y="150" text-anchor="middle" class="chart-axis-label" transform="rotate(-90 10 150)">{html.escape(str(block["y_axis_label"])[:80])}</text>')
    table_rows = "".join(f'<tr><th>{html.escape(label)}</th><td>{value:g}</td></tr>' for label, value in values[:100])
    table = f'<table class="chart-data-table"><caption>{html.escape(str(block.get("chart_title", chart_type + " chart")))}</caption><tbody>{table_rows}</tbody></table>' if table_rows else ""
    fragment = f'<figure class="template-chart" role="img" aria-label="{html.escape(str(block.get("alt", chart_type + " chart")), quote=True)}" style="{_offset_style(block)}"><svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{"".join(shapes)}</svg>{table}</figure>'
    return fragment, " ".join(label for label, _ in values)


_render_chart = _render_chart_robust


def _rich_text_style(style: Any) -> str:
    if not isinstance(style, dict):
        return ""
    values: list[str] = []
    family = style.get("font_family", style.get("fontFamily"))
    if isinstance(family, str) and re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", family):
        values.append(f"font-family:{html.escape(family, quote=True)}")
    size = style.get("font_size", style.get("fontSize"))
    if isinstance(size, (int, float)) and not isinstance(size, bool) and 8 <= size <= 96:
        values.append(f"font-size:{float(size):g}px")
    color = style.get("color")
    if isinstance(color, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        values.append(f"color:{color}")
    if style.get("bold") is True:
        values.append("font-weight:700")
    if style.get("italic") is True:
        values.append("font-style:italic")
    if style.get("underline") is True:
        values.append("text-decoration:underline")
    return ";".join(values)


def _rich_currency(value: Any, locale: str, currency: str | None) -> str:
    code = (currency or "").upper()
    base = format_value(value, locale, "number")
    symbols = {"USD": "$", "CNY": "¥", "EUR": "€", "GBP": "£", "JPY": "¥", "INR": "₹", "KRW": "₩"}
    return f"{symbols[code]}{base}" if code in symbols else f"{code + ' ' if code else ''}{base}"


def _render_rich_text(block: dict[str, Any], data: Any, locale: str, policy: str,
                      missing: list[str]) -> tuple[str, str]:
    paragraphs = block.get("paragraphs")
    if not isinstance(paragraphs, list) or len(paragraphs) > 100:
        raise ValueError("rich_text.paragraphs must be an array of at most 100 paragraphs")
    diagnostics: list[str] = []

    def render_runs(runs: Any, depth: int = 0) -> str:
        if depth > 4:
            raise ValueError("rich_text condition nesting exceeds 4 levels")
        if not isinstance(runs, list) or len(runs) > 200:
            raise ValueError("rich_text runs must be an array of at most 200 runs")
        output: list[str] = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            run_type = run.get("type", "text")
            style = _rich_text_style(run.get("style"))
            content = ""
            if run_type == "text":
                value = interpolate(str(run.get("text", "")), data, locale, policy,
                                    lambda path: missing.append(path) if path not in missing else None)
                content = TAB_MARK.join(html.escape(part) for part in value.split("\t"))
                diagnostics.append(value)
            elif run_type == "binding":
                path = run.get("path")
                if not isinstance(path, str) or not path.strip():
                    raise ValueError("rich_text binding.path is required")
                value, found = resolve_path(data, path)
                if not found or value is None:
                    if path not in missing:
                        missing.append(path)
                    if policy == "error":
                        raise ValueError(f"Missing rich_text field: {path}")
                    formatted = f"[[{path}]]" if policy == "placeholder" else ""
                else:
                    function = run.get("format", "text")
                    if function == "currency":
                        formatted = _rich_currency(value, locale, run.get("currency"))
                    else:
                        formatted = format_value(value, locale, function if function in {"text", "number", "date", "percent"} else "text")
                content = TAB_MARK.join(html.escape(part) for part in formatted.split("\t"))
                diagnostics.append(formatted)
            elif run_type == "condition":
                condition = run.get("condition")
                if not isinstance(condition, dict):
                    raise ValueError("rich_text condition is required")
                operator = condition.get("operator")
                key = {"equals": "equals", "not_equals": "not_equals", "in": "in", "truthy": "truthy", "greater_than": "greater_than", "greater_or_equal": "greater_or_equal", "less_than": "less_than", "less_or_equal": "less_or_equal"}.get(operator)
                if not key or not isinstance(condition.get("path"), str):
                    raise ValueError("rich_text condition has an unsupported operator or path")
                expression: dict[str, Any] = {"path": condition["path"], key: condition.get("value")}
                if key == "truthy":
                    expression[key] = True
                branch = condition.get("then", []) if condition_matches(expression, data, policy) else condition.get("else", [])
                content = render_runs(branch, depth + 1)
            else:
                raise ValueError(f"Unsupported rich_text run type: {run_type}")
            # Wrap each tab segment separately so splitting a paragraph at TAB_MARK keeps markup well formed.
            output.append(TAB_MARK.join(f'<span style="{style}">{part}</span>' for part in content.split(TAB_MARK))
                          if style else content)
        return "".join(output)

    body: list[str] = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        align = paragraph.get("align", "left")
        align = align if align in ALIGNMENTS else "left"
        settings = {**block, **paragraph}
        paragraph_style = [f"text-align:{align}"]
        largest = _largest_run_size(paragraph.get("runs", []))
        if largest:
            # Line height is a multiple of the paragraph's own font size; without this the paragraph inherits the
            # page default (16 px) and a 1.18 multiple of 13.28 px text spaced lines at 18.9 px (DD-428).
            paragraph_style.append(f"font-size:{largest:g}px")
        paragraph_style += _layout_style(settings, "paragraph")
        segments = render_runs(paragraph.get("runs", [])).split(TAB_MARK)
        stops = tab_stops(settings)
        if stops and len(segments) > 1:
            indent = settings.get("first_line_indent", 0)
            indent = float(indent) if isinstance(indent, (int, float)) and not isinstance(indent, bool) and -240 <= indent <= 240 else 0.0
            inner = tabbed_html(segments, stops, indent)
        else:
            inner = "\t".join(segments)
        body.append(f'<p class="rich-text-paragraph" style="{";".join(paragraph_style)}">{inner}</p>')
    layout = ";".join(_layout_style(block, "block"))
    fragment = f'<section class="rich-text-block" style="{_offset_style(block)}{layout}">{"".join(body)}</section>'
    return fragment, " ".join(diagnostics)


def _largest_run_size(runs: Any, depth: int = 0) -> float | None:
    """Largest valid explicit run font size in a rich-text paragraph, including condition branches."""
    sizes: list[float] = []
    for run in runs if isinstance(runs, list) and depth <= 4 else []:
        if not isinstance(run, dict):
            continue
        style = run.get("style") if isinstance(run.get("style"), dict) else {}
        size = style.get("font_size", style.get("fontSize"))
        if isinstance(size, (int, float)) and not isinstance(size, bool) and 8 <= size <= 96:
            sizes.append(round(float(size), 2))
        condition = run.get("condition") if isinstance(run.get("condition"), dict) else {}
        for branch in (condition.get("then"), condition.get("else")):
            nested = _largest_run_size(branch, depth + 1)
            if nested:
                sizes.append(nested)
    return max(sizes) if sizes else None


SHAPES = {"line", "rectangle"}
STROKE_STYLES = {"solid", "dashed", "dotted"}


def _render_shape(block: dict[str, Any]) -> str:
    """Decorative line or rectangle (DD-433), placed absolutely in mm or in the flow.

    Absolute shapes are positioned from the page content area (the page-owned surface). ``layer: behind``
    paints under text, for shaded bars behind headings. Shapes carry no text and are hidden from
    assistive technology.
    """
    shape = block.get("shape")
    if shape not in SHAPES:
        raise ValueError("shape.shape must be line or rectangle")
    color = block.get("stroke_color") if isinstance(block.get("stroke_color"), str) and _HEX_COLOR.fullmatch(
        block["stroke_color"]) else "#000000"
    stroke_width = _bounded_number(block.get("stroke_width", 1), 0, 10)
    stroke_width = 1.0 if stroke_width is None else stroke_width
    stroke_style = block.get("stroke_style") if block.get("stroke_style") in STROKE_STYLES else "solid"
    stroke = f"{stroke_width:g}px {stroke_style} {color}"
    width = _bounded_number(block.get("width_mm"), 0.1, 500)
    height = _bounded_number(block.get("height_mm"), 0.1, 500)
    style: list[str] = ["box-sizing:border-box", "display:block"]
    if shape == "line":
        if block.get("orientation") == "vertical":
            style += [f"height:{(height or 10):g}mm", "width:0", f"border-left:{stroke}"]
        else:
            style += [f"width:{width:g}mm" if width else "width:100%", "height:0", f"border-top:{stroke}"]
    else:
        style += [f"width:{width:g}mm" if width else "width:100%", f"height:{(height or 10):g}mm"]
        if stroke_width > 0:
            style.append(f"border:{stroke}")
        fill = block.get("fill_color")
        if isinstance(fill, str) and _HEX_COLOR.fullmatch(fill):
            style.append(f"background:{fill}")
    if block.get("position_mode") == "absolute":
        x = _bounded_number(block.get("position_x", 0), 0, 500) or 0
        y = _bounded_number(block.get("position_y", 0), 0, 500) or 0
        style += ["position:absolute", f"left:{x:g}mm", f"top:{y:g}mm"]
        if block.get("layer") == "behind":
            style.append("z-index:-1")
    else:
        for key, css in (("paragraph_spacing_before", "margin-top"), ("paragraph_spacing_after", "margin-bottom")):
            value = _bounded_number(block.get(key), 0, 240)
            style.append(f"{css}:{(value or 0):g}px")
    return f'<div class="template-shape template-shape-{shape}" aria-hidden="true" style="{";".join(style)}"></div>'


COLUMN_MARKERS = {"columns", "column_break", "columns_end"}
MAX_COLUMNS = 4


def _column_settings(block: dict[str, Any]) -> dict[str, Any]:
    count = block.get("count", 2)
    count = int(count) if isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= MAX_COLUMNS else 2
    gap = _bounded_number(block.get("gap_mm", 6), 0, 50)
    widths = block.get("widths")
    if not (isinstance(widths, list) and len(widths) == count
            and all(_bounded_number(w, 5, 100) is not None for w in widths)):
        widths = None
    color = block.get("rule_color") if isinstance(block.get("rule_color"), str) and _HEX_COLOR.fullmatch(
        block["rule_color"]) else None
    rule_width = _bounded_number(block.get("rule_width", 1), 0, 4)
    spacing = [f"{css}:{value:g}px" for key, css in (("paragraph_spacing_before", "margin-top"),
                                                     ("paragraph_spacing_after", "margin-bottom"))
               if (value := _bounded_number(block.get(key), 0, 240)) is not None]
    return {"count": count, "gap": 6.0 if gap is None else gap, "widths": widths, "rule": color,
            "rule_width": 1.0 if rule_width is None else rule_width, "spacing": spacing}


def _columns_container(settings: dict[str, Any], columns: list[list[str]]) -> str:
    """A column section (DD-435): explicit columns when column breaks were used, otherwise flowing columns."""
    gap, spacing = settings["gap"], settings["spacing"]
    if len(columns) > 1:
        count = max(settings["count"], len(columns))
        columns = (columns + [[] for _ in range(count)])[:count]
        widths = settings["widths"] if settings["widths"] and len(settings["widths"]) == count else None
        template = " ".join(f"{float(w):g}%" for w in widths) if widths else f"repeat({count},minmax(0,1fr))"
        rule = settings["rule"]
        column_gap = gap / 2 if rule else gap
        style = ";".join(["display:grid", f"grid-template-columns:{template}", f"column-gap:{column_gap:g}mm",
                          "align-items:start", *spacing])
        cells = []
        for index, column in enumerate(columns):
            cell_style = "min-width:0" + (f";border-left:{settings['rule_width']:g}px solid {rule};padding-left:{gap / 2:g}mm"
                                          if rule and index else "")
            cells.append(f'<div class="template-column" style="{cell_style}">{"".join(column)}</div>')
        return f'<div class="template-columns" style="{style}">{"".join(cells)}</div>'
    style = [f"column-count:{settings['count']}", f"column-gap:{gap:g}mm", "column-fill:balance", *spacing]
    if settings["rule"]:
        style.append(f"column-rule:{settings['rule_width']:g}px solid {settings['rule']}")
    return f'<div class="template-columns template-columns-flow" style="{";".join(style)}">{"".join(columns[0])}</div>'


def group_columns(entries: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Group fragments between ``columns`` and ``columns_end`` markers into column containers (DD-435).

    ``column_break`` starts the next column. A new ``columns`` marker, or the end of the page or document,
    closes an open section. Markers outside a section are ignored.
    """
    output: list[str] = []
    settings: dict[str, Any] | None = None
    columns: list[list[str]] = []
    for fragment, block in entries:
        marker = block.get("__marker")
        if marker == "columns":
            if settings is not None:
                output.append(_columns_container(settings, columns))
            settings, columns = _column_settings(block), [[]]
        elif marker == "column_break":
            if settings is not None and len(columns) < MAX_COLUMNS:
                columns.append([])
        elif marker == "columns_end":
            if settings is not None:
                output.append(_columns_container(settings, columns))
            settings, columns = None, []
        elif settings is not None:
            columns[-1].append(fragment)
        else:
            output.append(fragment)
    if settings is not None:
        output.append(_columns_container(settings, columns))
    return output


def _render_toc(blocks: list[dict[str, Any]]) -> str:
    entries = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or not block.get("toc_label"):
            continue
        label = str(block["toc_label"])[:200]
        anchor = str(block.get("anchor_id", f"section-{index}"))
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", anchor):
            anchor = f"section-{index}"
        level = min(6, max(1, int(block.get("toc_level", 1)))) if isinstance(block.get("toc_level", 1), int) else 1
        entries.append(f'<li data-level="{level}"><a href="#{html.escape(anchor, quote=True)}">{html.escape(label)}</a></li>')
    return '<nav class="template-toc" aria-label="Table of contents"><ol>' + "".join(entries) + "</ol></nav>"


def render_definition(definition: dict[str, Any], data: dict[str, Any] | None = None,
                      locale: str | None = None, missing_policy: str | None = None) -> dict[str, Any]:
    data = data or definition.get("sample_data", {})
    locale = locale or definition.get("locale", "en")
    policy = missing_policy or definition.get("missing_policy", "blank")
    if policy not in {"error", "blank", "placeholder"}:
        raise ValueError("missing_policy must be error, blank, or placeholder")
    validation_errors = validate_data(definition["data_schema"], data) if definition.get("data_schema") else []
    if validation_errors:
        raise ValueError({"message": "Render data failed schema validation", "errors": validation_errors})
    blocks = definition.get("blocks", [])
    missing: list[str] = []
    missing_translations: list[str] = []
    translations = definition.get("translations", {})
    rendered = []
    seen_scripts: set[str] = set()
    diagnostic_texts: list[str] = []
    rendered_blocks: list[tuple[str, dict[str, Any]]] = []
    last_page_number = 1
    for block in blocks:
        if not isinstance(block, dict):
            continue
        requested_page = block.get("page_number")
        page_number = int(requested_page) if isinstance(requested_page, (int, float)) and not isinstance(requested_page, bool) else None
        effective_block = {**block, "break_before": True} if page_number and page_number > last_page_number else block
        if page_number:
            last_page_number = max(last_page_number, min(1000, page_number))
        block = effective_block
        if block.get("type", "text") == "text" and not block.get("richText") and not block.get("rich_text"):
            rendered_blocks.append((interpolate(translated_text(block, translations, locale, missing_translations), data, locale, policy,
                                                 lambda path: missing.append(path) if path not in missing else None), block))
        elif block.get("type") == "rich_text" or isinstance(block.get("richText"), dict) or isinstance(block.get("rich_text"), dict):
            rich_block = block.get("rich_text") if isinstance(block.get("rich_text"), dict) else block.get("richText") if isinstance(block.get("richText"), dict) else block
            fragment, rich_text = _render_rich_text({**rich_block, **({"offset_x": block.get("offset_x")} if "offset_x" in block else {})}, data, locale, policy, missing)
            rendered_blocks.append((fragment, {**block, "__html": True}))
            seen_scripts.update(scripts_in(rich_text)); diagnostic_texts.append(rich_text)
        elif block.get("type") == "table":
            fragment, table_text = _render_table(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {**block, "__html": True}))
            for value in table_text:
                seen_scripts.update(scripts_in(value))
                diagnostic_texts.append(value)
        elif block.get("type") == "image":
            fragment, alt = _render_image(block, data, locale, policy, missing, definition)
            rendered_blocks.append((fragment, {**block, "__html": True}))
            seen_scripts.update(scripts_in(alt))
            diagnostic_texts.append(alt)
        elif block.get("type") == "code":
            fragment, label = _render_code(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {**block, "__html": True}))
            seen_scripts.update(scripts_in(label))
            diagnostic_texts.append(label)
        elif block.get("type") == "chart":
            fragment, labels = _render_chart(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {**block, "__html": True}))
            seen_scripts.update(scripts_in(labels)); diagnostic_texts.append(labels)
        elif block.get("type") == "toc":
            rendered_blocks.append((_render_toc(blocks), {**block, "__html": True}))
        elif block.get("type") == "shape":
            rendered_blocks.append((_render_shape(block), {**block, "__html": True}))
        elif block.get("type") in COLUMN_MARKERS:
            rendered_blocks.append(("", {**block, "__html": True, "__marker": block["type"]}))
        else:
            rendered_blocks.extend((text, {}) for text in render_blocks([block], data, locale, policy, missing,
                                                                         translations=translations,
                                                                         missing_translations=missing_translations))
    def rendered_fragment(text: str, block: dict[str, Any]) -> str:
        if block.get("__html"):
            return text
        diagnostic_texts.append(text)
        seen_scripts.update(scripts_in(text))
        style = []
        if block:
            color = str(block.get("color", ""))
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                style.append(f"color:{color}")
            size = block.get("font_size")
            if isinstance(size, (int, float)) and not isinstance(size, bool) and 8 <= size <= 96:
                style.append(f"font-size:{round(float(size), 2):g}px")  # decimal px, DD-424
            if block.get("bold") is True:
                style.append("font-weight:700")
            if block.get("italic") is True:
                style.append("font-style:italic")
            if block.get("align") in ALIGNMENTS:
                style.append(f"text-align:{block['align']}")
            if block.get("break_before") is True:
                style.append("break-before:page")
            if block.get("keep_together") is True:
                style.append("break-inside:avoid")
            style.extend(_layout_style(block))
            offset = _offset_style(block)
            if offset:
                style.append(offset[:-1])
            family = str(block.get("font_family", ""))
            if re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", family):
                style.append(f"font-family:{html.escape(family, quote=True)}")
        attribute = f' style="{";".join(style)}"' if style else ""
        anchor = str(block.get("anchor_id", "")) if block else ""
        anchor_attribute = f' id="{html.escape(anchor, quote=True)}"' if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", anchor) else ""
        marker = f'<span class="docplatform-anchor-marker" aria-hidden="true">__DOCPLATFORM_ANCHOR_{anchor}__</span>' if anchor_attribute else ""
        body = html.escape(text)
        stops = tab_stops(block) if block else []
        if stops and "\t" in text:
            indent = block.get("first_line_indent", 0)
            indent = float(indent) if isinstance(indent, (int, float)) and not isinstance(indent, bool) and -240 <= indent <= 240 else 0.0
            body = tabbed_html([html.escape(part) for part in text.split("\t")], stops, indent)
        return f'<p dir="auto"{anchor_attribute}{attribute}>{marker}{body}</p>'

    page_groups: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    unpaged: list[tuple[str, dict[str, Any]]] = []
    fragments: list[tuple[str, dict[str, Any]]] = []
    for text, block in rendered_blocks:
        fragment = rendered_fragment(text, block)
        page_number = block.get("page_number")
        normalized_page = int(page_number) if isinstance(page_number, (int, float)) and not isinstance(page_number, bool) else None
        fragments.append((fragment, block))
        if normalized_page is not None:
            page_groups.setdefault(normalized_page, []).append((fragment, block))
        else:
            unpaged.append((fragment, block))
    if page_groups and not unpaged:
        page_numbers = sorted(page_groups)
        for index, page_number in enumerate(page_numbers):
            page_break = " page-break-before" if index else ""
            rendered.append(f'<section class="page-surface{page_break}" data-page-number="{page_number}">{"".join(group_columns(page_groups[page_number]))}</section>')
    else:
        rendered.extend(group_columns(fragments))
    page = _page_settings(definition.get("page"))
    metadata = _document_metadata(definition)
    header_block = {"text": page["header"], "translation_key": page.get("header_translation_key")}
    footer_block = {"text": page["footer"], "translation_key": page.get("footer_translation_key")}
    header = interpolate(translated_text(header_block, translations, locale, missing_translations), data, locale, policy,
                         lambda path: missing.append(path) if path not in missing else None) if page["header"] else ""
    footer = interpolate(translated_text(footer_block, translations, locale, missing_translations), data, locale, policy,
                         lambda path: missing.append(path) if path not in missing else None) if page["footer"] else ""
    # Zones: the legacy header/footer text sits in its aligned zone; a zone-specific text takes precedence.
    zones: dict[str, dict[str, str]] = {"header": {}, "footer": {}}
    for band, legacy in (("header", header), ("footer", footer)):
        if legacy:
            zones[band][page[f"{band}_align"]] = legacy
        for align, raw in page["zones"][band].items():
            zones[band][align] = interpolate(raw, data, locale, policy,
                                             lambda path: missing.append(path) if path not in missing else None)
    header = "   ".join(zones["header"][a] for a in BOX_ALIGNMENTS if zones["header"].get(a))
    footer = "   ".join(zones["footer"][a] for a in BOX_ALIGNMENTS if zones["footer"].get(a))
    seen_scripts.update(scripts_in(header))
    seen_scripts.update(scripts_in(footer))
    diagnostic_texts.extend((header, footer))
    missing_glyphs = _diagnostic_missing_glyphs(diagnostic_texts)
    stacks = [SCRIPT_STACKS[script] for script in sorted(seen_scripts)]
    font_report = [{"script": script, "requested_stack": SCRIPT_STACKS[script],
                    "embedded_fonts": [],
                    "missing_glyphs": missing_glyphs if script == "latin" else [],
                    "status": "warning" if script == "latin" and missing_glyphs else "candidate"}
                   for script in sorted(seen_scripts)]
    css_stack = ", ".join(stacks) if stacks else SCRIPT_STACKS["latin"]
    body = "".join(rendered)
    direction = _locale_direction(locale)
    theme = definition.get("theme") if isinstance(definition.get("theme"), dict) else {}
    theme_css = ""
    for key, value in theme.items():
        if isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,40}", key) and isinstance(value, str) and len(value) <= 120:
            theme_css += f"--theme-{key}:{html.escape(value, quote=True)};"
    theme_font = str(theme.get("font_family", ""))
    furniture_font = css_stack
    if re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", theme_font):
        theme_css += f"--theme-font-family:{html.escape(theme_font, quote=True)};"
        furniture_font = theme_font  # margin boxes use the same font as the body
    try:
        theme_spacing = float(theme.get("spacing", 1.45))
    except (TypeError, ValueError):
        theme_spacing = 1.45
    if not 0.8 <= theme_spacing <= 2.0:
        theme_spacing = 1.45
    theme_css += f"--theme-spacing:{theme_spacing:g};"
    background = page.get("background") if isinstance(page.get("background"), str) else ""
    background_css = f"background-image:url('{html.escape(background, quote=True)}');background-size:cover;" if background.startswith("data:image/") else ""
    page_margins = page["margins"]
    margin_values = [page_margins[name] for name in ("top", "right", "bottom", "left")]
    margin_css = f"{margin_values[0]}mm" if len(set(margin_values)) == 1 else " ".join(f"{value}mm" for value in margin_values)
    page_dimensions_mm = {"A3": (297, 420), "A4": (210, 297), "A5": (148, 210), "Letter": (216, 279)}
    page_width_mm, page_height_mm = page_dimensions_mm[page["size"]]
    if page["orientation"] == "landscape":
        page_width_mm, page_height_mm = page_height_mm, page_width_mm
    # A page-owned surface fills the @page content area, i.e. the page height minus the top and bottom
    # margins (DD-422). Sizing it to the full page height made every surface overflow onto an extra page
    # whenever margins were non-zero.
    content_height_mm = max(1.0, page_height_mm - float(page_margins["top"]) - float(page_margins["bottom"]))
    page_surface_css = (f"height:{content_height_mm:g}mm;overflow:hidden;box-sizing:border-box;"
                        if page_groups and not unpaged else "")
    artifact = ("<!doctype html><html lang=\"" + html.escape(locale) + "\" dir=\"" + direction + "\"><head>"
        "<meta charset=\"utf-8\"><title>" + html.escape(metadata["title"]) + "</title><meta name=\"author\" content=\"" + html.escape(metadata["author"], quote=True) + "\"><style>:root{" + theme_css + "}@page{size:" + page["size"] + " " + page["orientation"] + ";margin:" + margin_css + ";" + margin_boxes_css(page, zones, furniture_font) + "}body{font-family:var(--theme-font-family," + css_stack + ");direction:auto;margin:0;" + background_css + "}.page-surface{position:relative;z-index:0;" + page_surface_css + "break-inside:avoid;page-break-inside:avoid;break-after:page;page-break-after:always;}.page-surface:last-of-type{break-after:auto;page-break-after:auto;}"
        ".document-header,.document-footer{font-size:" + f"{page['header_footer_font_size']:g}" + "px;color:#52645a;} .document-header{text-align:" + page["header_align"] + ";margin-bottom:8px;} .document-footer{text-align:" + page["footer_align"] + ";margin-top:8px;} @media print{.document-header,.document-footer{display:none!important;}}.docplatform-anchor-marker{font-size:1px;color:transparent;}.tab-box{display:inline-flex;align-items:baseline;white-space:pre;vertical-align:baseline;box-sizing:border-box;text-indent:0;}.tab-fill{flex:1 1 auto;min-width:0;align-self:baseline;margin:0 0.15em;}.leader-dot{border-bottom:1px dotted currentColor;}.leader-underscore{border-bottom:1px solid currentColor;}.leader-hyphen{border-bottom:1px dashed currentColor;}"
        "p{white-space:pre-wrap;line-height:var(--theme-spacing,1.45);break-inside:auto;page-break-inside:auto;orphans:3;widows:3;unicode-bidi:plaintext;} .document-header,.document-footer,table.template-table th,table.template-table td{unicode-bidi:plaintext;} .page-break-before{break-before:page;page-break-before:always;} .keep-together{break-inside:avoid;page-break-inside:avoid;}figure.template-image,figure.template-code,figure.template-chart{margin:0;display:block;break-inside:avoid;page-break-inside:avoid;}figure.template-image img,figure.template-code svg,figure.template-chart svg{max-width:100%;height:auto;}figure.template-image.image-align-left img{display:block!important;margin-left:0!important;margin-right:auto!important;}figure.template-image.image-align-center img{display:block!important;margin-left:auto!important;margin-right:auto!important;}figure.template-image.image-align-right img{display:block!important;margin-left:auto!important;margin-right:0!important;}figure.template-chart rect{fill:var(--theme-accent,#2f6f60);}figure.template-chart .chart-grid{stroke:#dce2d6;stroke-width:1;}figure.template-chart .chart-donut-hole{fill:#fff;}figure.template-chart text{fill:#52645a;font:11px sans-serif;}figure.template-chart .chart-title{font-weight:700;font-size:14px;fill:#203d37;}nav.template-toc{break-inside:avoid;page-break-inside:avoid;}nav.template-toc li{margin:4px 0;}table.template-table{width:100%;border-collapse:collapse;break-inside:auto;page-break-inside:auto;}table.template-table th,table.template-table td{border:1px solid #cfd9cc;padding:6px;text-align:left;}table.template-table thead{display:table-header-group;}table.template-table tr{break-inside:avoid;page-break-inside:avoid;}table.template-table tbody tr{orphans:3;widows:3;}</style></head>"
        "<style>.rich-text-block{break-inside:avoid;page-break-inside:avoid;}.rich-text-block .rich-text-paragraph{margin:0;white-space:pre-wrap;line-height:var(--theme-spacing,1.45);unicode-bidi:plaintext;}</style><body>" + (f'<header dir="auto" class="document-header">{html.escape(header)}</header>' if header else ""))
    artifact += body
    if footer or page["show_page_numbers"]:
        # Screen preview only; printed output uses the @page margin boxes above.
        artifact += f'<footer dir="auto" class="document-footer">{html.escape(footer)}'
        if page["show_page_numbers"]:
            artifact += f' <span class="page-number">{html.escape(page_number_preview(page["page_number_format"]))}</span>'
        artifact += "</footer>"
    artifact += "</body></html>"
    return {"artifact": artifact, "content_type": "text/html", "locale": locale,
            "metadata": {**metadata, "language": locale},
            "scripts": sorted(seen_scripts), "font_stacks": stacks, "missing_fields": missing,
            "missing_translations": missing_translations,
            "missing_glyphs": missing_glyphs,
            "font_report": font_report,
            "engine": "deterministic-html-0.1", "status": "candidate"}


def compare_candidates(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for fixture in fixtures:
        rendered = render_definition(fixture, fixture.get("sample_data", {}))
        results.append({"name": fixture.get("name", "fixture"), "engine": rendered["engine"],
                        "scripts": rendered["scripts"], "missing_glyphs": rendered["missing_glyphs"]})
    return {"status": "pending-native-review", "candidates": ["deterministic-html-0.1"],
            "results": results, "native_reader_scores": None}
