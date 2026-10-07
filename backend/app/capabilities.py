"""Machine-readable editor capability manifest (E16-05, DD-418).

The manifest records what the declarative renderer actually applies, with
bounds taken from ``app.rendering``, and whether the editor exposes each
property. ``ui`` values:

* ``control`` - a dedicated editor control references the property;
* ``json``    - reachable only by editing raw JSON in the editor;
* ``none``    - accepted by the renderer but not reachable from the editor.

UI exposure is declared from inspection of ``frontend/src``, in particular the
draft serializer ``saveEditorDraft`` in ``main.tsx`` (including its second
pass that restores layout and page fields for every block kind): a property the
serializer drops on save is ``none`` even when a control exists. The regression
test checks that every ``control`` key is referenced there; it does not yet
prove a visible control exists (a Playwright check is a later E16-05 step).
``limitations`` are known renderer behaviours a reconstruction must respect.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

MANIFEST_VERSION = "editor-capabilities-v1"


def _p(kind: str, ui: str, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "ui": ui, **extra}


_TYPOGRAPHY = {
    "font_family": _p("string", "control", pattern="[A-Za-z0-9 ,_-]{1,80}"),
    "font_size": _p("number", "control", range=[8, 96], unit="px", precision=2),
    "bold": _p("boolean", "control"),
    "italic": _p("boolean", "control"),
    "color": _p("color", "control", pattern="#RRGGBB"),
    "align": _p("enum", "control", values=["left", "center", "right", "justify"]),
}

_FLOW = {
    "break_before": _p("boolean", "control"),
    "keep_together": _p("boolean", "control"),
    "page_number": _p("integer", "control", range=[1, 1000]),
}

_PARAGRAPH_LAYOUT = {
    "line_height": _p("number", "control", range=[0.8, 3], unit="multiple"),
    "paragraph_spacing_before": _p("number", "control", range=[0, 240], unit="px"),
    "paragraph_spacing_after": _p("number", "control", range=[0, 240], unit="px"),
    "first_line_indent": _p("number", "control", range=[-240, 240], unit="px"),
    "left_indent": _p("number", "control", range=[-240, 240], unit="px"),
    "right_indent": _p("number", "control", range=[-240, 240], unit="px"),
    "tab_stops": _p("array", "control", item="tab-stop", max_items=16, range=[0, 2000], unit="px",
                    item_properties={"position": "number 0-2000 px from the left indent (0 = hanging-indent stop)",
                                     "align": ["left", "right"], "leader": ["none", "dot", "underscore", "hyphen"]},
                    notes="A bare number is a left stop. Tabs beyond the last stop stay literal tab characters."),
    "keep_with_next": _p("boolean", "control"),
    "break_after": _p("boolean", "control"),
    "position_mode": _p("enum", "control", values=["flow", "absolute"]),
    "position_x": _p("number", "control", range=[0, 320], unit="mm", notes="px unit range is 0-1200."),
    "position_y": _p("number", "control", range=[0, 450], unit="mm", notes="px unit range is 0-2000."),
    "position_unit": _p("enum", "control", values=["mm", "px"]),
}

_NOT_PERSISTED = "Renderer accepts it, but the editor draft serializer drops it on save."

_OFFSET = {
    "offset_x": _p("number", "control", range=[-160, 160], unit="px"),
    "offset_y": _p("number", "control", range=[-160, 160], unit="px"),
}

_RUN_STYLE = {
    "font_family": _p("string", "control", pattern="[A-Za-z0-9 ,_-]{1,80}"),
    "font_size": _p("number", "control", range=[8, 96], unit="px"),
    "color": _p("color", "control", pattern="#RRGGBB"),
    "bold": _p("boolean", "control"),
    "italic": _p("boolean", "control"),
    "underline": _p("boolean", "control"),
}

_MANIFEST: dict[str, Any] = {
    "version": MANIFEST_VERSION,
    "units": {"px": "CSS pixel, 1/96 inch (0.2646 mm)", "mm": "millimetre", "%": "percent of table width"},
    "components": {
        "text": {
            "description": "Single-style paragraph with {{path}} interpolation.",
            "properties": {
                "text": _p("string", "control"),
                **_TYPOGRAPHY, **_FLOW, **_PARAGRAPH_LAYOUT, **_OFFSET,
                "anchor_id": _p("string", "control", pattern="[A-Za-z][A-Za-z0-9_-]{0,63}"),
                "toc_level": _p("integer", "control"),
                "translation_key": _p("string", "none"),
            },
            "limitations": ["One style per block; mixed styling needs rich_text.",
                            "No list numbering, bullets, hanging-indent presets, borders, shading or columns.",
                            "Center and decimal tab alignment are not supported."],
        },
        "rich_text": {
            "description": "Paragraphs of typed runs (text, binding, condition).",
            "properties": {
                "paragraphs": _p("array", "control", max_items=100),
                "page_number": _FLOW["page_number"],
                **_PARAGRAPH_LAYOUT, **_OFFSET,
            },
            "paragraph_properties": {
                "align": _p("enum", "control", values=["left", "center", "right", "justify"]),
                "runs": _p("array", "control", max_items=200),
                **{key: dict(value, ui="json") for key, value in _PARAGRAPH_LAYOUT.items()},
            },
            "run_types": {
                "text": {"text": _p("string", "control"), "style": _p("object", "control", properties=_RUN_STYLE)},
                "binding": {"path": _p("path", "control"),
                            "format": _p("enum", "control", values=["text", "number", "currency", "date", "percent"]),
                            "currency": _p("string", "control", pattern="ISO 4217"),
                            "style": _p("object", "control", properties=_RUN_STYLE)},
                "condition": {"condition": _p("object", "control", operators=[
                    "equals", "not_equals", "in", "truthy", "greater_than", "greater_or_equal", "less_than", "less_or_equal"],
                    max_depth=4)},
            },
            "limitations": ["break_before and keep_together are not applied to rich_text blocks.",
                            "Block-level layout properties are applied to the block section and again to every paragraph.",
                            "No superscript/subscript, links, footnotes or list numbering."],
        },
        "table": {
            "description": "Rows repeated from a data array, or static rows (DD-431).",
            "properties": {
                "data_mode": _p("enum", "control", values=["bound", "static"]),
                "items": _p("path", "control"),
                "static_rows": _p("array", "control", max_items=1000,
                                  notes="Rows of cell strings ({{path}} interpolation allowed), at most one per column."),
                "columns": _p("array", "control", max_items=50, item_properties={
                    "header": _p("string", "control"), "path": _p("path", "control"),
                    "format": _p("enum", "control", values=["text", "number", "currency", "date", "percent"]),
                    "width": _p("number", "control", range=[5, 100], unit="%"),
                    "align": _p("enum", "control", values=["left", "center", "right"])}),
                "row_condition": _p("object", "control", properties={"path": "path", "equals": "scalar"}),
                "show_header": _p("boolean", "control"),
                "header_bold": _p("boolean", "control"),
                "header_background": _p("color", "control", pattern="#RRGGBB"),
                "font_family": _p("string", "control", pattern="[A-Za-z0-9 ,_-]{1,80}"),
                "font_size": _p("number", "control", range=[8, 96], unit="px", precision=2),
                "borders": _p("enum", "control", values=["grid", "horizontal", "none"]),
                "border_color": _p("color", "control", pattern="#RRGGBB"),
                "border_width": _p("number", "control", range=[0, 4], unit="px"),
                "cell_padding_x": _p("number", "control", range=[0, 48], unit="px"),
                "cell_padding_y": _p("number", "control", range=[0, 48], unit="px"),
                "row_height": _p("number", "control", range=[1, 400], unit="px"),
                "header_row_height": _p("number", "control", range=[1, 400], unit="px"),
                "header_spacing_after": _p("number", "control", range=[0, 240], unit="px"),
                "row_styles": _p("array", "control", max_items=50, item_properties={
                    "row": "integer body-row index from 0; negative counts from the end (-1 = last row)",
                    "bold": "boolean", "italic": "boolean", "background": "color #RRGGBB", "color": "color #RRGGBB"},
                    notes="Rows outside the table and invalid entries are ignored (DD-447)."),
                "paragraph_spacing_before": _p("number", "control", range=[0, 240], unit="px"),
                "paragraph_spacing_after": _p("number", "control", range=[0, 240], unit="px"),
                "break_before": _FLOW["break_before"], "keep_together": _FLOW["keep_together"],
                "page_number": _FLOW["page_number"],
            },
            "limitations": ["Maximum 1000 rows.",
                            "No merged cells, per-cell or per-column styling (other than alignment), or vertical alignment.",
                            "Tables span the content width; there is no table indent."],
        },
        "image": {
            "properties": {
                "src": _p("string", "control"), "source": _p("string", "control"),
                "alt": _p("string", "control"),
                "width": _p("number", "control", range=[1, 1200], unit="px"),
                "height": _p("number", "none", range=[1, 1200], unit="px", notes=_NOT_PERSISTED),
                "align": _p("enum", "control", values=["left", "center", "right"]),
                **_OFFSET, "break_before": _FLOW["break_before"], "keep_together": _FLOW["keep_together"],
                "page_number": _FLOW["page_number"],
            },
            "limitations": ["No absolute positioning, text wrap, cropping or z-order."],
        },
        "code": {
            "properties": {
                "value": _p("string", "control"),
                "code_type": _p("enum", "control", values=["qr", "code128", "ean13"]),
                "alt": _p("string", "control"),
                "width": _p("number", "control", range=[40, 1200], unit="px"),
                "break_before": _FLOW["break_before"], "keep_together": _FLOW["keep_together"],
                "page_number": _FLOW["page_number"],
            },
            "limitations": ["The editor saves an align value, but the renderer ignores it for codes."],
        },
        "chart": {
            "properties": {
                "chart_type": _p("enum", "control", values=["bar", "line", "pie"]),
                "data_mode": _p("enum", "control", values=["bound", "static"]),
                "items": _p("path", "control"), "static_data": _p("array", "control", max_items=100),
                "label_path": _p("path", "control"), "value_path": _p("path", "control"),
                "series_path": _p("path", "control"),
                "chart_title": _p("string", "control"), "x_axis_label": _p("string", "control"),
                "y_axis_label": _p("string", "control"),
                "chart_orientation": _p("enum", "control", values=["vertical", "horizontal"]),
                "show_grid": _p("boolean", "control"), "show_legend": _p("boolean", "control"),
                "show_points": _p("boolean", "control"), "show_values": _p("boolean", "control"),
                "stacked": _p("boolean", "control"), "donut": _p("boolean", "control"),
                "colors": _p("array", "control", item="color"), "axis_color": _p("color", "control"),
                "grid_color": _p("color", "control"), "background_color": _p("color", "control"),
                "page_number": _FLOW["page_number"],
            },
            "limitations": [],
        },
        "toc": {
            "properties": {"toc_label": _p("string", "control"), "page_number": _FLOW["page_number"]},
            "limitations": ["Lists blocks with anchor_id and toc_level; no leader or column styling."],
        },
        "shape": {
            "description": "Decorative line or rectangle (DD-433).",
            "properties": {
                "shape": _p("enum", "control", values=["line", "rectangle"]),
                "orientation": _p("enum", "control", values=["horizontal", "vertical"]),
                "width_mm": _p("number", "control", range=[0.1, 500], unit="mm"),
                "height_mm": _p("number", "control", range=[0.1, 500], unit="mm"),
                "stroke_color": _p("color", "control", pattern="#RRGGBB"),
                "stroke_width": _p("number", "control", range=[0, 10], unit="px"),
                "stroke_style": _p("enum", "control", values=["solid", "dashed", "dotted"]),
                "fill_color": _p("color", "control", pattern="#RRGGBB"),
                "layer": _p("enum", "control", values=["front", "behind"]),
                "position_mode": _p("enum", "control", values=["flow", "absolute"]),
                "position_x": _p("number", "control", range=[0, 500], unit="mm"),
                "position_y": _p("number", "control", range=[0, 500], unit="mm"),
                "position_unit": _p("enum", "control", values=["mm"]),
                "paragraph_spacing_before": _p("number", "control", range=[0, 240], unit="px"),
                "paragraph_spacing_after": _p("number", "control", range=[0, 240], unit="px"),
                "page_number": _FLOW["page_number"],
            },
            "limitations": ["Absolute shapes are placed within the page content area; page-margin areas are clipped.",
                            "No diagonal lines, rounded corners, ellipses or arbitrary paths."],
        },
        "columns": {
            "description": "Starts a column section (DD-435); blocks until columns_end are laid out in columns.",
            "properties": {
                "count": _p("integer", "control", range=[1, 4]),
                "gap_mm": _p("number", "control", range=[0, 50], unit="mm"),
                "widths": _p("array", "control", item="number", max_items=4, range=[5, 100], unit="%",
                             notes="One width per column, as % of the content width; widths plus the gap should not exceed 100%."),
                "rule_color": _p("color", "control", pattern="#RRGGBB"),
                "rule_width": _p("number", "control", range=[0, 4], unit="px"),
                "paragraph_spacing_before": _p("number", "control", range=[0, 240], unit="px"),
                "paragraph_spacing_after": _p("number", "control", range=[0, 240], unit="px"),
                "page_number": _FLOW["page_number"],
            },
            "limitations": ["With column_break markers content is split explicitly; without them it flows and balances.",
                            "Sections do not continue across page-owned surfaces; nested sections are not supported."],
        },
        "column_break": {"properties": {"page_number": _FLOW["page_number"]},
                         "limitations": ["Starts the next column of the open section; ignored outside a section."]},
        "columns_end": {"properties": {"page_number": _FLOW["page_number"]}, "limitations": []},
        "loop": {"properties": {"items": _p("path", "control"), "as": _p("string", "control"),
                                "blocks": _p("array", "control"), "empty": _p("array", "none")},
                 "limitations": ["Maximum 1000 items.", "The editor saves a loop body of exactly one plain text block."]},
        "if": {"properties": {"condition": _p("object", "control"), "then": _p("array", "control"),
                              "else": _p("array", "control")},
               "limitations": ["The editor saves only an equals-boolean condition with one plain text block per branch."]},
        "component": {"properties": {"component_id": _p("string", "control")}, "limitations": []},
    },
    "page": {
        "properties": {
            "size": _p("enum", "control", values=["A3", "A4", "A5", "Letter"]),
            "orientation": _p("enum", "control", values=["portrait", "landscape"]),
            "margin_mm": _p("number", "json", range=[0, 100], unit="mm"),
            **{f"margin_{side}_mm": _p("number", "control", range=[0, 100], unit="mm")
               for side in ("top", "right", "bottom", "left")},
            "header": _p("string", "control", max_length=500),
            "footer": _p("string", "control", max_length=500),
            "header_translation_key": _p("string", "none"),
            "footer_translation_key": _p("string", "none"),
            "header_component_id": _p("string", "control"),
            "footer_component_id": _p("string", "control"),
            "show_page_numbers": _p("boolean", "control"),
            "header_align": _p("enum", "control", values=["left", "center", "right"]),
            "footer_align": _p("enum", "control", values=["left", "center", "right"]),
            "page_number_position": _p("enum", "control", values=[f"{band}-{align}" for band in ("header", "footer")
                                                                   for align in ("left", "center", "right")]),
            "page_number_format": _p("string", "control", max_length=40, tokens=["{page}", "{pages}"]),
            "header_footer_font_size": _p("number", "control", range=[6, 48], unit="px", precision=2),
            **{f"{band}_{align}": _p("string", "control", max_length=500, notes="Zone text; overrides the legacy text in the same zone.")
               for band in ("header", "footer") for align in ("left", "center", "right")},
            "header_distance_mm": _p("number", "control", range=[0, 100], unit="mm", notes="Page top edge to the header text top."),
            "footer_distance_mm": _p("number", "control", range=[0, 100], unit="mm", notes="Page bottom edge to the footer text bottom."),
            "header_rule": _p("boolean", "control"),
            "footer_rule": _p("boolean", "control"),
            "header_rule_offset_mm": _p("number", "control", range=[0, 100], unit="mm", notes="Gap between the rule and the content area."),
            "footer_rule_offset_mm": _p("number", "control", range=[0, 100], unit="mm", notes="Gap between the content area and the rule."),
            "furniture_rule_color": _p("color", "control", pattern="#RRGGBB"),
            "furniture_rule_width": _p("number", "control", range=[0, 4], unit="px"),
            "zone_styles": _p("object", "control", keys=[f"{band}_{align}" for band in ("header", "footer")
                                                         for align in ("left", "center", "right")],
                              properties={"font_size": "number 6-48 px", "bold": "boolean", "italic": "boolean"},
                              notes="Per-zone overrides of header_footer_font_size, weight and style (DD-439)."),
            **{f"first_page_footer_{align}": _p("string", "control", max_length=500)
               for align in ("left", "center", "right")},
            "first_page_show_page_numbers": _p("boolean", "control"),
            "first_page_footer_distance_mm": _p("number", "control", range=[0, 100], unit="mm"),
            "first_page_footer_font_size": _p("number", "control", range=[6, 48], unit="px", precision=2),
            "background": _p("string", "json"),
            "background_pdf": _p("object", "control", fidelity="excluded",
                                 notes="Locked source background; excluded from E16 reconstruction."),
        },
        "limitations": [("Header and footer zones are plain text; zone_styles set size, bold and italic per zone, and "
                         "first_page_footer_* provides a first-page footer override, but there is no first-page header override."),
                        "Rules span the full content width; partial-width rules in the margins are not supported."],
    },
    "definition": {
        "properties": {
            "locale": _p("string", "control"), "translations": _p("object", "json"),
            "metadata": _p("object", "control", properties={"title": _p("string", "control", max_length=200),
                                                              "author": _p("string", "control", max_length=200)}),
            "data_schema": _p("object", "control"), "sample_data": _p("object", "control"),
            "missing_policy": _p("enum", "control", values=["error", "blank", "placeholder"]),
            "theme": _p("object", "json"),
        },
    },
}


def capability_manifest() -> dict[str, Any]:
    """Return a defensive copy of the editor capability manifest."""
    return deepcopy(_MANIFEST)


def declared_keys(manifest: dict[str, Any] | None = None) -> set[str]:
    """Every property key named anywhere in the manifest."""
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict) and "type" in value and "ui" in value:
                    found.add(key)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(manifest or _MANIFEST)
    return found
