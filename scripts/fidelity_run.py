"""E16 template fidelity harness (Phase A): analyse, render and compare PDFs.

Examples:
  python scripts/fidelity_run.py analyse source.pdf --out artifacts/fidelity/source.json
  python scripts/fidelity_run.py compare source.pdf candidate.pdf --out artifacts/fidelity/report.json
  python scripts/fidelity_run.py run source.pdf --template-id isda-template --out-dir artifacts/fidelity/isda --diff-images
  python scripts/fidelity_run.py corpus --check
  python scripts/fidelity_run.py corpus --update-baseline --decision DD-423
  python scripts/fidelity_run.py capabilities --out artifacts/fidelity/capabilities.json

Analysis and comparison are offline. The visual comparison needs the optional
``fidelity`` extra (pypdfium2, DD-419) and reports ``unavailable-no-rasterizer``
without it. ``run`` and ``capabilities`` call only the
platform API at ``--base-url``. Reports are diagnostics, not approvals.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (BACKEND, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fidelity.api_client import DEFAULT_BASE_URL, ApiClient
from fidelity.attribute import attribute
from fidelity.compare import compare_models
from fidelity.corpus import (
    aggregate_gaps,
    aggregate_globals,
    check_regressions,
    document_scores,
    load_manifest,
    markdown_report,
    new_baseline,
)
from fidelity.reconstruct import reconstruct, validate_reconstruction
from fidelity.source_model import analyse_path, analyse_pdf
from fidelity.taxonomy import detect_features
from fidelity.visual import DEFAULT_DPI, DEFAULT_TOLERANCE_MM, compare_visual


def _write(path: Path | None, value: object) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summary_lines(report: dict) -> list[str]:
    s = report["summary"]
    t = s["typography"]
    p = s["position_mm"]
    return [
        (f"pages: source {report['source']['pages']}, candidate {report['candidate']['pages']}, "
         f"geometry mismatches {s['page_geometry_mismatches'] or 'none'}"),
        (f"text: precision {s['text']['precision']}, recall {s['text']['recall']}, F1 {s['text']['f1']}, "
         f"reading order {s['reading_order']}"),
        (f"position: {s['matched_words']} matched words, same page {s['matched_same_page']}, "
         f"within 1 mm {p['within_1mm']}, within 3 mm {p['within_3mm']}, median |dx| {p['dx']['median']} mm, "
         f"median |dy| {p['dy']['median']} mm"),
        (f"typography: size within 0.5 pt {t['size_within_tolerance']} (median delta {t['size_delta_pt']['median']} pt), "
         f"bold {t['bold_match']}, italic {t['italic_match']}, family class {t['family_class_match']}"),
        (f"graphics: source {s['graphics']['source']}, candidate {s['graphics']['candidate']}, "
         f"matched {s['graphics']['matched']}; images source {s['images']['source']}, candidate {s['images']['candidate']}"),
        f"differences: {s['differences']}",
        (f"renderer artifacts in text layer: {s['renderer_artifact_words']['candidate']} words; "
         f"off-page or invisible candidate words: {s['off_page_or_invisible_words']['candidate']}"),
        visual_line(report.get("visual")),
    ]


def visual_line(visual: dict | None) -> str:
    if not visual:
        return "visual: not run"
    if visual["status"] != "compared":
        return f"visual: {visual['status']}"
    v = visual["summary"]
    return (f"visual ({visual['settings']['dpi']} dpi, {visual['settings']['tolerance_mm']} mm tolerance): "
            f"ink F1 {v['tolerant']['f1']} (recall {v['tolerant']['recall']}, precision {v['tolerant']['precision']}), "
            f"ink ratio {v['ink_ratio']}, page F1 mean {v['page_f1']['mean']} / min {v['page_f1']['min']}, "
            f"{len(v['page_f1']['pages_below_0_5'])} pages below 0.5")


def add_visual(report: dict, args: argparse.Namespace, source: bytes, candidate: bytes, out_dir: Path | None) -> None:
    if args.no_visual:
        return
    diff_dir = out_dir / "visual" if (out_dir is not None and args.diff_images) else None
    report["visual"] = compare_visual(source, candidate, dpi=args.visual_dpi,
                                      tolerance_mm=args.visual_tolerance_mm, diff_dir=diff_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    analyse = commands.add_parser("analyse", help="write a SourceModel for one PDF")
    analyse.add_argument("pdf", type=Path)
    analyse.add_argument("--out", type=Path)
    compare = commands.add_parser("compare", help="compare a candidate PDF against a source PDF")
    compare.add_argument("source", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--out", type=Path)
    run = commands.add_parser("run", help="render a template through the API and compare it with the source")
    run.add_argument("source", type=Path)
    run.add_argument("--template-id", required=True)
    run.add_argument("--draft", action="store_true", help="render the latest draft instead of the published version")
    run.add_argument("--data", type=Path, help="JSON render data; defaults to the template sample data")
    run.add_argument("--out-dir", type=Path, required=True)
    rebuild = commands.add_parser("reconstruct", help="rebuild a source PDF as a template through the API and attribute gaps")
    rebuild.add_argument("source", type=Path)
    rebuild.add_argument("--out-dir", type=Path, required=True)
    rebuild.add_argument("--template-id", help="template id to create or add a draft to; default fidelity-<sha12>")
    rebuild.add_argument("--reconstruction", type=Path,
                         help="use an agent-produced reconstruction-v1 JSON instead of the rule-based mapper")
    corpus = commands.add_parser("corpus", help="rebuild every corpus document, rank gaps and track regressions")
    corpus.add_argument("--manifest", type=Path, default=ROOT / "fidelity-corpus" / "manifest.json")
    corpus.add_argument("--out-dir", type=Path, default=ROOT / "artifacts" / "fidelity" / "corpus")
    corpus.add_argument("--only", nargs="*", help="document ids to run")
    corpus.add_argument("--baseline", type=Path, default=ROOT / "fidelity-corpus" / "baselines.json")
    corpus.add_argument("--check", action="store_true", help="exit 1 when a score regresses beyond tolerance")
    corpus.add_argument("--update-baseline", action="store_true", help="write the current scores as the baseline")
    corpus.add_argument("--decision", help="design decision id that approves a baseline update, e.g. DD-423")
    capabilities = commands.add_parser("capabilities", help="fetch the editor capability manifest")
    capabilities.add_argument("--out", type=Path)
    for command in (compare, run, rebuild, corpus):
        command.add_argument("--no-visual", action="store_true", help="skip the raster comparison")
        command.add_argument("--visual-dpi", type=int, default=DEFAULT_DPI)
        command.add_argument("--visual-tolerance-mm", type=float, default=DEFAULT_TOLERANCE_MM)
        command.add_argument("--diff-images", action="store_true",
                             help="write per-page diff PNGs (red missing, blue extra, grey matched)")
    for command in (run, capabilities, rebuild, corpus):
        command.add_argument("--base-url", default=DEFAULT_BASE_URL)
        command.add_argument("--api-key")
    args = parser.parse_args()

    if args.command == "analyse":
        model = analyse_path(args.pdf)
        _write(args.out, model)
        print(json.dumps(model["summary"], indent=2) if args.out else json.dumps(model, indent=2))
        return 0
    if args.command == "compare":
        report = compare_models(analyse_path(args.source), analyse_path(args.candidate))
        add_visual(report, args, args.source.read_bytes(), args.candidate.read_bytes(),
                   args.out.parent if args.out else None)
        _write(args.out, report)
        print("\n".join(summary_lines(report)))
        return 0
    client = ApiClient(args.base_url, args.api_key)
    if args.command == "capabilities":
        manifest = client.capabilities()
        _write(args.out, manifest)
        if not args.out:
            print(json.dumps(manifest, indent=2))
        return 0
    if args.command == "reconstruct":
        return run_reconstruction(args, client)
    if args.command == "corpus":
        if args.update_baseline and not args.decision:
            parser.error("--update-baseline requires --decision DD-nnn")
        return run_corpus(args, client)
    data = json.loads(args.data.read_text(encoding="utf-8")) if args.data else None
    pdf, render_report = client.render_pdf(args.template_id, draft=args.draft, data=data)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate.pdf").write_bytes(pdf)
    source_model = analyse_path(args.source)
    candidate_model = analyse_pdf(pdf, label=f"{args.template_id}{' (draft)' if args.draft else ''}")
    report = compare_models(source_model, candidate_model)
    add_visual(report, args, args.source.read_bytes(), pdf, out)
    report["render_report"] = render_report
    report["capabilities_version"] = client.capabilities().get("version")
    _write(out / "source-model.json", source_model)
    _write(out / "candidate-model.json", candidate_model)
    _write(out / "report.json", report)
    print("\n".join(summary_lines(report)))
    print(f"artifacts: {out}")
    return 0


class ReconstructionRejected(Exception):
    def __init__(self, violations: list[str]) -> None:
        super().__init__(f"{len(violations)} editor-contract violations")
        self.violations = violations


def reconstruct_document(source: Path, out: Path, client: ApiClient, args: argparse.Namespace, *,
                         template_id: str | None = None, reconstruction: Path | None = None) -> dict:
    """Analyse, detect, rebuild (or load), validate, save via the API, render, compare and attribute."""
    out.mkdir(parents=True, exist_ok=True)
    source_bytes = source.read_bytes()
    source_model = analyse_pdf(source_bytes, label=source.name)
    features = detect_features(source_model)
    if reconstruction:
        rebuilt = json.loads(reconstruction.read_text(encoding="utf-8"))
        rebuilt.setdefault("method", "agent")
    else:
        rebuilt = reconstruct(source_model, features)
    manifest = client.capabilities()
    violations = validate_reconstruction(rebuilt, manifest)
    _write(out / "source-model.json", source_model)
    _write(out / "features.json", features)
    _write(out / "reconstruction.json", rebuilt)
    if violations:
        _write(out / "violations.json", violations)
        raise ReconstructionRejected(violations)
    template_id = template_id or f"fidelity-{source_model['sha256'][:12]}"
    saved = client.save_draft(template_id, rebuilt["definition"], summary=f"E16 {rebuilt.get('method')} reconstruction")
    pdf, render_report = client.render_pdf(template_id, draft=True)
    (out / "candidate.pdf").write_bytes(pdf)
    candidate_model = analyse_pdf(pdf, label=f"{template_id} (draft)")
    report = compare_models(source_model, candidate_model, include_matches=True)
    add_visual(report, args, source_bytes, pdf, out)
    attribution = attribute(source_model, features, rebuilt, report, report.get("visual"))
    report.pop("matches")
    report.update({"render_report": render_report, "capabilities_version": manifest.get("version"),
                   "template": {"id": template_id, **saved}, "reconstruction_method": rebuilt.get("method"),
                   "effort": rebuilt.get("effort"), "attribution_summary": attribution["summary"]})
    _write(out / "candidate-model.json", candidate_model)
    _write(out / "attribution.json", attribution)
    _write(out / "gap-report.json", attribution["gap_report"])
    _write(out / "report.json", report)
    return {"report": report, "attribution": attribution, "features": features, "rebuilt": rebuilt,
            "template_id": template_id, "saved": saved}


def run_reconstruction(args: argparse.Namespace, client: ApiClient) -> int:
    try:
        result = reconstruct_document(args.source, args.out_dir, client, args, template_id=args.template_id,
                                      reconstruction=args.reconstruction)
    except ReconstructionRejected as rejected:
        print(f"reconstruction rejected: {rejected} (see violations.json)")
        for violation in rejected.violations[:10]:
            print(f"  {violation}")
        return 2
    report, attribution, rebuilt = result["report"], result["attribution"], result["rebuilt"]
    print("\n".join(summary_lines(report)))
    effort = rebuilt.get("effort") or {}
    print(f"effort: {effort.get('blocks')} blocks {effort.get('block_types')}, {effort.get('properties_per_block')} "
          f"properties/block, {effort.get('workarounds')} workarounds, {effort.get('absolute_blocks')} absolute")
    summary = attribution["summary"]
    for finding in summary["global"]:
        print(f"GLOBAL [{finding['severity']}] {finding['cause']}: {finding['detail']}")
    print(f"words by cause: {summary['words_by_cause']}")
    control = summary["control_evidence"]
    print(f"control words (no editor gap): {control['words']}, median |dx| {control['median_abs_dx_mm']} mm, "
          f"dx within 3 mm {control['dx_within_3mm']}")
    print("top gaps (impact = words x excess |dx| over control + 10 x lost words):")
    for entry in attribution["gap_report"][:12]:
        evidence = entry["evidence"]
        print(f"  {entry['rank']:>2}. {entry['component']}.{entry['property']} [{entry['reason']}] {entry['feature']}: "
              f"{entry['occurrences']}x on {entry['pages']} pages, {evidence['words']} words, "
              f"median |dx| {evidence.get('median_abs_dx_mm')} mm (excess {entry['excess_median_dx_mm']}), "
              f"lost {entry['words_lost']}, impact {entry['impact']}; exclusive {entry['exclusive_evidence']['words']} words, "
              f"median |dx| {entry['exclusive_evidence'].get('median_abs_dx_mm')} mm")
    saved = result["saved"]
    print(f"template: {result['template_id']} ({saved.get('id') or saved.get('version_id')}); artifacts: {args.out_dir}")
    return 0


def run_corpus(args: argparse.Namespace, client: ApiClient) -> int:
    documents = load_manifest(args.manifest, ROOT)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.only:
        documents = [d for d in documents if d["id"] in set(args.only)]
    if any(d["origin"] == "generated" and not d["absolute_path"].exists() for d in documents):
        from build_fidelity_corpus import (
            build,
        )

        build(ROOT / "fidelity-corpus" / "generated")
    run = {"date": datetime.now(UTC).strftime("%Y-%m-%d"), "documents": {}, "skipped": [], "rejected": {},
           "pending_categories": manifest.get("pending_categories", [])}
    attributions = {}
    for document in documents:
        if not document["absolute_path"].exists():
            run["skipped"].append({"id": document["id"], "reason": "local-only file absent" if document["local_only"]
                                   else "file absent"})
            continue
        print(f"[{document['id']}] {document['path']}")
        try:
            result = reconstruct_document(document["absolute_path"], args.out_dir / document["id"], client, args,
                                          template_id=f"fidelity-{document['id']}")
        except ReconstructionRejected as rejected:
            run["rejected"][document["id"]] = rejected.violations[:20]
            print(f"  rejected: {rejected}")
            continue
        scores = document_scores(result["report"], result["features"], document["expected_features"])
        run["documents"][document["id"]] = {"category": document["category"], "local_only": document["local_only"],
                                            "scores": scores, "effort": result["rebuilt"].get("effort")}
        attributions[document["id"]] = result["attribution"]
        print(f"  text F1 {scores['text_f1']}, visual F1 {scores['visual_f1']}, same page {scores['same_page']}, "
              f"expected features {scores['expected_feature_recall']}")
    run["gaps"] = aggregate_gaps(attributions)
    run["globals"] = aggregate_globals(attributions)
    status = 0
    shared = {k: v["scores"] for k, v in run["documents"].items() if not v["local_only"]}
    local = {k: v["scores"] for k, v in run["documents"].items() if v["local_only"]}
    baselines = ((args.baseline, shared), (ROOT / "fidelity-corpus" / "local" / "baselines.json", local))
    if args.check:
        run["checked"] = True
        run["regressions"] = []
        for path, scores in baselines:
            if path.exists() and scores:
                run["regressions"] += check_regressions(scores, json.loads(path.read_text(encoding="utf-8")))
        status = 1 if run["regressions"] else 0
    if args.update_baseline:
        for path, scores in baselines:
            if scores:
                previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
                _write(path, new_baseline(scores, args.decision, ROOT / "docs" / "design-decisions.md", previous))
                print(f"baseline written: {path} ({args.decision})")
    _write(args.out_dir / "corpus-report.json", run)
    (args.out_dir / "corpus-report.md").write_text(markdown_report(run), encoding="utf-8")
    print(f"global findings: {[(g['cause'], len(g['documents'])) for g in run['globals']]}")
    print("top editor gaps across the corpus (mean share of each document's gap impact):")
    for gap in run["gaps"][:10]:
        print(f"  {gap['rank']:>2}. {gap['component']}.{gap['property']} [{gap['reason']}] {gap['feature']}: "
              f"share {gap['mean_impact_share']}, documents {gap['documents']}")
    if run.get("checked"):
        print(f"regressions: {len(run['regressions'])}")
        for regression in run["regressions"]:
            print(f"  {regression['document']} {regression['metric']}: {regression['baseline']} -> {regression['current']}")
    if run["skipped"]:
        print(f"skipped: {run['skipped']}")
    print(f"report: {args.out_dir / 'corpus-report.md'}")
    return 2 if run["rejected"] else status


if __name__ == "__main__":
    raise SystemExit(main())
