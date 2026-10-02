"""Capture bounded source-page text and origin measurements for ISDA calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "2002-ISDA-Master-Agreement.pdf")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "isda-source-measurements.json")
    args = parser.parse_args()
    source = args.source.resolve()
    reader = PdfReader(str(source))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        origins: list[dict[str, object]] = []
        text_parts: list[str] = []

        def visitor(text, cm, tm, font_dict, font_size):
            value = "".join(text).strip()
            if not value:
                return
            text_parts.append(value)
            if len(origins) < 5:
                origins.append({"x_pt": round(float(tm[4]), 2), "y_pt": round(float(tm[5]), 2), "text": value[:120]})

        page.extract_text(visitor_text=visitor)
        box = page.mediabox
        pages.append({
            "page": number,
            "page_size_pt": [float(box.width), float(box.height)],
            "extracted_text_chars": len(" ".join(text_parts)),
            "first_origins": origins,
            "method": "pypdf visitor text origins; provisional source-region evidence",
        })
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    report = {
        "status": "measurement-only",
        "source": {"path": str(source), "sha256": digest, "pages": len(reader.pages)},
        "limitations": [
            "Text origins are not glyph boxes or a visual comparison.",
            "Extraction can contain encoding, ordering and line-fragment artifacts.",
            "The measurements do not authorize source-PDF reuse as template content.",
        ],
        "pages": pages,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
