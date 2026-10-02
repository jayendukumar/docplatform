"""Attribute comparison results to features, blocks and causes; rank editor gaps (E16-07, E16-08, DD-421).

Attribution works at three levels:

1. **Global checks** catch document-wide renderer behaviour, e.g. a page-count
   mismatch (pagination) or missing running furniture, which would otherwise
   be blamed on whatever feature happens to overlap every region.
2. **Feature evidence** follows each source word through the word alignment.
   For every gap group (and every feature) it reports how many of its words
   were found, how many landed on the right page, and their horizontal and
   vertical displacement, next to a control group of words outside any editor
   gap. Horizontal displacement is robust to pagination errors.
3. **Region findings** classify each text difference and visual worst cell:
   ``pagination``, ``vertical-drift``, ``horizontal-drift``, ``content-lost-in-render``,
   ``text-mismatch``, ``not-reconstructed`` or ``extra-content``, listing overlapping
   gaps as possible contributors.

Causes are hypotheses for a reviewer, not proofs.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

ATTRIBUTION_VERSION = "fidelity-attribution-v2"
EDITOR_REASONS = {"missing-component", "missing-property", "value-out-of-range", "value-precision-loss",
                  "ui-unreachable", "workaround-used"}
NEAR_MM = 3.0


def _overlaps(a: list[float], b: list[float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def _evidence(words: set[tuple[int, int]], matches: dict[tuple[int, int], dict[str, Any]]) -> dict[str, Any]:
    found = [matches[w] for w in words if w in matches]
    same_page = [m for m in found if m["source_page"] == m["candidate_page"]]
    return {"words": len(words),
            "found_rate": round(len(found) / len(words), 4) if words else None,
            "same_page_rate": round(len(same_page) / len(found), 4) if found else None,
            "median_abs_dx_mm": _median([abs(m["dx_mm"]) for m in found]),
            "median_abs_dy_mm_same_page": _median([abs(m["dy_mm"]) for m in same_page]),
            "dx_within_3mm": round(sum(abs(m["dx_mm"]) <= NEAR_MM for m in found) / len(found), 4) if found else None,
            "median_abs_size_delta_pt": _median([abs(m["size_delta_pt"]) for m in found])}


def attribute(model: dict[str, Any], features: dict[str, Any], reconstruction: dict[str, Any],
              comparison: dict[str, Any], visual: dict[str, Any] | None) -> dict[str, Any]:
    detections = {d["id"]: d for d in features["detections"]}
    matches = {(m["source_page"], m["source_index"]): m for m in comparison.get("matches", [])}

    def words_of(detection_ids: list[str]) -> set[tuple[int, int]]:
        result: set[tuple[int, int]] = set()
        for detection_id in detection_ids:
            detection = detections.get(detection_id)
            if not detection:
                continue
            page = model["pages"][detection["page"] - 1]
            for _, line_index in detection["lines"]:
                if line_index < len(page["lines"]):
                    result.update((detection["page"], i) for i in page["lines"][line_index].get("word_indices", []))
        return result

    # 1. Global checks.
    global_findings = []
    source_pages, candidate_pages = comparison["source"]["pages"], comparison["candidate"]["pages"]
    if source_pages != candidate_pages:
        global_findings.append({"cause": "pagination", "severity": "high",
                                "detail": f"source has {source_pages} pages, candidate {candidate_pages}",
                                "same_page_rate": comparison["summary"]["matched_same_page"]})
    furniture = [d for d in features["detections"] if d["feature"] in {"page.running_footer", "page.page_number",
                                                                       "page.running_header"}]
    if furniture:
        furniture_evidence = _evidence(words_of([d["id"] for d in furniture]), matches)
        if furniture_evidence["same_page_rate"] is not None and furniture_evidence["same_page_rate"] < 0.5:
            global_findings.append({"cause": "running-furniture", "severity": "medium",
                                    "detail": "running header/footer/page-number text is not reproduced on matching pages",
                                    **furniture_evidence})

    # 2. Feature evidence and gap ranking.
    gap_words: set[tuple[int, int]] = set()
    for entry in reconstruction["gaps"]:
        if entry["reason"] in EDITOR_REASONS:
            gap_words |= words_of(entry["detection_ids"])
    all_words = {(page["page_number"], i) for page in model["pages"] for i in range(len(page["words"]))
                 if not page["words"][i].get("off_page") and not page["words"][i].get("invisible")}
    control = _evidence(all_words - gap_words, matches)
    by_feature: dict[str, list[str]] = defaultdict(list)
    for detection in features["detections"]:
        by_feature[detection["feature"]].append(detection["id"])
    feature_evidence = {feature: _evidence(words_of(ids), matches) for feature, ids in sorted(by_feature.items())
                        if words_of(ids)}

    grids = {}
    if visual and visual.get("status") == "compared":
        grids = {p["page_number"]: p["cell_grid"] for p in visual["pages"] if p.get("cell_grid")}
    missing_graphics = {p["page_number"]: p["graphics"].get("missing_source_boxes_mm", []) for p in comparison["pages"]}

    def visual_px(detection_ids: list[str]) -> int:
        cells: set[tuple[int, int, int]] = set()
        for detection_id in detection_ids:
            detection = detections.get(detection_id)
            # Page-level detections (size, margins) span the whole page and get no visual share.
            whole_page = detection is not None and detection["feature"] in {"page.size", "page.margins"}
            grid = grids.get(detection["page"]) if detection and not whole_page else None
            if not grid:
                continue
            size = grid["cell_mm"]
            x0, y0, x1, y1 = detection["box_mm"]
            for row in range(max(0, int(y0 // size)), min(len(grid["missing_px"]), int(y1 // size) + 1)):
                for column in range(max(0, int(x0 // size)), min(len(grid["missing_px"][row]), int(x1 // size) + 1)):
                    cells.add((detection["page"], row, column))
        return sum(grids[p]["missing_px"][r][c] + grids[p]["extra_px"][r][c] for p, r, c in cells)

    def lost_graphics(detection_ids: list[str]) -> int:
        lost = 0
        for detection_id in detection_ids:
            detection = detections.get(detection_id)
            if detection and detection["feature"].startswith("graphic.") and detection["box_mm"] in missing_graphics.get(
                    detection["page"], []):
                lost += 1
        return lost

    ranked = []
    for entry in reconstruction["gaps"]:
        words = words_of(entry["detection_ids"])
        evidence = _evidence(words, matches) if words else {"words": 0}
        excess_dx = (round(evidence["median_abs_dx_mm"] - control["median_abs_dx_mm"], 2)
                     if words and evidence.get("median_abs_dx_mm") is not None
                     and control["median_abs_dx_mm"] is not None else None)
        lost = round(evidence["words"] * (1 - evidence["found_rate"])) if words and evidence["found_rate"] is not None else 0
        graphics_lost = lost_graphics(entry["detection_ids"])
        ranked.append({"rank": 0, "feature": entry["feature"], "reason": entry["reason"],
                       "component": entry["component"], "property": entry["property"], "note": entry["note"],
                       "editor_finding": entry["reason"] in EDITOR_REASONS,
                       "occurrences": entry.get("occurrences", len(entry["detection_ids"])),
                       "pages": len({detections[d]["page"] for d in entry["detection_ids"] if d in detections}),
                       "evidence": evidence, "excess_median_dx_mm": excess_dx, "words_lost": lost,
                       "graphics_lost": graphics_lost, "visual_px": visual_px(entry["detection_ids"]),
                       "impact": round(evidence["words"] * max(0.0, excess_dx or 0.0) + 10 * (lost + graphics_lost), 1)})
    ranked.sort(key=lambda g: (not g["editor_finding"], -g["impact"], -g["evidence"]["words"]))
    # Gap groups share words (e.g. a justified paragraph with a decimal size). Exclusive evidence uses only
    # words not already claimed by a higher-ranked gap, to separate confounded causes.
    claimed: set[tuple[int, int]] = set()
    gap_words_by_key = {(e["feature"], e["reason"], e["component"], e["property"]): words_of(e["detection_ids"])
                        for e in reconstruction["gaps"]}
    for position, entry in enumerate(ranked, start=1):
        entry["rank"] = position
        words = gap_words_by_key[(entry["feature"], entry["reason"], entry["component"], entry["property"])]
        exclusive = words - claimed
        entry["exclusive_evidence"] = _evidence(exclusive, matches) if exclusive else {"words": 0}
        claimed |= words

    # 3. Region findings.
    blocks_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in reconstruction["provenance"]:
        blocks_by_page[item["page"]].append(item)
    gap_of_detection: dict[str, list[int]] = defaultdict(list)
    for index, entry in enumerate(reconstruction["gaps"]):
        for detection_id in entry["detection_ids"]:
            gap_of_detection[detection_id].append(index)

    def locate(page: int, box: list[float]) -> tuple[list[int], list[str], list[str]]:
        blocks = [b["block"] for b in blocks_by_page.get(page, []) if _overlaps(b["box_mm"], box)]
        found = [d for d in features["detections"] if d["page"] == page and _overlaps(d["box_mm"], box)
                 and d["feature"] not in {"page.size", "page.margins"}]
        contributors = sorted({f"{reconstruction['gaps'][g]['component']}.{reconstruction['gaps'][g]['property']}"
                               for d in found for g in gap_of_detection.get(d["id"], [])
                               if reconstruction["gaps"][g]["reason"] in EDITOR_REASONS})
        return blocks, sorted({d["feature"] for d in found}), contributors

    findings: list[dict[str, Any]] = []
    cause_words: dict[str, int] = defaultdict(int)
    for difference in comparison.get("differences", []):
        source, candidate = difference["source"], difference["candidate"]
        if source is None:
            cause = "extra-content"
            cause_words[cause] += candidate["words"]
            findings.append({"source": "text", "kind": difference["kind"], "cause": cause, "words": candidate["words"],
                             "candidate_pages": candidate["pages"], "excerpt": candidate["excerpt"][:120]})
            continue
        page = source["pages"][0]
        blocks, found, contributors = locate(page, source["box_mm"])
        if not blocks:
            cause = "not-reconstructed"
        elif difference["kind"] == "missing":
            cause = "content-lost-in-render"
        elif difference["kind"] == "moved":
            dx, dy = difference.get("median_shift_mm", [0, 0])
            if candidate and candidate["pages"][0] != page:
                cause = "pagination"
            elif abs(dy) >= abs(dx):
                cause = "vertical-drift"
            else:
                cause = "horizontal-drift"
        else:
            cause = "text-mismatch"
        cause_words[cause] += source["words"]
        findings.append({"source": "text", "kind": difference["kind"], "cause": cause, "words": source["words"],
                         "page": page, "candidate_pages": candidate["pages"] if candidate else [],
                         "box_mm": source["box_mm"], "blocks": blocks[:20], "features": found,
                         "possible_contributors": contributors, "excerpt": source["excerpt"][:120]})
    visual_cells = 0
    if visual and visual.get("status") == "compared":
        for page in visual["pages"]:
            for cell in page.get("worst_cells", []):
                visual_cells += 1
                blocks, found, contributors = locate(page["page_number"], cell["box_mm"])
                cause = ("not-reconstructed" if not blocks and cell["missing_px"] >= cell["extra_px"]
                         else "extra-content" if not blocks else "layout-drift")
                findings.append({"source": "visual", "cause": cause, "page": page["page_number"],
                                 "box_mm": cell["box_mm"], "missing_px": cell["missing_px"], "extra_px": cell["extra_px"],
                                 "blocks": blocks[:20], "features": found, "possible_contributors": contributors})
    return {"contract": ATTRIBUTION_VERSION,
            "summary": {"global": global_findings,
                        "text_differences": sum(1 for f in findings if f["source"] == "text"),
                        "visual_cells": visual_cells,
                        "words_by_cause": dict(sorted(cause_words.items(), key=lambda item: -item[1])),
                        "control_evidence": control},
            "gap_report": ranked, "feature_evidence": feature_evidence, "findings": findings[:2000],
            "limitations": ["Causes are hypotheses from alignment and region overlap; a reviewer confirms them.",
                            ("visual_px sums mismatched ink in the 10 mm cells a gap's detections touch; cells are "
                             "shared between overlapping gaps."),
                            ("Impact = words x excess median horizontal displacement over the control group, "
                             "plus 10 per lost word or source rule/box; vertical effects are confounded by pagination "
                             "and reported separately.")]}
