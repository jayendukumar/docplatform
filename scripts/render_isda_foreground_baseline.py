"""Render the current application-owned ISDA foreground to offline Chromium artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.isda_template import editable_isda_blocks, isda_data_schema, isda_sample_data  # noqa: E402
from app.rendering import render_definition  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "isda-foreground-baseline")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "isda-foreground.html"
    pdf_path = output_dir / "isda-foreground.pdf"
    manifest_path = output_dir / "isda-foreground.json"
    png_path = output_dir / "isda-foreground.png"
    definition = {
        "name": "ISDA editable foreground baseline",
        "page": {"size": "Letter", "orientation": "portrait", "margin_mm": 0, "show_page_numbers": False},
        "blocks": editable_isda_blocks(),
        "data_schema": isda_data_schema(),
        "sample_data": isda_sample_data(),
        "metadata": {"title": "2002 Master Agreement", "author": "International Swaps and Derivatives Association, Inc."},
    }
    rendered = render_definition(definition, isda_sample_data())
    if rendered["missing_fields"]:
        raise SystemExit(f"missing fields: {rendered['missing_fields']}")
    html_path.write_text(rendered["artifact"], encoding="utf-8")
    harness = ROOT / "scripts" / "render_chromium_candidate.mjs"
    subprocess.run(["node", str(harness), str(html_path), str(pdf_path), str(manifest_path), str(png_path)], cwd=ROOT, check=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "status": "foreground-baseline",
        "locked_background": "omitted",
        "objects": len(definition["blocks"]),
        "missing_fields": rendered["missing_fields"],
        "html_sha256": sha256(html_path),
        "pdf_sha256": sha256(pdf_path),
        "png_sha256": sha256(png_path),
        "chromium_manifest": manifest,
    }
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
