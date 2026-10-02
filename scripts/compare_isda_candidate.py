"""Compare the editable ISDA candidate with the locked source PDF offline.

This command measures bounded PDF/text/resource facts only. The candidate must
have been rendered with the API's ``comparison_mode=editable-only`` mode; the
command does not merge the source into the candidate, render page images, or
infer native-reader or legal approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def visual_comparison_status() -> str:
    """Describe why this diagnostic does not emit page-image comparison data."""
    rasterizers = ("pdftoppm", "pdftocairo", "mutool", "magick", "gs")
    if any(shutil.which(command) for command in rasterizers):
        return "not-run-rasterizer-not-integrated"
    return "unavailable-no-local-rasterizer"


def candidate_manifest_status(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"status": "not-supplied", "path": None, "locked_background": None}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    locked_background = manifest.get("locked_background")
    if locked_background != "omitted":
        raise ValueError("candidate manifest must declare locked_background=omitted")
    object_count = manifest.get("objects")
    if not isinstance(object_count, int) or object_count <= 0:
        raise ValueError("candidate manifest must declare a positive semantic object count")
    return {"status": "foreground-only", "path": str(path), "locked_background": locked_background, "object_count": object_count}


def page_texts(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    return [re.sub(r"\s+", " ", page.extract_text() or "").strip() for page in reader.pages]


def normalized_text(path: Path) -> str:
    return " ".join(page_texts(path)).strip()


def page_text_metrics(source_pages: list[str], candidate_pages: list[str]) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    for index in range(max(len(source_pages), len(candidate_pages))):
        source_page = source_pages[index] if index < len(source_pages) else ""
        candidate_page = candidate_pages[index] if index < len(candidate_pages) else ""
        metrics.append(
            {
                "page": index + 1,
                "source_chars": len(source_page),
                "candidate_chars": len(candidate_page),
                "similarity": round(SequenceMatcher(None, source_page, candidate_page).ratio(), 4),
            }
        )
    return metrics


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_size(reader: PdfReader) -> list[float]:
    box = reader.pages[0].mediabox
    return [float(box.width), float(box.height)]


def page_sizes(reader: PdfReader) -> list[list[float]]:
    return [[float(page.mediabox.width), float(page.mediabox.height)] for page in reader.pages]


def page_size_mismatches(source_sizes: list[list[float]], candidate_sizes: list[list[float]]) -> list[dict[str, object]]:
    return [
        {
            "page": index + 1,
            "source": source_sizes[index] if index < len(source_sizes) else None,
            "candidate": candidate_sizes[index] if index < len(candidate_sizes) else None,
        }
        for index in range(max(len(source_sizes), len(candidate_sizes)))
        if index >= len(source_sizes)
        or index >= len(candidate_sizes)
        or source_sizes[index] != candidate_sizes[index]
    ]


def font_inventory(reader: PdfReader) -> list[str]:
    names: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources", {})
        fonts = resources.get("/Font", {}) if resources else {}
        for font in fonts.values():
            name = font.get("/BaseFont")
            if name:
                names.add(str(name))
    return sorted(names)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "2002-ISDA-Master-Agreement.pdf")
    parser.add_argument("--candidate", type=Path, default=ROOT / "artifacts" / "isda-editable-candidate.pdf")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "isda-editable-comparison.json")
    args = parser.parse_args()
    source = args.source.resolve()
    candidate = args.candidate.resolve()
    manifest = candidate_manifest_status(args.manifest.resolve() if args.manifest else None)
    source_reader = PdfReader(str(source))
    candidate_reader = PdfReader(str(candidate))
    source_pages = page_texts(source)
    candidate_pages = page_texts(candidate)
    source_text = " ".join(source_pages).strip()
    candidate_text = " ".join(candidate_pages).strip()
    page_metrics = page_text_metrics(source_pages, candidate_pages)
    page_scores = [metric["similarity"] for metric in page_metrics]
    source_sizes = page_sizes(source_reader)
    candidate_sizes = page_sizes(candidate_reader)
    geometry_mismatches = page_size_mismatches(source_sizes, candidate_sizes)
    report = {
        "status": "diagnostic-pending-review",
        "source": {"path": str(source), "sha256": sha256(source), "pages": len(source_reader.pages), "page_size_pt": page_size(source_reader)},
        "candidate": {"path": str(candidate), "sha256": sha256(candidate), "bytes": candidate.stat().st_size, "pages": len(candidate_reader.pages), "page_size_pt": page_size(candidate_reader), "font_names": font_inventory(candidate_reader)},
        "candidate_manifest": manifest,
        "normalized_text_similarity": round(SequenceMatcher(None, source_text, candidate_text).ratio(), 4),
        "page_count_match": len(source_pages) == len(candidate_pages),
        "page_size_match": not geometry_mismatches,
        "page_size_mismatches": geometry_mismatches,
        "page_text_similarity_summary": {
            "pages_compared": len(page_metrics),
            "minimum": min(page_scores) if page_scores else None,
            "maximum": max(page_scores) if page_scores else None,
            "mean": round(sum(page_scores) / len(page_scores), 4) if page_scores else None,
        },
        "page_text_similarity": page_metrics,
        "visual_comparison": None,
        "visual_comparison_status": visual_comparison_status(),
        "native_reader_review": "pending",
        "second_engine_review": "pending",
        "limitations": [
            "Text extraction does not establish glyph coverage, coordinates, wrapping or visual equivalence.",
            "Font object names do not establish licensing, shaping or native-reader behavior.",
            "The locked source PDF is comparison input only and is not candidate document content.",
        ],
    }
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
