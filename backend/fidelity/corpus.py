"""Corpus manifest, cross-corpus gap ranking and fidelity regression tracking (E16-01, E16-08, E16-09, DD-423).

Ranking gives every document equal weight: a gap's score is the mean, over all
documents in the run, of its share of that document's editor-gap impact, where
the share averages the text-impact share (words x excess displacement plus lost
words and rules/boxes) and the visual share (mismatched ink in the gap's cells). A
large document therefore cannot drown out a gap that dominates several small
ones. Baselines hold per-document scores; a run fails when a score regresses
beyond its tolerance, and a baseline may only be replaced by citing a recorded
design decision.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CORPUS_VERSION = "fidelity-corpus-v1"
BASELINE_VERSION = "fidelity-baseline-v1"
# metric -> (direction, tolerance): "higher" metrics regress when they drop by more than the tolerance.
METRICS: dict[str, tuple[str, float]] = {
    "text_f1": ("higher", 0.01),
    "reading_order": ("higher", 0.02),
    "same_page": ("higher", 0.02),
    "position_within_3mm": ("higher", 0.03),
    "size_match": ("higher", 0.02),
    "visual_f1": ("higher", 0.03),
    "control_median_dx_mm": ("lower", 0.5),
    "expected_feature_recall": ("higher", 0.0),
    "page_count_match": ("higher", 0.0),
}


class CorpusError(ValueError):
    """Raised for invalid manifests or baseline updates."""


def load_manifest(path: Path, root: Path) -> list[dict[str, Any]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("contract") != CORPUS_VERSION:
        raise CorpusError(f"manifest contract must be {CORPUS_VERSION}")
    documents = []
    seen = set()
    for entry in manifest["documents"]:
        for key in ("id", "category", "path", "origin", "licence", "expected_features"):
            if key not in entry:
                raise CorpusError(f"document {entry.get('id')!r} lacks {key}")
        if entry["id"] in seen:
            raise CorpusError(f"duplicate document id {entry['id']}")
        seen.add(entry["id"])
        documents.append({**entry, "absolute_path": root / entry["path"],
                          "local_only": bool(entry.get("local_only"))})
    return documents


def document_scores(report: dict[str, Any], features: dict[str, Any], expected: list[str]) -> dict[str, Any]:
    summary = report["summary"]
    visual = report.get("visual") or {}
    detected = set(features["summary"])
    control = report.get("attribution_summary", {}).get("control_evidence", {})
    return {
        "text_f1": summary["text"]["f1"],
        "reading_order": summary["reading_order"],
        "same_page": summary["matched_same_page"],
        "position_within_3mm": summary["position_mm"]["within_3mm"],
        "size_match": summary["typography"]["size_within_tolerance"],
        "visual_f1": (visual.get("summary") or {}).get("tolerant", {}).get("f1"),
        "control_median_dx_mm": control.get("median_abs_dx_mm"),
        "expected_feature_recall": round(sum(f in detected for f in expected) / len(expected), 4) if expected else 1.0,
        "missing_expected_features": sorted(set(expected) - detected),
        "page_count_match": 1.0 if summary["page_count_match"] else 0.0,
    }


def aggregate_gaps(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank editor gaps across documents; ``results`` maps document id to its attribution."""
    totals: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for document_id, attribution in results.items():
        editor_gaps = [g for g in attribution["gap_report"] if g["editor_finding"]]
        document_impact = sum(g["impact"] for g in editor_gaps)
        document_visual = sum(g.get("visual_px", 0) for g in editor_gaps)
        for gap in editor_gaps:
            key = (gap["component"], gap["property"], gap["reason"], gap["feature"])
            entry = totals.setdefault(key, {"component": key[0], "property": key[1], "reason": key[2],
                                            "feature": key[3], "note": gap["note"], "documents": [],
                                            "occurrences": 0, "words": 0, "impact": 0.0, "share_sum": 0.0})
            entry["documents"].append(document_id)
            entry["occurrences"] += gap["occurrences"]
            entry["words"] += gap["evidence"].get("words", 0)
            entry["impact"] += gap["impact"]
            text_share = gap["impact"] / document_impact if document_impact else 0.0
            visual_share = gap.get("visual_px", 0) / document_visual if document_visual else None
            entry["share_sum"] += text_share if visual_share is None else (text_share + visual_share) / 2
            entry["visual_px"] = entry.get("visual_px", 0) + gap.get("visual_px", 0)
    ranked = []
    for entry in totals.values():
        entry["mean_impact_share"] = round(entry.pop("share_sum") / max(1, len(results)), 4)
        entry["impact"] = round(entry["impact"], 1)
        ranked.append(entry)
    ranked.sort(key=lambda e: (-e["mean_impact_share"], -len(e["documents"]), -e["impact"]))
    for position, entry in enumerate(ranked, start=1):
        entry["rank"] = position
    return ranked


def aggregate_globals(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    found: dict[str, list[str]] = defaultdict(list)
    for document_id, attribution in results.items():
        for finding in attribution["summary"]["global"]:
            found[finding["cause"]].append(document_id)
    return [{"cause": cause, "documents": documents} for cause, documents in sorted(found.items(), key=lambda i: -len(i[1]))]


def check_regressions(scores: dict[str, dict[str, Any]], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    regressions = []
    for document_id, current in scores.items():
        previous = baseline.get("documents", {}).get(document_id)
        if previous is None:
            continue
        for metric, (direction, tolerance) in METRICS.items():
            before, after = previous.get(metric), current.get(metric)
            if before is None or after is None:
                continue
            worse = (before - after) if direction == "higher" else (after - before)
            if worse > tolerance + 1e-9:
                regressions.append({"document": document_id, "metric": metric, "baseline": before,
                                    "current": after, "tolerance": tolerance})
    return regressions


def new_baseline(scores: dict[str, dict[str, Any]], decision: str, decisions_path: Path,
                 previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a baseline; the decision must be a DD id recorded in the decision register."""
    if not re.fullmatch(r"DD-\d+", decision or ""):
        raise CorpusError("a baseline update must cite a decision id such as DD-423")
    if not re.search(rf"^## {re.escape(decision)}\b", decisions_path.read_text(encoding="utf-8"), re.MULTILINE):
        raise CorpusError(f"{decision} is not recorded in {decisions_path.name}")
    documents = dict((previous or {}).get("documents", {}))
    documents.update({k: {m: v for m, v in s.items() if m in METRICS} for k, s in scores.items()})
    return {"contract": BASELINE_VERSION, "decision": decision,
            "updated": datetime.now(UTC).strftime("%Y-%m-%d"), "metrics": {k: list(v) for k, v in METRICS.items()},
            "documents": dict(sorted(documents.items()))}


def markdown_report(run: dict[str, Any]) -> str:
    lines = [f"# E16 corpus fidelity report ({run['date']})", "",
             "Diagnostic only: not native-reader, accessibility, legal or second-engine evidence.", "",
             "| Document | Category | Text F1 | Reading order | Same page | Visual F1 | Size match | Control dx (mm) | Expected features |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for document_id, item in run["documents"].items():
        s = item["scores"]
        missing = ", ".join(s["missing_expected_features"]) or "all"
        lines.append(f"| {document_id} | {item['category']} | {s['text_f1']} | {s['reading_order']} | {s['same_page']} | "
                     f"{s['visual_f1']} | {s['size_match']} | {s['control_median_dx_mm']} | "
                     f"{'all' if missing == 'all' else 'missing ' + missing} |")
    lines += ["", "## Global renderer findings", ""]
    lines += [f"- {g['cause']}: {', '.join(g['documents'])}" for g in run["globals"]] or ["- none"]
    lines += ["", "## Editor gaps across the corpus", "",
              "| Rank | Gap | Reason | Feature | Documents | Mean impact share | Words |",
              "| ---: | --- | --- | --- | --- | ---: | ---: |"]
    for gap in run["gaps"][:20]:
        lines.append(f"| {gap['rank']} | `{gap['component']}.{gap['property']}` | {gap['reason']} | {gap['feature']} | "
                     f"{', '.join(gap['documents'])} | {gap['mean_impact_share']} | {gap['words']} |")
    lines += ["", "## Regressions", ""]
    lines += [f"- {r['document']} {r['metric']}: {r['baseline']} -> {r['current']} (tolerance {r['tolerance']})"
              for r in run.get("regressions", [])] or ["- none" if run.get("checked") else "- not checked"]
    if run.get("pending_categories"):
        lines += ["", f"Corpus categories not yet covered: {', '.join(run['pending_categories'])}."]
    return "\n".join(lines) + "\n"
