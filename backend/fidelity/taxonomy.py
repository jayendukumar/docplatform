"""Fixed document-feature taxonomy and detectors (E16-03, DD-421).

Detectors read a SourceModel (``source-model-v2``) and emit evidence-bearing
detections. Paragraph segmentation is shared with the reconstruction mapper so
that detections and template blocks refer to the same source lines.

A detection is ``{"id", "feature", "page", "box_mm", "lines", "evidence"}``.
``lines`` are ``[page, line_index]`` references into the SourceModel.
"""
from __future__ import annotations

import itertools
import re
import statistics
from collections import Counter
from typing import Any

TAXONOMY_VERSION = "fidelity-taxonomy-v1"
PT_TO_MM = 25.4 / 72

# Gap reason codes. The first five are editor findings; the last is a harness limitation.
REASON_CODES = {
    "missing-component": "No editor component can express the feature.",
    "missing-property": "The component exists but lacks a property for the feature.",
    "value-out-of-range": "The property exists but the needed value is outside its bounds.",
    "value-precision-loss": "The property exists but its granularity cannot represent the value exactly.",
    "ui-unreachable": "The renderer supports it but the editor cannot set it.",
    "workaround-used": "Expressed only through an approximation that a user would find unnatural.",
    "harness-limitation": "The reconstruction mapper does not attempt the feature yet; not an editor finding.",
}

FEATURES = {
    "page.size": "Physical page size",
    "page.margins": "Content-area margins",
    "page.running_header": "Text repeated in the top band of most pages",
    "page.running_footer": "Text repeated in the bottom band of most pages",
    "page.page_number": "Sequential page number in a header or footer band",
    "text.paragraph": "Multi-line flowing paragraph",
    "text.heading": "Short line larger or bolder than body text",
    "text.decimal_size": "Font size not expressible in whole CSS pixels",
    "text.mixed_inline_style": "Bold, italic or size change inside one paragraph",
    "text.align_justify": "Justified paragraph (flush left and right)",
    "text.align_center": "Centred line or paragraph",
    "text.align_right": "Right-aligned line or paragraph",
    "text.first_line_indent": "First line indented relative to following lines",
    "text.hanging_indent": "Following lines indented relative to the first",
    "list.numbered_label": "Clause or list label followed by a tab gap, e.g. '1.', '(a)', '(iii)'",
    "tab.positioned_gap": "Text segments on one baseline separated by a tab-like gap",
    "tab.dot_leader": "Run of dots or underscores used as a leader or fill-in line",
    "table.grid": "Rows of segments aligned on shared column positions",
    "graphic.rule": "Vector horizontal or vertical rule",
    "graphic.box": "Vector rectangle (stroked or filled)",
    "image.raster": "Raster image",
    "layout.columns": "Two or more text columns on a page",
    "form.signature_block": "Signature/execution block labels (By, Name, Title, Date)",
}

_LABEL = re.compile(r"^(\(?[0-9]{1,3}[.)]|\([a-z]{1,2}\)|\([ivxl]{1,6}\)|\([A-Z]\)|[A-Z][.)]|Section\s+\d+[.:]?|Part\s+\d+[.:]?)$")
_LEADER = re.compile(r"(\.{5,}|_{5,}|…{3,})")
_SIGNATURE = re.compile(r"^(By|Name|Title|Date|Signature)\s*:", re.IGNORECASE)
_DIGITS = re.compile(r"\d+")


def _line_box(line: dict[str, Any]) -> list[float]:
    size_mm = line["size_pt"] * PT_TO_MM
    return [line["x_mm"], round(line["y_mm"] - 0.8 * size_mm, 3), round(line["x_mm"] + line["width_mm"], 3),
            round(line["y_mm"] + 0.25 * size_mm, 3)]


def _union(boxes: list[list[float]]) -> list[float]:
    return [round(min(b[0] for b in boxes), 2), round(min(b[1] for b in boxes), 2),
            round(max(b[2] for b in boxes), 2), round(max(b[3] for b in boxes), 2)]


def body_size(model: dict[str, Any]) -> float:
    weights: Counter[float] = Counter()
    for page in model["pages"]:
        for line in page["lines"]:
            weights[round(line["size_pt"], 1)] += len(line["text"])
    return weights.most_common(1)[0][0] if weights else 10.0


def furniture_lines(model: dict[str, Any], band_mm: float = 25.0) -> dict[str, set[tuple[int, int]]]:
    """Lines in top/bottom bands whose digit-normalised text recurs on at least half the pages."""
    result: dict[str, set[tuple[int, int]]] = {"header": set(), "footer": set(), "page_number": set()}
    pages = model["pages"]
    if len(pages) < 3:
        return result
    for band in ("header", "footer"):
        texts: Counter[str] = Counter()
        members: dict[str, list[tuple[int, int]]] = {}
        for page in pages:
            seen = set()
            for index, line in enumerate(page["lines"]):
                in_band = line["y_mm"] <= band_mm if band == "header" else line["y_mm"] >= page["height_mm"] - band_mm
                if not in_band:
                    continue
                key = _DIGITS.sub("#", line["text"].strip())
                if key in seen:
                    continue
                seen.add(key)
                texts[key] += 1
                members.setdefault(key, []).append((page["page_number"], index))
        for key, count in texts.items():
            if count >= max(3, len(pages) // 2):
                page_label = re.search(r"\bpage\s*#(\s*of\s*#)?\s*$", key.strip(), re.IGNORECASE)
                target = "page_number" if key.strip("# ") == "" or page_label else band
                result[target].update(members[key])
    return result


def segment_paragraphs(page: dict[str, Any], skip: set[tuple[int, int]], body_pt: float) -> list[dict[str, Any]]:
    """Group a page's lines into paragraphs: consecutive rows, steady pitch, compatible left edges."""
    rows: list[list[int]] = []
    ordered = sorted(range(len(page["lines"])), key=lambda i: (page["lines"][i].get("column", 0),
                                                                page["lines"][i]["y_mm"], page["lines"][i]["x_mm"]))
    for index in ordered:
        line = page["lines"][index]
        if (page["page_number"], index) in skip:
            continue
        same_column = rows and page["lines"][rows[-1][0]].get("column", 0) == line.get("column", 0)
        if same_column and abs(page["lines"][rows[-1][0]]["y_mm"] - line["y_mm"]) < 0.3 * line["size_pt"] * PT_TO_MM:
            rows[-1].append(index)
        else:
            rows.append([index])
    for row in rows:  # segments sharing a row read left to right, whatever their baseline order
        row.sort(key=lambda i: page["lines"][i]["x_mm"])
    paragraphs: list[dict[str, Any]] = []
    current: list[list[int]] = []
    # Column content edges: a line ending more than a quarter of the column width before the right edge is a
    # hard line break (address blocks, signature lines), not a wrapped line of the same paragraph.
    column_edges: dict[int, tuple[float, float]] = {}
    for column in {line.get("column", 0) for line in page["lines"]}:
        members = [line for line in page["lines"] if line.get("column", 0) == column]
        lefts = sorted(line["x_mm"] for line in members)
        rights = sorted(line["x_mm"] + line["width_mm"] for line in members)
        column_edges[column] = (lefts[len(lefts) // 10], rights[min(len(rights) - 1, (9 * len(rights)) // 10)])

    def close() -> None:
        if current:
            paragraphs.append({"rows": [list(r) for r in current]})
            current.clear()

    for row in rows:
        first = page["lines"][row[0]]
        if not current:
            current.append(row)
            continue
        previous = page["lines"][current[-1][0]]
        pitch = first["y_mm"] - previous["y_mm"]
        expected = 1.35 * max(previous["size_pt"], first["size_pt"]) * PT_TO_MM
        if len(current) >= 2:
            last_pitch = previous["y_mm"] - page["lines"][current[-2][0]]["y_mm"]
            expected = min(expected, last_pitch * 1.25)
        same_style = abs(first["size_pt"] - previous["size_pt"]) < 0.6
        heading_like = len(row) == 1 and first["bold"] and len(first["text"]) < 80 and first["size_pt"] >= body_pt
        # A row with several segments (label + text, or a table row) starts a new paragraph; single-segment
        # rows may continue it. "Short" compares the previous row's last segment with the paragraph's right edge.
        previous_end = page["lines"][current[-1][-1]]
        previous_right = previous_end["x_mm"] + previous_end["width_mm"]
        left_edge, right_edge = column_edges[previous.get("column", 0)]
        previous_short = (previous_right < _right_edge(page, current) - 4 * PT_TO_MM * previous["size_pt"]
                          or previous_right < right_edge - 0.25 * (right_edge - left_edge))
        column_change = first.get("column", 0) != previous.get("column", 0)
        # A wrapped continuation starts where the paragraph's text starts: under the first line (allowing a
        # first-line indent of up to 25 mm), at a tab/segment position of the first line (hanging indent),
        # or under the previous continuation line.
        # Segment anchors apply only to a label + text opening row: under a row of three or more segments
        # (a tabular or form-header row), a line below one segment is a wrapped cell, not a continuation (DD-449).
        opening = [page["lines"][i] for i in current[0]]
        anchors = [opening[0]["x_mm"]] + ([line["x_mm"] for line in opening[1:]] if len(opening) <= 2 else [])             + list(opening[0].get("tabs_mm", []))
        if len(current) > 1:
            anchors = [page["lines"][current[-1][0]]["x_mm"]]
        x = first["x_mm"]
        continues_left = (any(abs(x - anchor) <= 3.0 for anchor in anchors)
                          or (len(current) == 1 and opening[0]["x_mm"] - 25.0 <= x <= opening[0]["x_mm"]))
        if column_change or pitch > expected or not same_style or len(row) > 1 or heading_like or previous_short \
                or not continues_left:
            close()
        current.append(row)
    close()
    for paragraph in paragraphs:
        _describe(page, paragraph)
    return paragraphs


def _right_edge(page: dict[str, Any], rows: list[list[int]]) -> float:
    return max(page["lines"][r[-1]]["x_mm"] + page["lines"][r[-1]]["width_mm"] for r in rows)


def _describe(page: dict[str, Any], paragraph: dict[str, Any]) -> None:
    lines = [page["lines"][i] for row in paragraph["rows"] for i in row]
    firsts = [page["lines"][row[0]] for row in paragraph["rows"]]
    pitches = [b["y_mm"] - a["y_mm"] for a, b in itertools.pairwise(firsts)]
    lefts = [line["x_mm"] for line in firsts]
    rights = [page["lines"][row[-1]]["x_mm"] + page["lines"][row[-1]]["width_mm"] for row in paragraph["rows"]]
    paragraph.update({
        "lines": [[page["page_number"], i] for row in paragraph["rows"] for i in row],
        "box_mm": _union([_line_box(line) for line in lines]),
        "size_pt": statistics.median(line["size_pt"] for line in lines),
        "pitch_mm": statistics.median(pitches) if pitches else None,
        "left_mm": statistics.median(lefts[1:]) if len(lefts) > 1 else lefts[0],
        "first_left_mm": lefts[0],
        "right_mm": max(rights),
        "rights_mm": rights,
        "bold": all(line["bold"] for line in lines),
        "italic": all(line["italic"] for line in lines),
        "mixed_style": len({(run["bold"], run["italic"], round(run["size_pt"], 1))
                            for line in lines for run in line.get("runs", [line])}) > 1,
        "segments": max(len(row) for row in paragraph["rows"]),
    })


def detect_features(model: dict[str, Any]) -> dict[str, Any]:
    """Return furniture, per-page paragraphs and feature detections for a SourceModel."""
    detections: list[dict[str, Any]] = []
    body_pt = body_size(model)
    furniture = furniture_lines(model)
    skip = set().union(*furniture.values())

    def add(feature: str, page: int, box: list[float], lines: list[list[int]] | None = None, **evidence: Any) -> None:
        detections.append({"id": f"d{len(detections) + 1}", "feature": feature, "page": page, "box_mm": box,
                           "lines": lines or [], "evidence": evidence})

    first = model["pages"][0] if model["pages"] else None
    if first:
        add("page.size", 1, [0, 0, first["width_mm"], first["height_mm"]],
            width_mm=first["width_mm"], height_mm=first["height_mm"])
    for kind, feature in (("header", "page.running_header"), ("footer", "page.running_footer"),
                          ("page_number", "page.page_number")):
        by_page: dict[int, list[int]] = {}
        for page_number, index in furniture[kind]:
            by_page.setdefault(page_number, []).append(index)
        for page_number, indexes in sorted(by_page.items()):
            page = model["pages"][page_number - 1]
            add(feature, page_number, _union([_line_box(page["lines"][i]) for i in indexes]),
                [[page_number, i] for i in indexes], text=" | ".join(page["lines"][i]["text"] for i in indexes)[:200])

    paragraphs_by_page: dict[int, list[dict[str, Any]]] = {}
    lefts: list[float] = []
    rights: list[float] = []
    tops: list[float] = []
    bottoms: list[float] = []
    for page in model["pages"]:
        number = page["page_number"]
        paragraphs = segment_paragraphs(page, skip, body_pt)
        paragraphs_by_page[number] = paragraphs
        if paragraphs:
            lefts.extend(p["left_mm"] for p in paragraphs)
            rights.extend(p["right_mm"] for p in paragraphs)
            # Rules and boxes in the page body are content too (DD-434): a rule wider than the text widens the
            # content area so its shape is not clipped. Header/footer bands (outer 25 mm) are excluded.
            body_graphics = [g["box_mm"] for g in page["graphics"] if g["kind"] in {"rule", "box", "filled-box"}
                             and g["box_mm"][1] > 25 and g["box_mm"][3] < page["height_mm"] - 25]
            lefts.extend(box[0] for box in body_graphics)
            rights.extend(box[2] for box in body_graphics)
            tops.append(min(p["box_mm"][1] for p in paragraphs))
            bottoms.append(max(p["box_mm"][3] for p in paragraphs))
        content_left = min((p["left_mm"] for p in paragraphs), default=0)
        content_right = max((p["right_mm"] for p in paragraphs), default=page["width_mm"])
        center = (content_left + content_right) / 2
        for paragraph in paragraphs:
            box, refs = paragraph["box_mm"], paragraph["lines"]
            rows = len(paragraph["rows"])
            text_lines = [page["lines"][i] for row in paragraph["rows"] for i in row]
            if rows >= 2:
                add("text.paragraph", number, box, refs, rows=rows, pitch_mm=round(paragraph["pitch_mm"], 3))
            if rows >= 3 and max(paragraph["rights_mm"][:-1]) - min(paragraph["rights_mm"][:-1]) < 1.0:
                add("text.align_justify", number, box, refs, right_mm=round(paragraph["right_mm"], 2))
            if rows <= 2 and abs((box[0] + box[2]) / 2 - center) < 3 and box[0] > content_left + 10:
                add("text.align_center", number, box, refs)
            elif rows <= 2 and abs(box[2] - content_right) < 2 and box[0] > content_left + 40:
                add("text.align_right", number, box, refs)
            if rows >= 2 and paragraph["first_left_mm"] - paragraph["left_mm"] > 1.5:
                add("text.first_line_indent", number, box, refs,
                    indent_mm=round(paragraph["first_left_mm"] - paragraph["left_mm"], 2))
            if rows >= 2 and paragraph["left_mm"] - paragraph["first_left_mm"] > 1.5:
                add("text.hanging_indent", number, box, refs,
                    indent_mm=round(paragraph["left_mm"] - paragraph["first_left_mm"], 2))
            if paragraph["mixed_style"]:
                add("text.mixed_inline_style", number, box, refs)
            if rows == 1 and len(text_lines) == 1 and len(text_lines[0]["text"]) < 80 and (
                    text_lines[0]["size_pt"] > body_pt + 1 or (text_lines[0]["bold"] and not paragraph["mixed_style"])):
                add("text.heading", number, box, refs, size_pt=text_lines[0]["size_pt"])
            size_px = paragraph["size_pt"] * 4 / 3
            if abs(size_px - round(size_px)) > 0.15:
                add("text.decimal_size", number, box, refs, size_pt=paragraph["size_pt"], size_px=round(size_px, 2))
            for row in paragraph["rows"]:
                first_line = page["lines"][row[0]]
                if len(row) == 1 and first_line.get("tabs_mm"):
                    head = first_line["text"].split("\t", 1)[0].strip()
                    row_refs = [[number, row[0]]]
                    if _LABEL.match(head):
                        add("list.numbered_label", number, _line_box(first_line), row_refs, label=head,
                            gap_mm=round(first_line["tabs_mm"][0] - first_line["x_mm"], 2))
                    else:
                        add("tab.positioned_gap", number, _line_box(first_line), row_refs,
                            stops_mm=[round(x, 2) for x in first_line["tabs_mm"]])
                if len(row) > 1:
                    first_line = page["lines"][row[0]]
                    row_refs = [[number, i] for i in row]
                    row_box = _union([_line_box(page["lines"][i]) for i in row])
                    if _LABEL.match(first_line["text"].strip()):
                        add("list.numbered_label", number, row_box, row_refs, label=first_line["text"].strip(),
                            gap_mm=round(page["lines"][row[1]]["x_mm"] - first_line["x_mm"], 2))
                    else:
                        add("tab.positioned_gap", number, row_box, row_refs,
                            stops_mm=[round(page["lines"][i]["x_mm"], 2) for i in row])
            for line_index in (i for row in paragraph["rows"] for i in row):
                line = page["lines"][line_index]
                if _LEADER.search(line["text"]):
                    add("tab.dot_leader", number, _line_box(line), [[number, line_index]],
                        leader=_LEADER.search(line["text"]).group()[:12])
                if _SIGNATURE.match(line["text"].strip()):
                    add("form.signature_block", number, _line_box(line), [[number, line_index]], label=line["text"][:40])
        _detect_tables(page, paragraphs, add)
        _detect_columns(page, paragraphs, add)
        for graphic in page["graphics"]:
            if graphic["kind"] == "rule":
                add("graphic.rule", number, graphic["box_mm"])
            elif graphic["kind"] in {"box", "filled-box"}:
                add("graphic.box", number, graphic["box_mm"], filled=graphic["filled"])
        for image in page["images"]:
            add("image.raster", number, image["box_mm"])

    if lefts and first:
        margins = {"left": round(_percentile(lefts, 0.1), 2), "top": round(_percentile(tops, 0.1), 2),
                   "right": round(first["width_mm"] - _percentile(rights, 0.9), 2),
                   "bottom": round(first["height_mm"] - _percentile(bottoms, 0.9), 2)}
        # Space below the last line of short pages is not a margin: when body text never comes near the
        # bottom of the page, the bottom margin is unconstrained and mirrors the top margin.
        margins["bottom_constrained"] = margins["bottom"] <= max(margins["top"], 40.0)
        if not margins["bottom_constrained"]:
            margins["bottom"] = margins["top"]
        add("page.margins", 1, [0, 0, first["width_mm"], first["height_mm"]], **margins)
    return {"contract": TAXONOMY_VERSION, "body_size_pt": body_pt,
            "furniture": {k: sorted([list(x) for x in v]) for k, v in furniture.items()},
            "paragraphs": paragraphs_by_page, "detections": detections,
            "summary": dict(Counter(d["feature"] for d in detections))}


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(fraction * len(ordered))))]


def _aligned(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Cells share a column when their left or right edges align within 2 mm."""
    return abs(a["x_mm"] - b["x_mm"]) < 2.0 or abs(a["x_mm"] + a["width_mm"] - b["x_mm"] - b["width_mm"]) < 2.0


def _detect_tables(page: dict[str, Any], paragraphs: list[dict[str, Any]], add: Any) -> None:
    run: list[list[int]] = []

    def flush() -> None:
        if len(run) >= 3:
            refs = [[page["page_number"], i] for row in run for i in row]
            box = _union([_line_box(page["lines"][i]) for row in run for i in row])
            columns = sorted({round(page["lines"][i]["x_mm"]) for i in run[0]})
            add("table.grid", page["page_number"], box, refs, rows=len(run), columns_mm=columns)
        run.clear()

    rows = [row for paragraph in paragraphs for row in paragraph["rows"]]
    for row in rows:
        if len(row) >= 2 and (not run or (len(run[0]) == len(row) and all(
                _aligned(page["lines"][a], page["lines"][b]) for a, b in zip(row, run[0], strict=True)))):
            run.append(row)
        else:
            flush()
            if len(row) >= 2:
                run.append(row)
    flush()


def _detect_columns(page: dict[str, Any], paragraphs: list[dict[str, Any]], add: Any) -> None:
    if page.get("gutter_mm") is None:
        return
    right = [p for p in paragraphs if any(page["lines"][i].get("column", 0) == 1 for row in p["rows"] for i in row)]
    left = [p for p in paragraphs if p not in right and p["right_mm"] <= page["gutter_mm"]]
    if right and left:
        add("layout.columns", page["page_number"], _union([p["box_mm"] for p in left + right]),
            [ref for p in left + right for ref in p["lines"]], columns=2, gutter_mm=page["gutter_mm"])
