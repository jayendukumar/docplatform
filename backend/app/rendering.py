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


def _render_table(block: dict[str, Any], data: Any, locale: str, policy: str,
                  missing: list[str]) -> tuple[str, list[str]]:
    items_path = block.get("items")
    columns = block.get("columns")
    if not isinstance(items_path, str) or not items_path:
        raise ValueError("table.items is required")
    if not isinstance(columns, list) or not columns or len(columns) > 50:
        raise ValueError("table.columns must contain between 1 and 50 columns")
    items, found = resolve_path(data, items_path)
    if not found or items is None:
        items = []
    if not isinstance(items, list):
        raise ValueError(f"Table source is not an array: {items_path}")  # noqa: TRY004
    if len(items) > MAX_LOOP_ITEMS:
        raise ValueError(f"Table exceeds {MAX_LOOP_ITEMS} rows: {items_path}")
    normalized: list[dict[str, str]] = []
    for column in columns:
        if not isinstance(column, dict) or not isinstance(column.get("header"), str) or not isinstance(column.get("path"), str):
            raise ValueError("table columns require header and path")  # noqa: TRY004
        if column.get("format") not in {None, "text", "number", "currency", "date", "percent"}:
            raise ValueError("unsupported table column format")
        normalized.append({"header": column["header"], "path": column["path"], "format": column.get("format") or "text"})
    body_rows: list[list[str]] = []
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
    headers = "".join(f"<th scope=\"col\" dir=\"auto\">{html.escape(column['header'])}</th>" for column in normalized)
    rows = "".join("<tr>" + "".join(f"<td dir=\"auto\">{html.escape(value)}</td>" for value in row) + "</tr>" for row in body_rows)
    flow = _flow_classes(block)
    fragment = f"<table class=\"template-table{(' ' + flow) if flow else ''}\"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"
    return fragment, [value for row in body_rows for value in row] + [column["header"] for column in normalized]


def _page_settings(page: Any) -> dict[str, Any]:
    if not isinstance(page, dict):
        page = {}
    size = page.get("size", "A4")
    orientation = page.get("orientation", "portrait")
    if size not in {"A3", "A4", "A5", "Letter"}:
        raise ValueError("page.size must be A3, A4, A5, or Letter")
    if orientation not in {"portrait", "landscape"}:
        raise ValueError("page.orientation must be portrait or landscape")
    margin = page.get("margin_mm", 20)
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not 0 <= margin <= 100:
        raise ValueError("page.margin_mm must be between 0 and 100")
    return {"size": size, "orientation": orientation, "margin_mm": margin,
            "header": str(page.get("header", ""))[:500], "footer": str(page.get("footer", ""))[:500],
            "show_page_numbers": page.get("show_page_numbers", False) is True,
            "background": page.get("background", "") if isinstance(page.get("background", ""), str) else ""}


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
    return f'<figure class="{classes}" style="text-align:{align}"><img src="{html.escape(source, quote=True)}" alt="{html.escape(alt, quote=True)}" style="display:block;{horizontal_margin}{image_size}" /></figure>', alt


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
    width, height = 600, 260
    shapes = []
    for index, (label, value) in enumerate(values):
        x = 20 + index * max(40, (width - 40) / max(1, len(values)))
        bar_height = max(1, 190 * value / maximum)
        if chart_type == "bar":
            shapes.append(f'<rect x="{x:.1f}" y="{220 - bar_height:.1f}" width="28" height="{bar_height:.1f}" aria-label="{html.escape(label)} {value:g}" />')
    if chart_type == "line" and values:
        points = " ".join(f"{20 + index * max(40, (width - 40) / max(1, len(values) - 1)):.1f},{220 - max(1, 190 * value / maximum):.1f}" for index, (_, value) in enumerate(values))
        shapes.append(f'<polyline points="{points}" fill="none" stroke="currentColor" stroke-width="3" aria-label="{html.escape(chart_type)} chart" />')
        for index, (label, value) in enumerate(values):
            x = 20 + index * max(40, (width - 40) / max(1, len(values) - 1))
            y = 220 - max(1, 190 * value / maximum)
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
    fragment = f'<figure class="template-chart" role="img" aria-label="{html.escape(str(block.get("alt", chart_type + " chart")), quote=True)}"><svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{"".join(shapes)}</svg></figure>'
    return fragment, " ".join(label for label, _ in values)


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
    for block in blocks:
        if block.get("type", "text") == "text":
            rendered_blocks.append((interpolate(translated_text(block, translations, locale, missing_translations), data, locale, policy,
                                                 lambda path: missing.append(path) if path not in missing else None), block))
        elif block.get("type") == "table":
            fragment, table_text = _render_table(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {"__html": True}))
            for value in table_text:
                seen_scripts.update(scripts_in(value))
                diagnostic_texts.append(value)
        elif block.get("type") == "image":
            fragment, alt = _render_image(block, data, locale, policy, missing, definition)
            rendered_blocks.append((fragment, {"__html": True}))
            seen_scripts.update(scripts_in(alt))
            diagnostic_texts.append(alt)
        elif block.get("type") == "code":
            fragment, label = _render_code(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {"__html": True}))
            seen_scripts.update(scripts_in(label))
            diagnostic_texts.append(label)
        elif block.get("type") == "chart":
            fragment, labels = _render_chart(block, data, locale, policy, missing)
            rendered_blocks.append((fragment, {"__html": True}))
            seen_scripts.update(scripts_in(labels)); diagnostic_texts.append(labels)
        elif block.get("type") == "toc":
            rendered_blocks.append((_render_toc(blocks), {"__html": True}))
        else:
            rendered_blocks.extend((text, {}) for text in render_blocks([block], data, locale, policy, missing,
                                                                         translations=translations,
                                                                         missing_translations=missing_translations))
    for text, block in rendered_blocks:
        if block.get("__html"):
            rendered.append(text)
            continue
        diagnostic_texts.append(text)
        seen_scripts.update(scripts_in(text))
        style = []
        if block:
            color = str(block.get("color", ""))
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                style.append(f"color:{color}")
            size = block.get("font_size")
            if isinstance(size, int) and 8 <= size <= 96:
                style.append(f"font-size:{size}px")
            if block.get("bold") is True:
                style.append("font-weight:700")
            if block.get("italic") is True:
                style.append("font-style:italic")
            if block.get("align") in {"left", "center", "right"}:
                style.append(f"text-align:{block['align']}")
            if block.get("break_before") is True:
                style.append("break-before:page")
            if block.get("keep_together") is True:
                style.append("break-inside:avoid")
            family = str(block.get("font_family", ""))
            if re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", family):
                style.append(f"font-family:{html.escape(family, quote=True)}")
        attribute = f' style="{";".join(style)}"' if style else ""
        anchor = str(block.get("anchor_id", "")) if block else ""
        anchor_attribute = f' id="{html.escape(anchor, quote=True)}"' if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", anchor) else ""
        marker = f'<span class="docplatform-anchor-marker" aria-hidden="true">__DOCPLATFORM_ANCHOR_{anchor}__</span>' if anchor_attribute else ""
        rendered.append(f'<p dir="auto"{anchor_attribute}{attribute}>{marker}{html.escape(text)}</p>')
    page = _page_settings(definition.get("page"))
    metadata = _document_metadata(definition)
    header_block = {"text": page["header"], "translation_key": page.get("header_translation_key")}
    footer_block = {"text": page["footer"], "translation_key": page.get("footer_translation_key")}
    header = interpolate(translated_text(header_block, translations, locale, missing_translations), data, locale, policy,
                         lambda path: missing.append(path) if path not in missing else None) if page["header"] else ""
    footer = interpolate(translated_text(footer_block, translations, locale, missing_translations), data, locale, policy,
                         lambda path: missing.append(path) if path not in missing else None) if page["footer"] else ""
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
    if re.fullmatch(r"[A-Za-z0-9 ,_-]{1,80}", theme_font):
        theme_css += f"--theme-font-family:{html.escape(theme_font, quote=True)};"
    try:
        theme_spacing = float(theme.get("spacing", 1.45))
    except (TypeError, ValueError):
        theme_spacing = 1.45
    if not 0.8 <= theme_spacing <= 2.0:
        theme_spacing = 1.45
    theme_css += f"--theme-spacing:{theme_spacing:g};"
    background = page.get("background") if isinstance(page.get("background"), str) else ""
    background_css = f"background-image:url('{html.escape(background, quote=True)}');background-size:cover;" if background.startswith("data:image/") else ""
    artifact = ("<!doctype html><html lang=\"" + html.escape(locale) + "\" dir=\"" + direction + "\"><head>"
        "<meta charset=\"utf-8\"><title>" + html.escape(metadata["title"]) + "</title><meta name=\"author\" content=\"" + html.escape(metadata["author"], quote=True) + "\"><style>:root{" + theme_css + "}@page{size:" + page["size"] + " " + page["orientation"] + ";margin:" + str(page["margin_mm"]) + "mm;}body{font-family:var(--theme-font-family," + css_stack + ");direction:auto;margin:0;" + background_css + "}"
        ".document-header{position:fixed;top:-" + str(page["margin_mm"]) + "mm;left:0;right:0;} .document-footer{position:fixed;bottom:-" + str(page["margin_mm"]) + "mm;left:0;right:0;} .page-number::after{content:counter(page);}.docplatform-anchor-marker{font-size:1px;color:transparent;}"
        "p{white-space:pre-wrap;line-height:var(--theme-spacing,1.45);break-inside:avoid;page-break-inside:avoid;orphans:3;widows:3;unicode-bidi:plaintext;} .document-header,.document-footer,table.template-table th,table.template-table td{unicode-bidi:plaintext;} .page-break-before{break-before:page;page-break-before:always;} .keep-together{break-inside:avoid;page-break-inside:avoid;}figure.template-image,figure.template-code,figure.template-chart{margin:0;display:block;break-inside:avoid;page-break-inside:avoid;}figure.template-image img,figure.template-code svg,figure.template-chart svg{max-width:100%;height:auto;}figure.template-image.image-align-left img{display:block!important;margin-left:0!important;margin-right:auto!important;}figure.template-image.image-align-center img{display:block!important;margin-left:auto!important;margin-right:auto!important;}figure.template-image.image-align-right img{display:block!important;margin-left:auto!important;margin-right:0!important;}figure.template-chart rect{fill:var(--theme-accent,#2f6f60);}nav.template-toc{break-inside:avoid;page-break-inside:avoid;}nav.template-toc li{margin:4px 0;}table.template-table{width:100%;border-collapse:collapse;break-inside:auto;page-break-inside:auto;}table.template-table th,table.template-table td{border:1px solid #cfd9cc;padding:6px;text-align:left;}table.template-table thead{display:table-header-group;}table.template-table tr{break-inside:avoid;page-break-inside:avoid;}table.template-table tbody tr{orphans:3;widows:3;}</style></head>"
        "<body>" + (f'<header dir="auto" class="document-header">{html.escape(header)}</header>' if header else ""))
    artifact += body
    if footer or page["show_page_numbers"]:
        artifact += f'<footer dir="auto" class="document-footer">{html.escape(footer)}'
        if page["show_page_numbers"]:
            artifact += ' <span class="page-number">Page </span>'
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
