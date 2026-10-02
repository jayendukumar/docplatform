"""E16 Phase C regression tests: generated corpus ground truth, ranking, regressions and baselines (DD-423)."""
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parent
for path in (BACKEND, REPOSITORY / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fidelity import visual
from fidelity.corpus import (
    CorpusError,
    aggregate_gaps,
    check_regressions,
    load_manifest,
    markdown_report,
    new_baseline,
)
from fidelity.source_model import analyse_path
from fidelity.taxonomy import detect_features

MANIFEST = REPOSITORY / "fidelity-corpus" / "manifest.json"


def test_manifest_is_valid_and_marks_local_only_material():
    documents = {d["id"]: d for d in load_manifest(MANIFEST, REPOSITORY)}
    assert {"letter", "invoice", "form", "report", "statement", "contract", "isda-2002"} <= set(documents)
    assert documents["isda-2002"]["local_only"] is True
    assert all(not d["local_only"] for k, d in documents.items() if k != "isda-2002")
    assert all(d["expected_features"] for d in documents.values())


@pytest.mark.skipif(visual.rasterizer_status() != "available", reason="corpus generator needs the fidelity extra")
def test_generated_corpus_detections_match_authored_ground_truth(tmp_path):
    from build_fidelity_corpus import build

    built = build(tmp_path)
    documents = {d["id"]: d for d in load_manifest(MANIFEST, REPOSITORY) if d["origin"] == "generated"}
    assert set(built) == set(documents)
    for document_id, path in built.items():
        model = analyse_path(path)
        assert model["summary"]["default_width_share"] == 0.0, document_id   # exact embedded widths
        detected = set(detect_features(model)["summary"])
        missing = set(documents[document_id]["expected_features"]) - detected
        assert not missing, f"{document_id}: detectors missed {sorted(missing)}"
    report = analyse_path(built["report"])
    assert all(page["gutter_mm"] and 104 < page["gutter_mm"] < 112 for page in report["pages"])
    statement = analyse_path(built["statement"])
    assert all(page["gutter_mm"] is None for page in statement["pages"])   # tables are not columns


def _attribution(gaps):
    return {"gap_report": [{"editor_finding": True, "component": c, "property": p, "reason": "missing-property",
                            "feature": f, "note": "", "occurrences": 1, "evidence": {"words": 10}, "impact": impact,
                            "visual_px": 0} for c, p, f, impact in gaps],
            "summary": {"global": []}}


def test_cross_corpus_ranking_weights_documents_equally():
    results = {
        "huge": _attribution([("text", "align", "text.align_justify", 100000.0), ("text", "font_size", "text.decimal_size", 1.0)]),
        "small-1": _attribution([("text", "font_size", "text.decimal_size", 10.0)]),
        "small-2": _attribution([("text", "font_size", "text.decimal_size", 5.0), ("text", "align", "text.align_justify", 5.0)]),
    }
    ranked = aggregate_gaps(results)
    assert [g["property"] for g in ranked] == ["font_size", "align"]
    assert ranked[0]["documents"] == ["huge", "small-1", "small-2"]
    assert ranked[1]["impact"] == 100005.0   # raw impact is reported but does not decide the rank


def test_regressions_respect_direction_and_tolerance():
    baseline = {"documents": {"letter": {"text_f1": 0.99, "visual_f1": 0.65, "control_median_dx_mm": 0.2,
                                         "page_count_match": 1.0}}}
    current = {"letter": {"text_f1": 0.985, "visual_f1": 0.60, "control_median_dx_mm": 0.9, "page_count_match": 0.0},
               "new-doc": {"text_f1": 0.1}}
    regressions = {(r["document"], r["metric"]) for r in check_regressions(current, baseline)}
    assert regressions == {("letter", "visual_f1"), ("letter", "control_median_dx_mm"), ("letter", "page_count_match")}


def test_baseline_updates_require_a_recorded_decision(tmp_path):
    register = tmp_path / "design-decisions.md"
    register.write_text("## DD-900 - Approve fidelity baseline\n", encoding="utf-8")
    scores = {"letter": {"text_f1": 1.0, "missing_expected_features": [], "visual_f1": 0.6}}
    baseline = new_baseline(scores, "DD-900", register)
    assert baseline["decision"] == "DD-900" and baseline["documents"]["letter"] == {"text_f1": 1.0, "visual_f1": 0.6}
    with pytest.raises(CorpusError, match="cite a decision"):
        new_baseline(scores, "because", register)
    with pytest.raises(CorpusError, match="not recorded"):
        new_baseline(scores, "DD-901", register)


def test_markdown_report_lists_scores_gaps_and_pending_categories():
    run = {"date": "2026-10-01", "documents": {"letter": {"category": "letter", "scores": {
        "text_f1": 1.0, "reading_order": 1.0, "same_page": 1.0, "visual_f1": 0.65, "size_match": 1.0,
        "control_median_dx_mm": 0.02, "missing_expected_features": []}}},
        "globals": [], "gaps": aggregate_gaps({"letter": _attribution([("text", "align", "text.align_justify", 3.0)])}),
        "checked": True, "regressions": [], "pending_categories": ["rtl-or-cjk"]}
    text = markdown_report(run)
    assert "| letter | letter | 1.0 |" in text and "`text.align`" in text
    assert "Corpus categories not yet covered: rtl-or-cjk." in text
    assert json.dumps(run)  # the run record is JSON-serialisable
