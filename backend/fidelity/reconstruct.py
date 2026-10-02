"""Rule-based reconstruction through the editor-reachable template contract (E16-04, E16-10, DD-421).

The mapper turns a SourceModel plus taxonomy detections into a template
definition, the way a careful user of the editor would: the simplest component
that fits, only properties the capability manifest marks as editor-reachable,
and flow layout rather than absolute positioning. Anything it cannot express is
recorded as a coded gap. Agent-produced reconstructions use the same
``reconstruction-v1`` format and pass the same validator.
"""
from __future__ import annotations

import itertools
import re
from collections import defaultdict
from typing import Any

from fidelity.taxonomy import FEATURES, PT_TO_MM, REASON_CODES, _describe

RECONSTRUCTION_VERSION = "reconstruction-v1"
MAPPER_VERSION = "rule-based-mapper-v2"  # v2 (DD-427): justify, decimal sizes and positioned tab stops
MM_TO_PX = 96 / 25.4
PAGE_SIZES_MM = {"A3": (297, 420), "A4": (210, 297), "A5": (148, 210), "Letter": (215.9, 279.4)}
FONT_STACKS = {"serif": "Times New Roman, Liberation Serif, serif",
               "sans": "Arial, Liberation Sans, sans-serif",
               "mono": "Courier New, Liberation Mono, monospace",
               "unknown": "Times New Roman, Liberation Serif, serif"}
# Side-by-side blocks (DD-443): the least horizontal gap that separates them, the most gap the column section
# keeps (the rest goes to the columns), and how far apart a row's halves must differ to be separate blocks.
SIDE_GAP_MM, SIDE_COLUMN_GAP_MM, SIDE_SIZE_PT, SIDE_BASELINE_MM = 15.0, 6.0, 1.5, 1.0
# Liberation Serif metrics (Times-compatible), used to place the first baseline of a CSS line box.
ASCENT_EM, DESCENT_EM = 0.891, 0.216

# How each detected feature is handled by this mapper: None means expressed without a gap.
FEATURE_GAPS: dict[str, tuple[str, str, str, str] | None] = {
    # Justified text, decimal sizes, numbered labels, positioned gaps and leaders are expressible since
    # DD-424 to DD-426; remaining cases (leaders in centred or rich-text lines, out-of-range stops) are
    # recorded per paragraph below.
    # Tables are rebuilt as static tables with typography, alignment, rules and header shading (DD-432).
    # Rules and boxes become shape blocks (DD-434); only shapes in the clipped margin areas remain gaps.
    "image.raster": ("harness-limitation", "image", "src", "mapper does not extract source images yet"),
    # Two-column pages become column sections (DD-436).
    # Running headers, footers and page numbers are mapped by _map_furniture (DD-430); only multi-zone bands,
    # first-page differences and off-centre vertical placement remain gaps.
}


_LEADER_WORD = re.compile(r"^[.\u2026_\-]{3,}[.,;:]?$")
_NUMERIC = re.compile(r"^[\d.,%$\u20ac\u00a3()+\-]*\d[\d.,%$\u20ac\u00a3()+\-]*$")
LEADER_KINDS = {".": "dot", "\u2026": "dot", "_": "underscore", "-": "hyphen"}
MAX_STOPS = 16
MAX_INDENT_MM = 63.5  # the text left/first-line indent range, 240 px
MAX_ROW_STYLES = 50  # the table row_styles limit in the capability manifest (DD-447)


def _join(words: list[dict[str, Any]]) -> str:
    out = ""
    for index, word in enumerate(words):
        if index:
            previous = words[index - 1]
            gap = word["x_mm"] - (previous["x_mm"] + previous["width_mm"])
            out += " " if gap > 0.1 * previous["size_pt"] * PT_TO_MM else ""
        out += word["text"]
    return out


def row_tabs(page: dict[str, Any], row: list[int], origin_mm: float) -> tuple[str, list[dict[str, Any]], bool]:
    """Express one source row as tab segments and stops (DD-427).

    Words split into groups at leader words (dots, underscores, hyphens) and at gaps wider than 1 em.
    A leader becomes a tab whose stop is the leader's end, or a right stop at the end of an adjacent
    number. Numeric groups become right stops at their end; other groups left stops at their start.
    Positions are px from ``origin_mm`` (the paragraph's left indent). Returns the text, the stops and
    whether the row was expressible (False when stops exceed bounds; the text then has no tabs).
    """
    words = sorted((page["words"][i] for line in row for i in page["lines"][line].get("word_indices", [])),
                   key=lambda w: w["x_mm"])
    plain = " ".join(page["lines"][line]["text"].replace("\t", " ") for line in row)
    if not words:
        return plain, [], True
    groups: list[dict[str, Any]] = []
    for word in words:
        kind = "leader" if _LEADER_WORD.match(word["text"]) else "text"
        if groups and kind == "text" and groups[-1]["kind"] == "text":
            previous = groups[-1]["words"][-1]
            if word["x_mm"] - (previous["x_mm"] + previous["width_mm"]) <= previous["size_pt"] * PT_TO_MM:
                groups[-1]["words"].append(word)
                continue
        groups.append({"kind": kind, "words": [word]})
    if len(groups) == 1 and groups[0]["kind"] == "text":
        return _join(groups[0]["words"]), [], True

    def start(group: dict[str, Any]) -> float:
        return group["words"][0]["x_mm"]

    def end(group: dict[str, Any]) -> float:
        return group["words"][-1]["x_mm"] + group["words"][-1]["width_mm"]

    def numeric(group: dict[str, Any]) -> bool:
        return group["kind"] == "text" and bool(_NUMERIC.match(_join(group["words"]).replace(" ", "")))

    segments, stops = [""], []
    closed = False
    index = 0
    while index < len(groups):
        group = groups[index]
        following = groups[index + 1] if index + 1 < len(groups) else None
        if group["kind"] == "leader":
            leader = LEADER_KINDS.get(group["words"][0]["text"][0], "dot")
            em = group["words"][0]["size_pt"] * PT_TO_MM
            if following and numeric(following) and start(following) - end(group) <= 1.5 * em:
                stops.append({"position": end(following), "align": "right", "leader": leader})
                segments.append(_join(following["words"]))
                closed, index = True, index + 2
                continue
            stops.append({"position": end(group), "align": "left", "leader": leader})
            segments.append("")
            closed, index = False, index + 1
            continue
        if segments[-1] == "" and not closed:
            segments[-1] = _join(group["words"])
        elif numeric(group):
            stops.append({"position": end(group), "align": "right", "leader": "none"})
            segments.append(_join(group["words"]))
            closed = True
        else:
            stops.append({"position": start(group), "align": "left", "leader": "none"})
            segments.append(_join(group["words"]))
            closed = False
        index += 1
    for stop in stops:
        position = _px(stop["position"] - origin_mm)
        stop["position"] = 0.0 if -0.5 < position < 0 else position  # a stop at the indent itself
    positions = [stop["position"] for stop in stops]
    if len(stops) > MAX_STOPS or any(not 0 <= p <= 2000 for p in positions) or positions != sorted(set(positions)):
        return plain, [], False
    return "\t".join(segments), [s if s["align"] == "right" or s["leader"] != "none" else s["position"] for s in stops], True


def _with_leading_stop(stops: list[Any], leading_px: float) -> list[Any] | None:
    """Prepend a left stop at ``leading_px`` and shift the row's stops by it, or None if out of bounds (DD-449)."""
    shifted: list[Any] = [leading_px]
    for stop in stops:
        if isinstance(stop, dict):
            shifted.append({**stop, "position": round(stop["position"] + leading_px, 2)})
        else:
            shifted.append(round(stop + leading_px, 2))
    positions = [s["position"] if isinstance(s, dict) else s for s in shifted]
    if len(shifted) > MAX_STOPS or positions[-1] > 2000 or positions != sorted(set(positions)):
        return None
    return shifted


def _px(mm: float) -> float:
    return round(mm * MM_TO_PX, 2)


def _overlaps(a: list[float], b: list[float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _baseline_offset_mm(size_pt: float, line_height: float) -> float:
    size_mm = size_pt * PT_TO_MM
    return ((line_height - (ASCENT_EM + DESCENT_EM)) / 2 + ASCENT_EM) * size_mm


def reconstruct(model: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Map a SourceModel and its detections to a template definition with provenance and gaps."""
    detections = features["detections"]
    by_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detection in detections:
        by_feature[detection["feature"]].append(detection)
    gaps: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    def gap(feature: str, reason: str, component: str, prop: str, note: str, detection_id: str | None) -> None:
        key = (feature, reason, component, prop)
        entry = gaps.setdefault(key, {"feature": feature, "reason": reason, "component": component,
                                      "property": prop, "note": note, "detection_ids": [], "occurrences": 0})
        entry["occurrences"] += 1
        if detection_id:
            entry["detection_ids"].append(detection_id)

    for feature, mapping in FEATURE_GAPS.items():
        if mapping:
            for detection in by_feature.get(feature, []):
                gap(feature, *mapping, detection["id"])
    first = model["pages"][0]
    page_settings: dict[str, Any] = {"orientation": "portrait"}
    width, height = first["width_mm"], first["height_mm"]
    if width > height:
        page_settings["orientation"] = "landscape"
        width, height = height, width
    size = min(PAGE_SIZES_MM, key=lambda name: abs(PAGE_SIZES_MM[name][0] - width) + abs(PAGE_SIZES_MM[name][1] - height))
    page_settings["size"] = size
    size_detection = by_feature["page.size"][0]["id"] if by_feature.get("page.size") else None
    if abs(PAGE_SIZES_MM[size][0] - width) + abs(PAGE_SIZES_MM[size][1] - height) > 2:
        gap("page.size", "value-out-of-range", "page", "size",
            f"{width:.1f} x {height:.1f} mm is not one of A3/A4/A5/Letter; nearest {size} used", size_detection)
    margins = by_feature["page.margins"][0]["evidence"] if by_feature.get("page.margins") else \
        {"top": 20, "right": 20, "bottom": 20, "left": 20}
    for side in ("top", "right", "bottom", "left"):
        value = round(float(margins[side]), 1)
        if not 0 <= value <= 100:
            gap("page.margins", "value-out-of-range", "page", f"margin_{side}_mm", f"{value} mm outside 0-100",
                by_feature["page.margins"][0]["id"])
        page_settings[f"margin_{side}_mm"] = max(0.0, min(100.0, value))
    _map_furniture(model, by_feature, page_settings, gap)

    content_left = page_settings["margin_left_mm"]
    content_right = width - page_settings["margin_right_mm"]
    body_pt = features["body_size_pt"]
    pitches = [p["pitch_mm"] for paragraphs in features["paragraphs"].values() for p in paragraphs if p["pitch_mm"]]
    body_line_height = round(sorted(pitches)[len(pitches) // 2] / (body_pt * PT_TO_MM), 3) if pitches else 1.2

    table_rows: dict[tuple[int, int], dict[str, Any]] = {}
    for detection in by_feature.get("table.grid", []):
        for page_number, index in detection["lines"]:
            table_rows[(page_number, index)] = detection
    feature_lines: dict[tuple[int, int], set[str]] = defaultdict(set)
    for detection in detections:
        for page_number, index in detection["lines"]:
            feature_lines[(page_number, index)].add(detection["feature"])

    blocks: list[dict[str, Any]] = []
    first_tops: list[tuple[int, float]] = []  # (block index, top in mm) of the first block on each page
    absolute_tops: list[tuple[int, float]] = []  # (block index, top in mm) of absolutely placed blocks
    lowest_bottom = 0.0  # lowest computed block bottom on any page, in mm from the page top
    provenance: list[dict[str, Any]] = []
    sample_data: dict[str, Any] = {}
    emitted_tables: set[str] = set()
    effort = {"workarounds": 0, "properties_set": 0, "rich_text_runs": 0, "absolute_blocks": 0, "shapes": 0}
    used_graphics: set[tuple[int, tuple[float, ...]]] = set()  # graphics already expressed by a table

    for page in model["pages"]:
        number = page["page_number"]
        previous_bottom: float | None = None  # bottom of the previous block on this page, in mm
        col_left, col_right = content_left, content_right  # edges of the current column (or the content area)
        column_bottoms: list[float] = []
        container_top = 0.0
        for kind, item in _page_items(page, features["paragraphs"].get(number, []), body_line_height, content_right):
            if kind != "para":
                marker: dict[str, Any] = {"type": {"start": "columns", "break": "column_break", "end": "columns_end"}[kind],
                                          "page_number": number}
                if kind == "start":
                    container_top = item["top"]
                    if previous_bottom is None:
                        first_tops.append((len(blocks), container_top))
                    start = page_settings["margin_top_mm"] if previous_bottom is None else previous_bottom
                    width = max(1.0, content_right - content_left)
                    marker.update({
                        "count": 2, "gap_mm": round(max(0.0, min(50.0, item["right_left"] - item["left_right"])), 2),
                        "widths": [round(max(5.0, min(100.0, (item["left_right"] - content_left) / width * 100)), 2),
                                   round(max(5.0, min(100.0, (content_right - item["right_left"]) / width * 100)), 2)],
                        "paragraph_spacing_before": min(240.0, _px(max(0.0, container_top - start)))})
                    previous_bottom, column_bottoms = container_top, []
                    col_left, col_right = content_left, item["left_right"]
                elif kind == "break":
                    column_bottoms.append(previous_bottom)
                    previous_bottom = container_top
                    col_left, col_right = item["right_left"], content_right
                else:
                    column_bottoms.append(previous_bottom)
                    previous_bottom = max(column_bottoms)
                    col_left, col_right = content_left, content_right
                blocks.append(marker)
                provenance.append({"block": len(blocks) - 1, "page": number, "lines": [], "box_mm": [0, 0, 0, 0],
                                   "detections": []})
                continue
            paragraph = item
            first_ref = (number, paragraph["rows"][0][0])
            if first_ref in table_rows:
                detection = table_rows[first_ref]
                if detection["id"] in emitted_tables:
                    continue
                emitted_tables.add(detection["id"])
                block, top, bottom, used = _table_block(page, detection, col_left, col_right)
                if block.pop("_unstyled_bold_rows"):
                    gap("table.grid", "value-out-of-range", "table", "row_styles",
                        "more bold body rows than row_styles entries allow", detection["id"])
                used_graphics.update((number, tuple(box)) for box in used)
                if previous_bottom is None:
                    first_tops.append((len(blocks), top))
                start = page_settings["margin_top_mm"] if previous_bottom is None else previous_bottom
                block["paragraph_spacing_before"] = min(240.0, _px(max(0.0, top - start)))
                block["page_number"] = number
                blocks.append(block)
                provenance.append({"block": len(blocks) - 1, "page": number, "lines": detection["lines"],
                                   "box_mm": detection["box_mm"], "detections": [detection["id"]]})
                effort["properties_set"] += len([k for k in block if k not in {"type", "columns", "static_rows"}])
                previous_bottom = bottom
                lowest_bottom = max(lowest_bottom, bottom)
                continue
            lines = [page["lines"][i] for row in paragraph["rows"] for i in row]
            size_pt, line_height, offset = _paragraph_metrics(page, paragraph, body_line_height)
            first_baseline = page["lines"][paragraph["rows"][0][0]]["y_mm"]
            # Spacing runs from the previous block's bottom to this paragraph's first line-box top; for consecutive
            # paragraphs of one size this equals the previous baseline-to-baseline rule (DD-432).
            first_on_page = previous_bottom is None
            start = page_settings["margin_top_mm"] if previous_bottom is None else previous_bottom
            space_mm = first_baseline - offset - start
            spacing = _px(max(0.0, space_mm))
            absolute_top = None
            if spacing > 240:
                # Spacing-before is capped at 240 px; a user would place such a block at fixed coordinates.
                gap("text.paragraph", "workaround-used", "text", "paragraph_spacing_before",
                    "space above exceeds 240 px; block placed with absolute positioning", None)
                absolute_top = first_baseline - offset
                spacing = 0
            else:
                if first_on_page:
                    first_tops.append((len(blocks), first_baseline - offset))
                previous_bottom = (page["lines"][paragraph["rows"][-1][0]]["y_mm"] - offset
                                   + line_height * size_pt * PT_TO_MM)
                lowest_bottom = max(lowest_bottom, previous_bottom)
            refs = {(p, i) for p, i in paragraph["lines"]}
            features_here = set().union(*(feature_lines.get(ref, set()) for ref in refs))
            align = "left"
            if paragraph.get("align_hint"):
                align = paragraph["align_hint"]
            elif "text.align_center" in features_here:
                align = "center"
            elif "text.align_right" in features_here:
                align = "right"
            layout = {
                "align": align,
                "line_height": line_height,
                "paragraph_spacing_before": spacing,
                "paragraph_spacing_after": 0,
                "left_indent": _px(max(-MAX_INDENT_MM, min(MAX_INDENT_MM, paragraph["left_mm"] - col_left))),
                "first_line_indent": _px(max(-MAX_INDENT_MM, min(MAX_INDENT_MM,
                                                                 paragraph["first_left_mm"] - paragraph["left_mm"]))),
                "page_number": number,
            }
            if absolute_top is not None:
                # position_y is finalised once the top margin is known; the origin is the content box.
                layout.update({"position_mode": "absolute", "position_unit": "mm",
                               "position_x": 0.0 if align in {"center", "right"}
                               else round(max(0.0, paragraph["left_mm"] - content_left), 2),
                               "left_indent": 0})
                layout["paragraph_spacing_before"] = 0  # explicit 0: otherwise the browser's default 1 em margin applies
                absolute_tops.append((len(blocks), absolute_top))
                lowest_bottom = max(lowest_bottom, absolute_top + len(paragraph["rows"]) * line_height * size_pt * PT_TO_MM)
                effort["absolute_blocks"] += 1
            if align in {"center", "right"}:
                layout["left_indent"] = 0
                layout["first_line_indent"] = 0
            # A one-line paragraph starting beyond the indent range (a right-hand election or form cell) starts
            # with a tab to a left stop at its offset, as a Word user would type it; longer paragraphs keep the
            # clamped indent and record the gap instead of hiding it (DD-449).
            leading_px = None
            if absolute_top is None and align == "left":
                indent_mm = paragraph["left_mm"] - col_left
                hanging_mm = paragraph["first_left_mm"] - paragraph["left_mm"]
                if indent_mm > MAX_INDENT_MM and len(paragraph["rows"]) == 1:
                    leading_px = _px(indent_mm)
                    layout["left_indent"] = layout["first_line_indent"] = 0
                elif abs(indent_mm) > MAX_INDENT_MM or abs(hanging_mm) > MAX_INDENT_MM:
                    gap("text.paragraph", "value-out-of-range", "text", "left_indent",
                        f"indent of {max(abs(indent_mm), abs(hanging_mm)):.1f} mm clamped to {MAX_INDENT_MM} mm", None)
            if len(paragraph["rows"]) >= 2 and "text.align_justify" in features_here:
                layout["right_indent"] = _px(max(0.0, min(63.5, col_right - paragraph["right_mm"])))
                if align == "left":
                    align = layout["align"] = "justify"
            family = FONT_STACKS[lines[0]["family_class"]]
            paragraph_detections = [d for d in detections if d["page"] == number
                                    and {(p, i) for p, i in d["lines"]} & refs]
            leaders_literal = paragraph["mixed_style"] or align in {"center", "right"}
            for detection in paragraph_detections:
                if detection["feature"] == "tab.dot_leader" and leaders_literal:
                    gap("tab.dot_leader", "workaround-used", "rich_text" if paragraph["mixed_style"] else "text",
                        "tab_stops", "leader kept as literal characters in a centred, right-aligned or rich-text line",
                        detection["id"])
            if paragraph["mixed_style"]:
                first_row = paragraph["rows"][0]
                positions = sorted([x for i in first_row for x in page["lines"][i].get("tabs_mm", [])]
                                   + [page["lines"][i]["x_mm"] for i in first_row[1:]])
                if positions and align in {"left", "justify"}:
                    stops = [max(0.0, p) if p > -0.5 else p for p in (_px(x - paragraph["left_mm"]) for x in positions)]
                    if stops and len(stops) <= MAX_STOPS and all(0 <= s <= 2000 for s in stops):
                        layout["tab_stops"] = stops
                    elif stops:
                        for detection in paragraph_detections:
                            if detection["feature"] in {"list.numbered_label", "tab.positioned_gap"}:
                                gap(detection["feature"], "value-out-of-range", "rich_text", "tab_stops",
                                    "stop outside 0-2000 px or more than 16 stops", detection["id"])
                runs = _runs(page, paragraph, family)
                if leading_px is not None and runs:
                    stops = _with_leading_stop(layout.get("tab_stops", []), leading_px)
                    if stops is not None:
                        layout["tab_stops"] = stops
                        runs[0]["text"] = "	" + runs[0]["text"]
                    else:
                        layout["left_indent"] = _px(MAX_INDENT_MM)
                        gap("text.paragraph", "value-out-of-range", "rich_text", "tab_stops",
                            "leading tab stop outside 0-2000 px or more than 16 stops", None)
                effort["rich_text_runs"] += len(runs)
                block = {"type": "rich_text", "paragraphs": [{"align": align, "runs": runs}],
                         **{k: v for k, v in layout.items() if k != "align"}}
            else:
                font_px = round(size_pt * 4 / 3, 2)
                if not 8 <= font_px <= 96:
                    gap("text.paragraph", "value-out-of-range", "text", "font_size",
                        f"needed {font_px:.2f} px; range is 8-96", None)
                    font_px = max(8.0, min(96.0, font_px))
                rows_text = [" ".join(page["lines"][i]["text"].replace("\t", " ") for i in row) for row in paragraph["rows"]]
                if align in {"left", "justify"}:
                    first_text, stops, expressible = row_tabs(page, paragraph["rows"][0], paragraph["left_mm"])
                    rows_text[0] = first_text
                    if leading_px is not None:
                        leading = _with_leading_stop(stops, leading_px)
                        if leading is not None:
                            rows_text[0], stops = "	" + rows_text[0], leading
                        else:
                            layout["left_indent"] = _px(MAX_INDENT_MM)
                            gap("text.paragraph", "value-out-of-range", "text", "tab_stops",
                                "leading tab stop outside 0-2000 px or more than 16 stops", None)
                    if stops:
                        layout["tab_stops"] = stops
                    if not expressible:
                        for detection in paragraph_detections:
                            if detection["feature"] in {"list.numbered_label", "tab.positioned_gap", "tab.dot_leader"}:
                                gap(detection["feature"], "value-out-of-range", "text", "tab_stops",
                                    "stop outside 0-2000 px, unordered, or more than 16 stops", detection["id"])
                block = {"type": "text", "text": " ".join(rows_text), "font_family": family, "font_size": font_px,
                         "bold": paragraph["bold"], "italic": paragraph["italic"], "color": "#000000", **layout}
            blocks.append(block)
            effort["properties_set"] += len([k for k in block if k not in {"type", "text", "paragraphs"}])
            provenance.append({"block": len(blocks) - 1, "page": number, "lines": paragraph["lines"],
                               "box_mm": paragraph["box_mm"],
                               "detections": sorted({d["id"] for d in detections
                                                     if d["page"] == number and _overlaps(d["box_mm"], paragraph["box_mm"])
                                                     and d["feature"] not in {"page.size", "page.margins"}})})
    # The detected top margin is a text-top estimate; the first block of a page (a table row, or a line box with
    # leading) may need to start above it. Lower the margin to the highest first-block top and recompute each
    # page's first spacing from it, instead of clamping to zero (DD-432).
    if first_tops:
        highest = min(top for _, top in first_tops)
        if highest < page_settings["margin_top_mm"]:
            page_settings["margin_top_mm"] = max(0.0, round(highest, 2))
        for index, top in first_tops:
            blocks[index]["paragraph_spacing_before"] = min(240.0, _px(max(0.0, top - page_settings["margin_top_mm"])))
    # Likewise the bottom margin: page-owned surfaces clip at the content area, so every computed block bottom
    # must fit inside it.
    if lowest_bottom and height - page_settings["margin_bottom_mm"] < lowest_bottom + 0.5:
        page_settings["margin_bottom_mm"] = max(0.0, round(height - lowest_bottom - 0.5, 2))
    for index, top in absolute_tops:
        blocks[index]["position_y"] = round(max(0.0, min(450.0, top - page_settings["margin_top_mm"])), 2)
    _map_furniture_rules(model, page_settings, used_graphics)
    _map_shapes(model, by_feature, page_settings, used_graphics, blocks, provenance, effort, gap)
    effort["workarounds"] += sum(len(g["detection_ids"]) for g in gaps.values() if g["reason"] == "workaround-used")
    block_types: dict[str, int] = defaultdict(int)
    for block in blocks:
        block_types[block["type"]] += 1
    definition = {"name": f"E16 reconstruction {model.get('sha256', '')[:12]}", "locale": "en",
                  "missing_policy": "blank", "page": page_settings, "blocks": blocks,
                  "metadata": {"title": model.get("label") or "E16 reconstruction", "author": "E16 fidelity harness"},
                  "sample_data": sample_data,
                  "theme": {"font_family": FONT_STACKS[_body_family(model)]}}
    return {"contract": RECONSTRUCTION_VERSION, "method": MAPPER_VERSION,
            "source": {"label": model.get("label"), "sha256": model.get("sha256")},
            "definition": definition, "provenance": provenance, "gaps": list(gaps.values()),
            "effort": {"blocks": len(blocks), "block_types": dict(block_types), **effort,
                       "properties_per_block": round(effort["properties_set"] / max(1, len(blocks)), 2)}}


def _paragraph_metrics(page: dict[str, Any], paragraph: dict[str, Any], body_line_height: float
                       ) -> tuple[float, float, float]:
    """Font size the renderer lays the paragraph out with, its line-height multiple, and the baseline offset (mm)."""
    lines = [page["lines"][i] for row in paragraph["rows"] for i in row]
    size_pt = paragraph["size_pt"]
    if paragraph["mixed_style"]:
        # The renderer sizes a rich-text line by its largest run (DD-428); lay it out the same way.
        size_pt = max(run["size_pt"] for line in lines for run in line.get("runs", [line]))
    line_height = (round(paragraph["pitch_mm"] / (size_pt * PT_TO_MM), 3)
                   if paragraph["pitch_mm"] else body_line_height * paragraph["size_pt"] / size_pt)
    line_height = max(0.8, min(3.0, line_height))
    return size_pt, line_height, _baseline_offset_mm(size_pt, line_height)


def _page_items(page: dict[str, Any], paragraphs: list[dict[str, Any]], body_line_height: float,
                content_right: float) -> list[tuple[str, Any]]:
    """Order a page's paragraphs, wrapping a detected two-column region in a column section (DD-436).

    Full-width paragraphs above the columns come first and those below come after; the left column's
    paragraphs precede a column break and the right column's. Pages without a gutter may still hold
    side-by-side blocks, such as a letterhead (DD-443).
    """
    plain = [("para", p) for p in paragraphs]
    gutter = page.get("gutter_mm")
    if gutter is None:
        return _side_by_side(page, paragraphs, body_line_height, content_right)

    def in_right(p: dict[str, Any]) -> bool:
        return any(page["lines"][i].get("column", 0) == 1 for row in p["rows"] for i in row)

    right = [p for p in paragraphs if in_right(p)]
    left = [p for p in paragraphs if not in_right(p) and p["right_mm"] <= gutter + 1]
    if not right or not left:
        return plain
    chosen = {id(p) for p in left + right}
    full = [p for p in paragraphs if id(p) not in chosen]

    def top(p: dict[str, Any]) -> float:
        return page["lines"][p["rows"][0][0]]["y_mm"] - _paragraph_metrics(page, p, body_line_height)[2]

    container_top = min(top(p) for p in left + right)
    above = [p for p in full if p["box_mm"][3] <= container_top + 1]
    below = [p for p in full if p["box_mm"][3] > container_top + 1]
    info = {"top": container_top, "left_right": max(p["right_mm"] for p in left),
            "right_left": min(min(p["left_mm"], p["first_left_mm"]) for p in right)}
    return ([("para", p) for p in above] + [("start", info)] + [("para", p) for p in left] + [("break", info)]
            + [("para", p) for p in right] + [("end", info)] + [("para", p) for p in below])


def _body_family(model: dict[str, Any]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for page in model["pages"]:
        for line in page["lines"]:
            counts[line["family_class"]] += len(line["text"])
    return max(counts, key=counts.get) if counts else "serif"


def _zone(line: dict[str, Any], page: dict[str, Any], left: float, right: float) -> str:
    """Horizontal zone of a furniture line relative to the content edges."""
    start, end = line["x_mm"], line["x_mm"] + line["width_mm"]
    if abs(start - left) <= 5:
        return "left"
    if abs(end - right) <= 5:
        return "right"
    return "center" if abs((start + end) / 2 - (left + right) / 2) <= 10 else ("left" if end < (left + right) / 2 else "right")


# Liberation Serif/Sans line-box geometry at normal line height: baseline below the line-box top, and the
# line-box bottom below the baseline, in em.
FURNITURE_ASCENT_EM, FURNITURE_DESCENT_EM = 0.91, 0.24


def _map_furniture(model: dict[str, Any], by_feature: dict[str, list[dict[str, Any]]], page_settings: dict[str, Any],
                   gap: Any) -> None:
    """Map running headers, footers and page numbers to editor page properties (DD-430, DD-438).

    Every furniture line goes to its own zone (left, centre or right); the band's distance from the page edge
    is measured from the source baseline; the page number keeps its band, zone and text format.
    """
    left = page_settings["margin_left_mm"]
    pages = model["pages"]
    sizes: list[float] = []
    zone_lines: dict[str, dict[str, Any]] = {}  # zone -> the source line placed there, for per-zone styling
    anchors: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for feature, band in (("page.running_header", "header"), ("page.running_footer", "footer")):
        detections = by_feature.get(feature, [])
        if not detections:
            continue
        sample = detections[len(detections) // 2]
        page = pages[sample["page"] - 1]
        right = page["width_mm"] - page_settings["margin_right_mm"]
        lines = sorted((page["lines"][i] for _, i in sample["lines"]), key=lambda line: line["x_mm"])
        for line in lines:
            key = f"{band}_{_zone(line, page, left, right)}"
            page_settings[key] = (page_settings.get(key, "") + " " + line["text"].replace("\t", " ")).strip()[:500]
            zone_lines.setdefault(key, line)
        sizes.extend(line["size_pt"] for line in lines)
        anchors[band] = (lines[0], page)
        _first_page_gap(feature, band, detections, gap)
    numbers = by_feature.get("page.page_number", [])
    if numbers:
        sample = numbers[len(numbers) // 2]
        page = pages[sample["page"] - 1]
        right = page["width_mm"] - page_settings["margin_right_mm"]
        line = page["lines"][sample["lines"][0][1]]
        band = "header" if line["y_mm"] < page["height_mm"] / 2 else "footer"
        number_format = line["text"].replace("\t", " ")
        number_format = number_format.replace(str(len(pages)), "{pages}") if str(len(pages)) != str(sample["page"]) \
            else number_format
        number_format = number_format.replace(str(sample["page"]), "{page}", 1)
        page_settings.update({"show_page_numbers": True, "page_number_position": f"{band}-{_zone(line, page, left, right)}",
                              "page_number_format": number_format[:40] if "{page}" in number_format else "{page}"})
        sizes.append(line["size_pt"])
        zone_lines.setdefault(page_settings["page_number_position"].replace("-", "_"), line)
        anchors.setdefault(band, (line, page))
        _first_page_gap("page.page_number", band, numbers, gap)
    for band, (line, page) in anchors.items():
        size_mm = line["size_pt"] * PT_TO_MM
        distance = (line["y_mm"] - FURNITURE_ASCENT_EM * size_mm if band == "header"
                    else page["height_mm"] - line["y_mm"] - FURNITURE_DESCENT_EM * size_mm)
        page_settings[f"{band}_distance_mm"] = round(max(0.0, min(100.0, distance)), 2)
    if sizes:
        median = sorted(sizes)[len(sizes) // 2]  # the shared size is the median; differing zones get zone styles
        page_settings["header_footer_font_size"] = max(6.0, min(48.0, round(median * 4 / 3, 2)))
        styles: dict[str, dict[str, Any]] = {}
        for zone, line in zone_lines.items():
            style: dict[str, Any] = {}
            if abs(line["size_pt"] - median) > 0.3:
                style["font_size"] = max(6.0, min(48.0, round(line["size_pt"] * 4 / 3, 2)))
            if line["bold"]:
                style["bold"] = True
            if line["italic"]:
                style["italic"] = True
            if style:
                styles[zone] = style
        if styles:
            page_settings["zone_styles"] = styles  # DD-440


def _first_page_gap(feature: str, band: str, detections: list[dict[str, Any]], gap: Any) -> None:
    if len(detections) > 1 and 1 not in {d["page"] for d in detections}:
        gap(feature, "missing-property", "page", f"{band}_first_page",
            f"page 1 has no running {band}; a different first page is not supported", detections[0]["id"])


def _map_furniture_rules(model: dict[str, Any], page_settings: dict[str, Any],
                         used: set[tuple[int, tuple[float, ...]]]) -> None:
    """Express rules recurring in the header or footer margin as header/footer rules (DD-438).

    A rule counts when it lies in the top or bottom margin, spans at least 60% of the content width and recurs
    on at least half the pages. The rule's offset from the content area, colour and thickness are kept.
    """
    pages = model["pages"]
    width = pages[0]["width_mm"] - page_settings["margin_left_mm"] - page_settings["margin_right_mm"]
    for band in ("header", "footer"):
        found = []
        for page in pages:
            limit_top = page_settings["margin_top_mm"]
            limit_bottom = page["height_mm"] - page_settings["margin_bottom_mm"]
            for graphic in page["graphics"]:
                box = graphic["box_mm"]
                if graphic["kind"] != "rule" or box[2] - box[0] < 0.6 * width:
                    continue
                if (band == "header" and box[3] <= limit_top) or (band == "footer" and box[1] >= limit_bottom):
                    found.append((page, graphic))
        if len({page["page_number"] for page, _ in found}) < max(1, len(pages) // 2):
            continue
        page, graphic = found[0]
        box = graphic["box_mm"]
        centre = (box[1] + box[3]) / 2
        offset = (page_settings["margin_top_mm"] - centre if band == "header"
                  else centre - (page["height_mm"] - page_settings["margin_bottom_mm"]))
        thickness_mm = max(0.05, graphic.get("thickness_pt", 0.75) * PT_TO_MM)
        page_settings.update({f"{band}_rule": True, f"{band}_rule_offset_mm": round(max(0.0, min(100.0, offset)), 2),
                              "furniture_rule_color": graphic.get("fill") or graphic.get("stroke") or "#000000",
                              "furniture_rule_width": round(min(4.0, thickness_mm * MM_TO_PX), 2)})
        used.update((p["page_number"], tuple(g["box_mm"])) for p, g in found)


def _runs(page: dict[str, Any], paragraph: dict[str, Any], family: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for row_index, row in enumerate(paragraph["rows"]):
        for segment_index, line_index in enumerate(row):
            prefix = " " if row_index and segment_index == 0 else "\t" if segment_index else ""
            if row_index and prefix == "\t":
                prefix = " "  # stops describe the first row only; later rows wrap as plain text
            for run_index, run in enumerate(page["lines"][line_index].get("runs", [])):
                text = (prefix if run_index == 0 else "") + (run["text"].replace("\t", " ") if row_index else run["text"])
                style = {"font_family": family, "font_size": round(run["size_pt"] * 4 / 3, 2),
                         "bold": run["bold"], "italic": run["italic"]}
                if runs and runs[-1]["style"] == style:
                    runs[-1]["text"] += text
                else:
                    runs.append({"type": "text", "text": text, "style": style})
    return runs[:200]


def _table_block(page: dict[str, Any], detection: dict[str, Any], left: float, right: float
                 ) -> tuple[dict[str, Any], float, float]:
    """Rebuild a detected grid as a static table matched to the source (DD-432).

    Returns the block and its top and bottom in mm. Column alignment comes from whichever cell edge lines
    up best; boundaries sit a cell padding away from aligned edges; the row height is the source row pitch;
    a filled box behind the first row becomes the header shading; horizontal rules between rows become
    horizontal borders.
    """
    # Cells share a row when their baselines lie within a third of an em of the row's first baseline. Rounding
    # to a 0.5 mm grid split a row whose last cell sat 0.4 mm lower into two rows (DD-449).
    rows: list[list[dict[str, Any]]] = []
    for line in sorted((page["lines"][index] for _, index in detection["lines"]), key=lambda c: c["y_mm"]):
        if rows and line["y_mm"] - rows[-1][0]["y_mm"] <= line["size_pt"] * PT_TO_MM / 3:
            rows[-1].append(line)
        else:
            rows.append([line])
    rows = [sorted(cells, key=lambda c: c["x_mm"]) for cells in rows]
    width = max(1.0, right - left)
    count = max(len(row) for row in rows)
    template = max(rows, key=len)
    columns: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    for row in rows:
        for cell in row:
            centre = cell["x_mm"] + cell["width_mm"] / 2
            nearest = min(range(count), key=lambda i: min(
                abs(cell["x_mm"] - template[i]["x_mm"]),
                abs(cell["x_mm"] + cell["width_mm"] - template[i]["x_mm"] - template[i]["width_mm"]),
                abs(centre - template[i]["x_mm"] - template[i]["width_mm"] / 2)))
            columns[nearest].append(cell)

    def spread(values: list[float]) -> float:
        return max(values) - min(values) if values else 0.0

    aligns = []
    for cells in columns:
        lefts = [c["x_mm"] for c in cells]
        rights = [c["x_mm"] + c["width_mm"] for c in cells]
        centres = [c["x_mm"] + c["width_mm"] / 2 for c in cells]
        best = min((spread(lefts), "left"), (spread(rights), "right"), (spread(centres) + 0.5, "center"))
        aligns.append(best[1])
    first_cells = columns[0]
    padding_mm = max(0.0, min(12.0, min(c["x_mm"] for c in first_cells) - left)) if aligns[0] == "left" else 1.5
    boundaries = [left]
    for index in range(1, count):
        previous_end = max(c["x_mm"] + c["width_mm"] for c in columns[index - 1]) if columns[index - 1] else boundaries[-1]
        start = min(c["x_mm"] for c in columns[index]) if columns[index] else previous_end
        if aligns[index] == "left":
            boundary = start - padding_mm
        elif aligns[index - 1] == "right":
            boundary = previous_end + padding_mm
        else:
            boundary = (previous_end + start) / 2
        boundaries.append(max(boundaries[-1] + 0.05 * width, boundary))
    boundaries.append(right)
    widths = [max(5, min(100, round((b - a) / width * 100, 2))) for a, b in itertools.pairwise(boundaries)]
    if aligns[-1] == "right" and columns[-1]:
        # Right-aligned last column: its text ends a padding before the table's right edge.
        padding_mm = max(padding_mm, min(12.0, right - max(c["x_mm"] + c["width_mm"] for c in columns[-1])))
    sizes = sorted(c["size_pt"] for row in rows for c in row)
    size_pt = sizes[len(sizes) // 2]
    baselines = [row[0]["y_mm"] for row in rows]
    pitches = sorted(b - a for a, b in itertools.pairwise(baselines))
    pitch_mm = pitches[len(pitches) // 2] if pitches else 1.4 * size_pt * PT_TO_MM
    header_box = None
    for graphic in page["graphics"]:
        box = graphic["box_mm"]
        if graphic["kind"] == "filled-box" and box[0] <= rows[0][0]["x_mm"] + 1 and box[1] - 2 <= baselines[0] <= box[3] + 2:
            header_box = graphic
    header = header_box is not None or all(c["bold"] for c in rows[0])
    body = rows[1:] if header else rows
    rules = [g for g in page["graphics"] if g["kind"] == "rule" and g["box_mm"][3] - g["box_mm"][1] < 1.0
             and baselines[0] - 2 <= g["box_mm"][1] <= baselines[-1] + pitch_mm]
    cell_index = {id(c): i for i, cells in enumerate(columns) for c in cells}
    static_rows = []
    for row in body:
        values = [""] * count
        for cell in row:
            values[cell_index[id(cell)]] = cell["text"].replace("\t", " ")
        while values and values[-1] == "":
            values.pop()
        static_rows.append(values or [""])
    header_cells = [""] * count
    if header:
        for cell in rows[0]:
            header_cells[cell_index[id(cell)]] = cell["text"].replace("\t", " ")
    block: dict[str, Any] = {
        "type": "table", "data_mode": "static", "show_header": header,
        "columns": [{"header": header_cells[i][:200], "format": "text", "width": widths[i], "align": aligns[i]}
                    for i in range(count)],
        "static_rows": static_rows,
        "font_family": FONT_STACKS[rows[0][0]["family_class"]],
        "font_size": round(size_pt * 4 / 3, 2),
        "header_bold": all(c["bold"] for c in rows[0]) if header else True,
        "borders": "horizontal" if len(rules) >= max(1, len(body) - 1) else "none",
        "cell_padding_x": _px(padding_mm), "cell_padding_y": 0,
        "row_height": _px(pitch_mm),
    }
    if header_box is not None and header_box.get("fill"):
        block["header_background"] = header_box["fill"]
    header_mm = pitch_mm
    # A cell's baseline sits about half a row plus 0.35 em below the row top (vertically centred line box).
    half_em = 0.35 * size_pt * PT_TO_MM
    top = baselines[0] - pitch_mm / 2 - half_em
    spacing_mm = 0.0
    if header and header_box is not None:
        # The shaded bar gives the header row its own height, often shorter than the body pitch (DD-442). When
        # the first body row starts below the bar, the space between them is header_spacing_after (DD-445).
        top = header_box["box_mm"][1]
        header_mm = header_box["box_mm"][3] - top
        block["header_row_height"] = round(max(1.0, min(400.0, _px(header_mm))), 2)
        if len(rows) >= 2:
            body_top = baselines[1] - pitch_mm / 2 - half_em
            if body_top - top - header_mm > 0.5:
                spacing_mm = min(_px(body_top - top - header_mm), 240.0) / MM_TO_PX
                block["header_spacing_after"] = round(_px(spacing_mm), 2)
    elif header:
        top = baselines[0] - header_mm / 2 - half_em
    if block["borders"] == "horizontal":
        thickness = sorted(r["box_mm"][3] - r["box_mm"][1] for r in rules)[len(rules) // 2]
        block["border_width"] = max(0.0, min(4.0, round(_px(thickness), 2))) or 0.5
        block["border_color"] = rules[0].get("fill") or "#000000"
    bottom = top + header_mm + spacing_mm + pitch_mm * (len(rows) - 1)
    # A body row whose cells are all bold while others are not (a totals row) becomes a row style (DD-448).
    bold_rows = [index for index, row in enumerate(body) if all(c["bold"] for c in row)] if any(
        not all(c["bold"] for c in row) for row in body) else []
    if bold_rows:
        block["row_styles"] = [{"row": index, "bold": True} for index in bold_rows[:MAX_ROW_STYLES]]
    block["_unstyled_bold_rows"] = max(0, len(bold_rows) - MAX_ROW_STYLES)
    used = ([header_box["box_mm"]] if header_box is not None else []) + \
        ([r["box_mm"] for r in rules] if block["borders"] == "horizontal" else [])
    return block, top, bottom, used


def _map_shapes(model: dict[str, Any], by_feature: dict[str, list[dict[str, Any]]], page_settings: dict[str, Any],
                used: set[tuple[int, tuple[float, ...]]], blocks: list[dict[str, Any]], provenance: list[dict[str, Any]],
                effort: dict[str, Any], gap: Any) -> None:
    """Express source rules and boxes as shape blocks positioned in the content area (DD-434).

    Filled rules become lines of the rule's thickness and colour; stroked paths become lines centred on the
    path; filled boxes become rectangles behind text; stroked boxes become outlined rectangles. Graphics used
    by a table, and diagonal segments, are skipped. Shapes outside the content area (which page-owned
    surfaces clip) are recorded as gaps.
    """
    detection_by_box = {(d["page"], tuple(d["box_mm"])): d for feature in ("graphic.rule", "graphic.box")
                        for d in by_feature.get(feature, [])}
    left, top = page_settings["margin_left_mm"], page_settings["margin_top_mm"]
    for page in model["pages"]:
        number = page["page_number"]
        right = page["width_mm"] - page_settings["margin_right_mm"]
        bottom = page["height_mm"] - page_settings["margin_bottom_mm"]
        for graphic in page["graphics"]:
            kind, box = graphic["kind"], graphic["box_mm"]
            if kind not in {"rule", "box", "filled-box"} or (number, tuple(box)) in used:
                continue
            detection = detection_by_box.get((number, tuple(box)))
            thickness_mm = max(0.05, graphic.get("thickness_pt", 0.75) * PT_TO_MM)
            x0, y0, x1, y1 = box
            stroked = not graphic["filled"]
            if stroked:  # strokes are centred on the path
                x0, y0, x1, y1 = x0 - thickness_mm / 2, y0 - thickness_mm / 2, x1 + thickness_mm / 2, y1 + thickness_mm / 2
            if x0 < left - 0.5 or y0 < top - 0.5 or x1 > right + 0.5 or y1 > bottom + 0.5:
                if detection:
                    gap(detection["feature"], "value-out-of-range", "shape", "position_y",
                        "shape lies in a page-margin area, which page-owned surfaces clip", detection["id"])
                continue
            color = (graphic.get("stroke") if stroked else graphic.get("fill")) or "#000000"
            shape: dict[str, Any] = {"type": "shape", "position_mode": "absolute", "position_unit": "mm",
                                     "position_x": round(max(0.0, x0 - left), 2), "position_y": round(max(0.0, y0 - top), 2),
                                     "page_number": number}
            if kind == "rule":
                horizontal = (box[2] - box[0]) >= (box[3] - box[1])
                shape.update({"shape": "line", "orientation": "horizontal" if horizontal else "vertical",
                              "stroke_color": color, "stroke_width": round(min(10.0, thickness_mm * MM_TO_PX), 2)})
                shape["width_mm" if horizontal else "height_mm"] = round(max(0.1, (x1 - x0) if horizontal else (y1 - y0)), 2)
            else:
                shape.update({"shape": "rectangle", "width_mm": round(max(0.1, x1 - x0), 2),
                              "height_mm": round(max(0.1, y1 - y0), 2)})
                if stroked:
                    shape.update({"stroke_color": color, "stroke_width": round(min(10.0, thickness_mm * MM_TO_PX), 2),
                                  "layer": "front"})
                else:
                    shape.update({"fill_color": color, "stroke_width": 0, "layer": "behind"})
            blocks.append(shape)
            provenance.append({"block": len(blocks) - 1, "page": number, "lines": [], "box_mm": box,
                               "detections": [detection["id"]] if detection else []})
            effort["shapes"] += 1


def validate_reconstruction(reconstruction: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Return violations of the editor-reachable contract; an empty list means the reconstruction is admissible."""
    violations: list[str] = []
    if reconstruction.get("contract") != RECONSTRUCTION_VERSION:
        violations.append(f"contract must be {RECONSTRUCTION_VERSION}")
    definition = reconstruction.get("definition")
    if not isinstance(definition, dict):
        return [*violations, "definition must be an object"]
    components = manifest["components"]

    def check(path: str, value: Any, spec: dict[str, Any]) -> None:
        if spec.get("ui") == "none":
            violations.append(f"{path}: not reachable from the editor (ui=none)")
        if spec.get("fidelity") == "excluded":
            violations.append(f"{path}: excluded from fidelity reconstruction")
        kind = spec.get("type")
        if kind in {"number", "integer"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                violations.append(f"{path}: expected a number")
            elif kind == "integer" and value != int(value):
                violations.append(f"{path}: expected a whole number")
            elif "range" in spec and not spec["range"][0] <= value <= spec["range"][1]:
                violations.append(f"{path}: {value} outside {spec['range']}")
        elif kind == "enum" and value not in spec.get("values", []):
            violations.append(f"{path}: {value!r} not in {spec.get('values')}")
        elif kind == "boolean" and not isinstance(value, bool):
            violations.append(f"{path}: expected a boolean")
        elif kind == "array" and isinstance(value, list):
            if "max_items" in spec and len(value) > spec["max_items"]:
                violations.append(f"{path}: more than {spec['max_items']} items")
            for item in value:
                if spec.get("item") == "tab-stop" and isinstance(item, dict):
                    allowed = spec["item_properties"]
                    if set(item) - set(allowed):
                        violations.append(f"{path}: unknown tab-stop keys {sorted(set(item) - set(allowed))}")
                    for key in ("align", "leader"):
                        if key in item and item[key] not in allowed[key]:
                            violations.append(f"{path}: tab-stop {key} {item[key]!r} not in {allowed[key]}")
                    item = item.get("position")
                elif isinstance(item, dict) and isinstance(spec.get("item_properties"), dict):
                    if set(item) - set(spec["item_properties"]):
                        violations.append(f"{path}: unknown item keys {sorted(set(item) - set(spec['item_properties']))}")
                    continue
                if "range" in spec and (isinstance(item, bool) or not isinstance(item, (int, float))
                                        or not spec["range"][0] <= item <= spec["range"][1]):
                    violations.append(f"{path}: item {item} outside {spec['range']}")

    page = definition.get("page", {})
    for key, value in page.items():
        spec = manifest["page"]["properties"].get(key)
        if spec is None:
            violations.append(f"page.{key}: not in the capability manifest")
        else:
            check(f"page.{key}", value, spec)
    for key in definition:
        if key not in {"name", "page", "blocks", "sample_data", *manifest["definition"]["properties"]}:
            violations.append(f"definition.{key}: not in the capability manifest")
    for index, block in enumerate(definition.get("blocks", [])):
        kind = block.get("type", "text")
        component = components.get(kind)
        if component is None:
            violations.append(f"blocks[{index}]: unknown component {kind!r}")
            continue
        for key, value in block.items():
            if key == "type":
                continue
            spec = component["properties"].get(key)
            if spec is None:
                violations.append(f"blocks[{index}].{key}: not a {kind} property in the capability manifest")
                continue
            check(f"blocks[{index}].{key}", value, spec)
        if kind == "rich_text":
            for p_index, paragraph in enumerate(block.get("paragraphs", [])):
                for key, value in paragraph.items():
                    spec = component["paragraph_properties"].get(key)
                    if spec is None:
                        violations.append(f"blocks[{index}].paragraphs[{p_index}].{key}: not in the manifest")
                    elif key != "runs":
                        check(f"blocks[{index}].paragraphs[{p_index}].{key}", value, spec)
                for r_index, run in enumerate(paragraph.get("runs", [])):
                    run_spec = component["run_types"].get(run.get("type", "text"))
                    if run_spec is None:
                        violations.append(f"blocks[{index}] run {r_index}: unknown run type")
                        continue
                    style_props = run_spec.get("style", {}).get("properties", {})
                    for key, value in (run.get("style") or {}).items():
                        if key not in style_props:
                            violations.append(f"blocks[{index}] run {r_index}.style.{key}: not in the manifest")
                        else:
                            check(f"blocks[{index}] run {r_index}.style.{key}", value, style_props[key])
    for entry in reconstruction.get("gaps", []):
        if entry.get("reason") not in REASON_CODES:
            violations.append(f"gap {entry.get('feature')}: unknown reason {entry.get('reason')!r}")
        if entry.get("feature") not in FEATURES:
            violations.append(f"gap: unknown feature {entry.get('feature')!r}")
    return violations


def _row_split(page: dict[str, Any], paragraph: dict[str, Any]) -> tuple[list[int], list[int]] | None:
    """Split a one-row paragraph whose segments are unlike blocks side by side, or return None.

    The row splits at its widest horizontal gap (at least SIDE_GAP_MM). The halves are separate blocks when
    their largest sizes or first baselines differ, as with a large title beside smaller details; a tabbed
    line or a table row shares one size and baseline and is left alone.
    """
    if len(paragraph["rows"]) != 1 or len(paragraph["rows"][0]) < 2:
        return None
    row = paragraph["rows"][0]
    lines = [page["lines"][i] for i in row]
    width, cut = max((b["x_mm"] - a["x_mm"] - a["width_mm"], k) for k, (a, b) in enumerate(itertools.pairwise(lines), 1))
    if width < SIDE_GAP_MM:
        return None
    left, right = lines[:cut], lines[cut:]
    unlike = (abs(max(line["size_pt"] for line in left) - max(line["size_pt"] for line in right)) > SIDE_SIZE_PT
              or abs(left[0]["y_mm"] - right[0]["y_mm"]) > SIDE_BASELINE_MM)
    return (row[:cut], row[cut:]) if unlike else None


def _side_by_side(page: dict[str, Any], paragraphs: list[dict[str, Any]], body_line_height: float,
                  content_right: float) -> list[tuple[str, Any]]:
    """Wrap side-by-side blocks (a title on the left, details on the right) in a two-column section (DD-443).

    A user builds a letterhead with a column section: the left block, a column break, then the right block.
    The section starts at a row that ``_row_split`` divides, and grows with following paragraphs that sit
    wholly on one side and close below that side's last block; right-hand lines sharing a right edge are
    right-aligned.
    """
    items: list[tuple[str, Any]] = []

    def part(rows: list[int]) -> dict[str, Any]:
        sub = {"rows": [list(rows)]}
        _describe(page, sub)
        return sub

    def top(p: dict[str, Any]) -> float:
        return page["lines"][p["rows"][0][0]]["y_mm"] - _paragraph_metrics(page, p, body_line_height)[2]

    index = 0
    while index < len(paragraphs):
        seed = paragraphs[index]
        index += 1
        split = _row_split(page, seed)
        if split is None:
            items.append(("para", seed))
            continue
        left, right = [part(split[0])], [part(split[1])]
        at = (left[0]["right_mm"] + right[0]["first_left_mm"]) / 2
        while index < len(paragraphs):
            candidate = paragraphs[index]
            side = (left if candidate["right_mm"] <= at
                    else right if min(candidate["left_mm"], candidate["first_left_mm"]) >= at else None)
            if side is None or candidate["box_mm"][1] - side[-1]["box_mm"][3] > max(2.0, candidate["size_pt"] * PT_TO_MM):
                break
            side.append(candidate)
            index += 1
        rights = [p["right_mm"] for p in right]
        if max(rights) - min(rights) <= 1.0 and (len({round(p["first_left_mm"]) for p in right}) > 1
                                                 or max(rights) >= content_right - 1.0):
            right = [dict(p, align_hint="right") for p in right]
        left_edge = max(p["right_mm"] for p in left)
        right_edge = min(min(p["left_mm"], p["first_left_mm"]) for p in right)
        at, gap = (left_edge + right_edge) / 2, min(SIDE_COLUMN_GAP_MM, right_edge - left_edge)
        info = {"top": min(top(p) for p in left + right), "left_right": at - gap / 2, "right_left": at + gap / 2}
        items += ([("start", info)] + [("para", p) for p in left] + [("break", info)]
                  + [("para", p) for p in right] + [("end", info)])
    return items
