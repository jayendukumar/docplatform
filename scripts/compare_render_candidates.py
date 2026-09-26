"""Compare the deterministic HTML and provisional Chromium candidates offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.rendering import render_definition  # noqa: I001


FIXTURES: list[dict[str, Any]] = [
    {
        "name": "script-matrix",
        "locale": "en",
        "metadata": {"title": "Script matrix", "author": "Document Platform"},
        "blocks": [{"type": "text", "text": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u05e2\u05d1\u05e8\u05d9\u05ea \u0939\u093f\u0928\u094d\u0926\u0940 \u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0e44\u0e17\u0e22 \u4e2d\u6587 \u65e5\u672c\u8a9e \ud55c\uad6d\uc5b4"}],
    },
    {
        "name": "page-flow-and-metadata",
        "locale": "de-DE",
        "metadata": {"title": "Quarterly report", "author": "Finance"},
        "page": {"size": "Letter", "orientation": "landscape", "margin_mm": 18,
                 "header": "{{title}}", "footer": "Confidential", "show_page_numbers": True},
        "sample_data": {"title": "Q3"},
        "blocks": [
            {"type": "text", "text": "Heading", "break_before": True, "keep_together": True},
            {"type": "table", "items": "rows", "keep_together": True,
             "columns": [{"header": "Name", "path": "name"}]},
        ],
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "render-candidate-comparison.json")
    args = parser.parse_args()
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for the Chromium candidate")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate_dir = output.parent / "render-candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    harness = ROOT / "scripts" / "render_chromium_candidate.mjs"
    results = []
    for fixture in FIXTURES:
        name = fixture["name"]
        rendered = render_definition(fixture, fixture.get("sample_data", {}))
        html_path = candidate_dir / f"{name}.html"
        pdf_path = candidate_dir / f"{name}.pdf"
        manifest_path = candidate_dir / f"{name}.json"
        screenshot_path = candidate_dir / f"{name}.png"
        html_path.write_text(rendered["artifact"], encoding="utf-8")
        subprocess.run([node, str(harness), str(html_path), str(pdf_path), str(manifest_path), str(screenshot_path)],
                       cwd=ROOT, check=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results.append({
            "name": name,
            "deterministic_html": {"sha256": sha256(html_path), "engine": rendered["engine"],
                                    "scripts": rendered["scripts"], "metadata": rendered["metadata"]},
            "chromium_pdf": {"sha256": sha256(pdf_path), "manifest": manifest},
            "chromium_visual_baseline": {"sha256": sha256(screenshot_path), "path": str(screenshot_path)},
        })
    report = {
        "status": "pending-native-review",
        "candidates": ["deterministic-html-0.1", "chromium-playwright"],
        "native_reader_scores": None,
        "visual_comparison": None,
        "visual_baseline": {"method": "Chromium full-page PNG SHA-256", "reviewed": False,
                            "reason": "baseline is reproducible evidence, not human visual approval"},
        "environment": {"python": sys.version.split()[0], "node": subprocess.check_output(
            [node, "--version"], text=True).strip()},
        "results": results,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
