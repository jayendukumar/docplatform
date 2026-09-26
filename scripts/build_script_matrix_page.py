"""Build the checked-in script matrix page from a deterministic JSON report."""
from __future__ import annotations

import json
from pathlib import Path
import sys


FAMILIES = [
    ("Arabic", "arabic"), ("Hebrew", "hebrew"), ("Devanagari", "devanagari"),
    ("Tamil", "tamil"), ("Thai", "thai"), ("Chinese", "cjk"),
    ("Japanese", "cjk"), ("Korean", "korean"),
]


def build(report: dict) -> str:
    results = report.get("results") or []
    detected = set(results[0].get("scripts", [])) if results else set()
    lines = [
        "# Script test matrix", "",
        "This page is generated from the deterministic offline report produced by `scripts/render_spike.py`. It is not native-reader approval and does not establish final PDF-engine selection.",
        "", "| Script family | Reported script | Deterministic result | Status |",
        "| --- | --- | --- | --- |",
    ]
    for label, script in FAMILIES:
        if script in detected:
            result = "Script detection, escaped HTML and fallback-stack report"
            status = "Contract covered; native review pending"
        else:
            result = "No result in current report"
            status = "Planned"
        lines.append(f"| {label} | `{script}` | {result} | {status} |")
    lines.extend([
        "", "## Rebuild the contract report", "", "```powershell",
        "python scripts/render_spike.py > artifacts/script-matrix.json",
        "python scripts/build_script_matrix_page.py artifacts/script-matrix.json > artifacts/script-test-matrix.md",
        "```", "",
        "The report is intentionally offline and deterministic. Before E4-01 can be accepted, add a second candidate engine, capture exact engine/font/environment manifests, produce visual baselines, and obtain native-reader grades. Do not convert a passing script-detection check into a glyph, shaping, line-breaking, or PDF claim.",
        "", "## CI contract", "",
        "`.github/workflows/script-matrix.yml` rebuilds the JSON report and this page, then checks the generated page against the checked-in documentation. The gate is deterministic contract coverage for E4-08/E14-03, not visual regression: no native font rendering, screenshot baseline, or native-reader approval is claimed yet.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_script_matrix_page.py REPORT.json")
    # PowerShell 5 writes a UTF-8 BOM for `>`/Set-Content; accept it while
    # retaining ordinary UTF-8 output for the generated page.
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    sys.stdout.write(build(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
