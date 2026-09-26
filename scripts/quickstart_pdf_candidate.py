"""Produce the documented offline Chromium PDF candidate from a rendered HTML file."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="HTML artifact created by the quickstart")
    parser.add_argument("--pdf", type=Path, default=Path("artifacts/quickstart-candidate.pdf"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--screenshot", type=Path, default=Path("artifacts/quickstart-candidate.png"))
    args = parser.parse_args()
    html = args.html.resolve()
    if not html.is_file():
        parser.error(f"HTML input does not exist: {html}")
    node = shutil.which("node")
    if not node:
        parser.error("Node.js is required; install the pinned frontend toolchain first")
    playwright_entry = ROOT / "frontend" / "node_modules" / "playwright" / "index.mjs"
    if not playwright_entry.is_file():
        parser.error("frontend dependencies are missing; run npm --prefix frontend ci first")
    pdf = args.pdf.resolve()
    pdf.parent.mkdir(parents=True, exist_ok=True)
    manifest = (args.manifest or pdf.with_suffix(".json")).resolve()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    screenshot = args.screenshot.resolve() if args.screenshot else None
    if screenshot:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
    command = [node, str(ROOT / "scripts" / "render_chromium_candidate.mjs"), str(html), str(pdf),
               str(manifest)]
    if screenshot:
        command.append(str(screenshot))
    started = time.perf_counter()
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except FileNotFoundError:
        parser.error("Chromium is not installed; run npx --prefix frontend playwright install chromium")
    elapsed = time.perf_counter() - started
    if not pdf.is_file() or pdf.stat().st_size == 0 or pdf.read_bytes()[:5] != b"%PDF-":
        parser.error("Chromium candidate did not produce a non-empty PDF")
    if not manifest.is_file() or manifest.stat().st_size == 0:
        parser.error("Chromium candidate did not produce a manifest")
    print(f"PDF candidate: {pdf}")
    print(f"Manifest: {manifest}")
    if screenshot:
        print(f"Visual candidate: {screenshot}")
    print(f"Elapsed seconds: {elapsed:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
