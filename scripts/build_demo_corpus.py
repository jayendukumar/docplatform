"""Build the checked-in starter-template verification corpus.

The corpus is deliberately generated from the same catalog and renderer used by
the API. It is a smoke/regression corpus for structure and binding completeness,
not a claim that the samples are legal, financial, tax or HR advice.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import STARTER_CATALOG, starter_definition  # noqa: E402
from app.rendering import render_definition  # noqa: E402


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    documents: list[dict] = []
    for starter_id, starter in STARTER_CATALOG.items():
        for language in starter["languages"]:
            definition = starter_definition(starter_id, language)
            rendered = render_definition(definition, definition["sample_data"], language, "error")
            slug = f"{starter_id}--{language}"
            (output / f"{slug}.json").write_text(
                json.dumps({"starter_id": starter_id, "category": starter["category"],
                            "language": language, "definition": definition,
                            "verification": {"missing_fields": rendered["missing_fields"],
                                             "missing_translations": rendered["missing_translations"],
                                             "scripts": rendered["scripts"]}},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (output / f"{slug}.html").write_text(rendered["artifact"], encoding="utf-8")
            documents.append({"id": slug, "starter_id": starter_id, "category": starter["category"],
                              "language": language, "blocks": len(definition["blocks"]),
                              "missing_fields": rendered["missing_fields"],
                              "missing_translations": rendered["missing_translations"],
                              "scripts": rendered["scripts"]})
    manifest = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                "catalog_size": len(STARTER_CATALOG), "document_count": len(documents),
                "documents": documents}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "demo-corpus" / "generated")
    args = parser.parse_args()
    result = build(args.output)
    print(f"Generated {result['document_count']} documents for {result['catalog_size']} starters in {args.output}")
