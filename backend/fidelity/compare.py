"""Region-level comparison of two SourceModels (E16-06).

Words are aligned across the whole document in reading order, so differences
in line wrapping or page breaks do not hide matching content. Matched words
yield position and typography deltas; unmatched runs become localised
differences for later attribution (E16-07). No raster comparison is made.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

COMPARISON_VERSION = "fidelity-comparison-v1"
RENDERER_ARTIFACT = re.compile(r"__DOCPLATFORM_ANCHOR_[A-Za-z0-9_-]*__")
GRAPHIC_TOLERANCE_MM = 2.0
MOVED_THRESHOLD_MM = 3.0
SIZE_TOLERANCE_PT = 0.5
MAX_DIFFERENCES = 1000


def _normal(text: str) -> str:
    return re.sub(r"[^\w]", "", text.casefold())


def _words(model: dict[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
    words: list[dict[str, Any]] = []
    artifacts = off_page = 0
    for page in model["pages"]:
        ordered = sorted(({**w, "index": i} for i, w in enumerate(page["words"])),
                         key=lambda w: (w.get("column", 0), round(w["y_mm"], 0), w["x_mm"]))
        for word in ordered:
            if word.get("off_page") or word.get("invisible"):
                off_page += 1
                continue
            text = word["text"]
            if RENDERER_ARTIFACT.search(text):
                artifacts += 1
                text = RENDERER_ARTIFACT.sub("", text)
            key = _normal(text)
            if key:
                words.append({**word, "text": text, "key": key, "page": page["page_number"]})
    return words, artifacts, off_page


def _f1(source: Counter[str], candidate: Counter[str]) -> dict[str, float]:
    common = sum((source & candidate).values())
    precision = common / sum(candidate.values()) if candidate else 0.0
    recall = common / sum(source.values()) if source else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def _distribution(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"median": None, "p90": None, "max": None}
    ordered = sorted(values)
    return {"median": round(statistics.median(ordered), 3),
            "p90": round(ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))], 3),
            "max": round(ordered[-1], 3)}


def _region(words: list[dict[str, Any]]) -> dict[str, Any]:
    pages = sorted({w["page"] for w in words})
    first_page = [w for w in words if w["page"] == pages[0]]
    return {"pages": pages,
            "box_mm": [round(min(w["x_mm"] for w in first_page), 2), round(min(w["y_mm"] for w in first_page), 2),
                       round(max(w["x_mm"] + w["width_mm"] for w in first_page), 2),
                       round(max(w["y_mm"] for w in first_page), 2)],
            "words": len(words), "excerpt": " ".join(w["text"] for w in words[:24])[:200]}


def _graphics_match(source: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> dict[str, Any]:
    unmatched = list(candidate)
    matched = 0
    missing: list[list[float]] = []
    for graphic in source:
        for index, other in enumerate(unmatched):
            if other["kind"] == graphic["kind"] and all(
                    abs(a - b) <= GRAPHIC_TOLERANCE_MM for a, b in zip(graphic["box_mm"], other["box_mm"], strict=True)):
                matched += 1
                del unmatched[index]
                break
        else:
            missing.append(graphic["box_mm"])
    return {"source": len(source), "candidate": len(candidate), "matched": matched, "missing_source_boxes_mm": missing}


def compare_models(source: dict[str, Any], candidate: dict[str, Any], *, include_matches: bool = False
                   ) -> dict[str, Any]:
    """Compare a candidate SourceModel against the source SourceModel.

    With ``include_matches`` the result carries ``matches``: one compact record per aligned word
    (source page/word index, candidate page, dx/dy in mm, size delta) for attribution. Callers
    normally drop it before writing reports.
    """
    source_words, source_artifacts, source_off_page = _words(source)
    candidate_words, candidate_artifacts, candidate_off_page = _words(candidate)
    matcher = SequenceMatcher(None, [w["key"] for w in source_words], [w["key"] for w in candidate_words])
    matched_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    differences: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            matched_pairs.extend(zip(source_words[i1:i2], candidate_words[j1:j2], strict=True))
            continue
        if i2 > i1:
            differences.append({"kind": "missing" if tag == "delete" else "replaced",
                                "source": _region(source_words[i1:i2]),
                                "candidate": _region(candidate_words[j1:j2]) if j2 > j1 else None})
        elif j2 > j1:
            differences.append({"kind": "extra", "source": None, "candidate": _region(candidate_words[j1:j2])})

    same_page = [(s, c) for s, c in matched_pairs if s["page"] == c["page"]]
    dx = [c["x_mm"] - s["x_mm"] for s, c in same_page]
    dy = [c["y_mm"] - s["y_mm"] for s, c in same_page]
    displacement = [(x * x + y * y) ** 0.5 for x, y in zip(dx, dy, strict=True)]
    run: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def flush_moved() -> None:
        if run:
            differences.append({"kind": "moved", "source": _region([s for s, _ in run]),
                                "candidate": _region([c for _, c in run]),
                                "median_shift_mm": [round(statistics.median(c["x_mm"] - s["x_mm"] for s, c in run), 2),
                                                    round(statistics.median(c["y_mm"] - s["y_mm"] for s, c in run), 2)]})
            run.clear()

    for source_word, candidate_word in matched_pairs:
        shift = ((candidate_word["x_mm"] - source_word["x_mm"]) ** 2 + (candidate_word["y_mm"] - source_word["y_mm"]) ** 2) ** 0.5
        if source_word["page"] != candidate_word["page"] or shift > MOVED_THRESHOLD_MM:
            if run and run[-1][0]["page"] != source_word["page"]:
                flush_moved()
            run.append((source_word, candidate_word))
        else:
            flush_moved()
    flush_moved()

    size_deltas = [abs(c["size_pt"] - s["size_pt"]) for s, c in matched_pairs]
    total = len(matched_pairs) or 1
    typography = {
        "size_delta_pt": _distribution(size_deltas),
        "size_within_tolerance": round(sum(d <= SIZE_TOLERANCE_PT for d in size_deltas) / total, 4),
        "bold_match": round(sum(s["bold"] == c["bold"] for s, c in matched_pairs) / total, 4),
        "italic_match": round(sum(s["italic"] == c["italic"] for s, c in matched_pairs) / total, 4),
        "family_class_match": round(sum(s["family_class"] == c["family_class"] for s, c in matched_pairs) / total, 4),
        "source_fonts": dict(Counter(w["font"] for w in source_words).most_common(10)),
        "candidate_fonts": dict(Counter(w["font"] for w in candidate_words).most_common(10)),
    }

    pages = []
    for index in range(max(source["page_count"], candidate["page_count"])):
        src_page = source["pages"][index] if index < source["page_count"] else None
        cand_page = candidate["pages"][index] if index < candidate["page_count"] else None
        src_keys = Counter(w["key"] for w in source_words if w["page"] == index + 1)
        cand_keys = Counter(w["key"] for w in candidate_words if w["page"] == index + 1)
        pages.append({
            "page_number": index + 1,
            "size_mm": {"source": [src_page["width_mm"], src_page["height_mm"]] if src_page else None,
                        "candidate": [cand_page["width_mm"], cand_page["height_mm"]] if cand_page else None},
            "text": _f1(src_keys, cand_keys),
            "graphics": _graphics_match(src_page["graphics"] if src_page else [], cand_page["graphics"] if cand_page else []),
            "images": {"source": len(src_page["images"]) if src_page else 0,
                       "candidate": len(cand_page["images"]) if cand_page else 0},
        })

    geometry_mismatches = [p["page_number"] for p in pages if p["size_mm"]["source"] is None
                           or p["size_mm"]["candidate"] is None
                           or any(abs(a - b) > 0.5 for a, b in zip(p["size_mm"]["source"], p["size_mm"]["candidate"], strict=True))]
    differences.sort(key=lambda d: -((d["source"] or d["candidate"])["words"]))
    graphics_source = sum(p["graphics"]["source"] for p in pages)
    graphics_candidate = sum(p["graphics"]["candidate"] for p in pages)
    graphics_matched = sum(p["graphics"]["matched"] for p in pages)
    result = {
        "contract": COMPARISON_VERSION,
        "source": {"label": source.get("label"), "sha256": source.get("sha256"), "pages": source["page_count"],
                   "words": len(source_words)},
        "candidate": {"label": candidate.get("label"), "sha256": candidate.get("sha256"), "pages": candidate["page_count"],
                      "words": len(candidate_words)},
        "summary": {
            "page_count_match": source["page_count"] == candidate["page_count"],
            "page_geometry_mismatches": geometry_mismatches,
            "text": _f1(Counter(w["key"] for w in source_words), Counter(w["key"] for w in candidate_words)),
            "reading_order": round(matcher.ratio(), 4),
            "matched_words": len(matched_pairs),
            "matched_same_page": round(len(same_page) / total, 4),
            "position_mm": {"dx": _distribution([abs(v) for v in dx]), "dy": _distribution([abs(v) for v in dy]),
                            "within_1mm": round(sum(d <= 1 for d in displacement) / max(1, len(displacement)), 4),
                            "within_3mm": round(sum(d <= 3 for d in displacement) / max(1, len(displacement)), 4)},
            "typography": typography,
            "graphics": {"source": graphics_source, "candidate": graphics_candidate, "matched": graphics_matched,
                         "recall": round(graphics_matched / graphics_source, 4) if graphics_source else None,
                         "precision": round(graphics_matched / graphics_candidate, 4) if graphics_candidate else None},
            "images": {"source": sum(p["images"]["source"] for p in pages),
                       "candidate": sum(p["images"]["candidate"] for p in pages)},
            "differences": dict(Counter(d["kind"] for d in differences)),
            "renderer_artifact_words": {"source": source_artifacts, "candidate": candidate_artifacts},
            "off_page_or_invisible_words": {"source": source_off_page, "candidate": candidate_off_page},
        },
        "pages": pages,
        "differences": differences[:MAX_DIFFERENCES],
        "differences_truncated": len(differences) > MAX_DIFFERENCES,
        "limitations": ["Raster comparison is reported separately (fidelity.visual, DD-420).",
                        "Reading order is column by column (two-column gutters only), then top-to-bottom, left-to-right.",
                        "Diagnostic only: not native-reader, accessibility, legal or second-engine evidence."],
    }
    if include_matches:
        result["matches"] = [{"source_page": src["page"], "source_index": src["index"], "candidate_page": cand["page"],
                              "dx_mm": round(cand["x_mm"] - src["x_mm"], 3), "dy_mm": round(cand["y_mm"] - src["y_mm"], 3),
                              "size_delta_pt": round(cand["size_pt"] - src["size_pt"], 2)}
                             for src, cand in matched_pairs]
    return result
