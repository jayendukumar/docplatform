"""Evaluate a confidence profile against a separate labelled JSONL corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.calibration import apply_profile, validate_profile  # noqa: E402
from app.extraction import BUNDLED_SCHEMAS, ExtractionSchemaError, extract_local  # noqa: E402
from benchmark_extraction import _read_corpus  # noqa: E402


def _metric(samples: list[tuple[float, float]]) -> dict[str, Any]:
    if not samples:
        return {"samples": 0, "accuracy": None, "brier_score": None,
                "absolute_calibration_error": None}
    accuracy = sum(correct for _, correct in samples) / len(samples)
    return {
        "samples": len(samples),
        "accuracy": accuracy,
        "brier_score": sum((confidence - correct) ** 2 for confidence, correct in samples) / len(samples),
        "absolute_calibration_error": sum(abs(confidence - correct)
                                           for confidence, correct in samples) / len(samples),
    }


def evaluate(records: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    """Compare raw and calibrated confidence on labelled records."""
    validate_profile(profile)
    by_schema: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(
        lambda: {"raw": [], "calibrated": []})
    for record in records:
        schema_id = str(record["schema_id"])
        schema = record.get("schema") or BUNDLED_SCHEMAS.get(schema_id)
        if not isinstance(schema, dict):
            raise ValueError(f"unknown schema {schema_id!r}; provide an inline schema")
        try:
            result = extract_local(record["page_model"], schema, str(record.get("locale", "en")))
        except ExtractionSchemaError as exc:
            raise ValueError(f"schema {schema_id!r} is invalid: {exc}") from exc
        calibrated = apply_profile(result, profile, schema_id)
        for name, expected in record["expected"]["fields"].items():
            predicted = result.get("fields", {}).get(name) or {}
            calibrated_field = calibrated.get("fields", {}).get(name) or {}
            correct = float(predicted.get("normalized_value") == expected.get("normalized_value"))
            by_schema[schema_id]["raw"].append((float(predicted.get("confidence", 0.0)), correct))
            by_schema[schema_id]["calibrated"].append(
                (float(calibrated_field.get("confidence", 0.0)), correct))
    schemas = {
        schema_id: {name: _metric(samples) for name, samples in sorted(values.items())}
        for schema_id, values in sorted(by_schema.items())
    }
    all_samples = {name: [sample for values in by_schema.values() for sample in values[name]]
                   for name in ("raw", "calibrated")}
    return {"contract": "confidence-calibration-evaluation-v1", "schemas": schemas,
            "overall": {name: _metric(samples) for name, samples in all_samples.items()},
            "profile_id": profile.get("profile_id")}


def ensure_separate_corpus(profile: dict[str, Any], evaluation_bytes: bytes) -> str:
    """Return the evaluation hash and reject exact calibration-corpus reuse."""
    evaluation_hash = hashlib.sha256(evaluation_bytes).hexdigest()
    calibration_hash = ((profile.get("calibration_corpus") or {}).get("sha256")
                        if isinstance(profile.get("calibration_corpus"), dict) else None)
    if calibration_hash and calibration_hash == evaluation_hash:
        raise ValueError("evaluation corpus must differ from the calibration corpus")
    return evaluation_hash


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path,
                        help="validated isotonic calibration profile JSON")
    parser.add_argument("--input", required=True, type=Path,
                        help="held-out labelled JSONL corpus")
    parser.add_argument("--output", type=Path, default=Path("artifacts/extraction-calibration-evaluation.json"))
    args = parser.parse_args()
    try:
        profile_bytes = args.profile.read_bytes()
        profile = json.loads(profile_bytes)
        if not isinstance(profile, dict):
            raise ValueError("profile must be a JSON object")
        evaluation_bytes = args.input.read_bytes()
        evaluation_hash = ensure_separate_corpus(profile, evaluation_bytes)
        report = evaluate(_read_corpus(args.input), profile)
        report["evaluation_corpus"] = {"source": str(args.input), "sha256": evaluation_hash}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
