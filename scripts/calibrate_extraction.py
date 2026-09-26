"""Build an offline isotonic confidence profile from a labelled calibration corpus.

The calibration corpus must be separate from the evaluation corpus. This command
only emits a data profile; it never downloads models or changes application data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.calibration import validate_profile
from app.extraction import BUNDLED_SCHEMAS, ExtractionSchemaError, extract_local


def _fit_mapping(samples: list[tuple[float, float]]) -> dict[str, Any]:
    """Fit monotone block means with the pool-adjacent-violators algorithm."""
    if not samples:
        raise ValueError("a calibration mapping needs at least one sample")
    ordered = sorted((min(1.0, max(0.0, float(score))), min(1.0, max(0.0, float(correct))))
                     for score, correct in samples)
    blocks: list[dict[str, float]] = []
    for score, correct in ordered:
        blocks.append({"weight": 1.0, "raw": score, "calibrated": correct})
        while len(blocks) >= 2 and blocks[-2]["calibrated"] > blocks[-1]["calibrated"]:
            right = blocks.pop()
            left = blocks.pop()
            weight = left["weight"] + right["weight"]
            blocks.append({
                "weight": weight,
                "raw": (left["raw"] * left["weight"] + right["raw"] * right["weight"]) / weight,
                "calibrated": (left["calibrated"] * left["weight"] +
                                right["calibrated"] * right["weight"]) / weight,
            })
    points = [{"raw": block["raw"], "calibrated": block["calibrated"]} for block in blocks]
    if points[0]["raw"] > 0:
        points.insert(0, {"raw": 0.0, "calibrated": points[0]["calibrated"]})
    if points[-1]["raw"] < 1:
        points.append({"raw": 1.0, "calibrated": points[-1]["calibrated"]})
    return {"points": points, "samples": len(samples)}


def _add_sample(collection: dict[str, list[tuple[float, float]]], name: str,
                predicted: dict[str, Any] | None, expected: dict[str, Any]) -> None:
    if not isinstance(predicted, dict):
        score = 0.0
        correct = 0.0
    else:
        try:
            score = min(1.0, max(0.0, float(predicted.get("confidence", 0.0))))
        except (TypeError, ValueError):
            score = 0.0
        correct = float(predicted.get("normalized_value") == expected.get("normalized_value"))
    collection.setdefault(name, []).append((score, correct))


def build_profile(records: list[dict[str, Any]], source_name: str = "",
                  corpus_sha256: str | None = None) -> dict[str, Any]:
    field_samples: dict[str, dict[str, list[tuple[float, float]]]] = {}
    table_samples: dict[str, dict[str, dict[str, list[tuple[float, float]]]]] = {}
    for record in records:
        schema_id = str(record["schema_id"])
        schema = record.get("schema") or BUNDLED_SCHEMAS.get(schema_id)
        if not isinstance(schema, dict):
            raise TypeError(f"unknown schema {schema_id!r}; provide an inline schema")
        try:
            result = extract_local(record["page_model"], schema, str(record.get("locale", "en")))
        except ExtractionSchemaError as exc:
            raise ValueError(f"schema {schema_id!r} is invalid: {exc}") from exc
        expected_fields = record["expected"]["fields"]
        for name, expected in expected_fields.items():
            if not isinstance(expected, dict):
                raise TypeError(f"expected field {name!r} must be an object")
            _add_sample(field_samples.setdefault(schema_id, {}), name,
                        result.get("fields", {}).get(name), expected)
        for table_name, expected_table in (record["expected"].get("tables") or {}).items():
            expected_rows = expected_table.get("rows", [])
            predicted_rows = ((result.get("tables") or {}).get(table_name) or {}).get("rows", [])
            for row_index, expected_row in enumerate(expected_rows):
                predicted_fields = predicted_rows[row_index].get("fields", {}) if row_index < len(predicted_rows) else {}
                for column, expected_cell in expected_row.items():
                    _add_sample(table_samples.setdefault(schema_id, {}).setdefault(table_name, {}), column,
                                predicted_fields.get(column), expected_cell)
    schemas: dict[str, Any] = {}
    for schema_id in sorted(set(field_samples) | set(table_samples)):
        schemas[schema_id] = {"fields": {}, "tables": {}}
        for name, samples in field_samples.get(schema_id, {}).items():
            schemas[schema_id]["fields"][name] = _fit_mapping(samples)
        for table_name, columns in table_samples.get(schema_id, {}).items():
            schemas[schema_id]["tables"][table_name] = {"columns": {
                name: _fit_mapping(samples) for name, samples in columns.items()
            }}
    profile = {"contract": "confidence-calibration-v1", "method": "isotonic",
               "profile_id": hashlib.sha256((corpus_sha256 or source_name).encode("utf-8")).hexdigest()[:16]
               if (corpus_sha256 or source_name) else None,
               "calibration_corpus": {"source": source_name or None,
                                      "sha256": corpus_sha256,
                                      "records": len(records)},
               "schemas": schemas}
    validate_profile(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="labelled calibration JSONL corpus")
    parser.add_argument("--output", type=Path, default=Path("artifacts/extraction-calibration.json"))
    args = parser.parse_args()
    from benchmark_extraction import _read_corpus  # local sibling script
    corpus_bytes = args.input.read_bytes()
    records = _read_corpus(args.input)
    profile = build_profile(records, str(args.input), hashlib.sha256(corpus_bytes).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
