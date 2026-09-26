"""Run the local extraction benchmark against an explicit labelled JSONL corpus.

The corpus is intentionally supplied by the caller. This script measures the
current extractor; it does not train, calibrate, or manufacture labels.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.extraction import BUNDLED_SCHEMAS, ExtractionSchemaError, extract_local  # noqa: E402


def _reliability_bins(outcomes: list[tuple[float, float]]) -> list[dict[str, Any]]:
    """Return ten fixed confidence bins with observed accuracy."""
    bins = []
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10
        selected = [outcome for outcome in outcomes
                    if lower <= outcome[0] < upper or (index == 9 and outcome[0] == 1)]
        bins.append({
            "lower": lower, "upper": upper,
            "samples": len(selected),
            "mean_confidence": (sum(item[0] for item in selected) / len(selected)
                                 if selected else None),
            "empirical_accuracy": (sum(item[1] for item in selected) / len(selected)
                                    if selected else None),
        })
    return bins


def _read_corpus(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: record must be an object")
        if not isinstance(record.get("schema_id"), str):
            raise ValueError(f"{path}:{line_number}: schema_id is required")
        if not isinstance(record.get("page_model"), dict):
            raise ValueError(f"{path}:{line_number}: page_model is required")
        expected = record.get("expected")
        if not isinstance(expected, dict) or not isinstance(expected.get("fields"), dict):
            raise ValueError(f"{path}:{line_number}: expected.fields is required")
        records.append(record)
    if not records:
        raise ValueError(f"{path}: corpus has no records")
    return records


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_schema: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "documents": 0, "fields_expected": 0, "normalized_matches": 0,
        "original_matches": 0, "missing_predictions": 0, "invalid_predictions": 0,
        "table_rows_expected": 0, "table_rows_exact_matches": 0,
        "table_columns_expected": 0, "table_column_matches": 0,
        "confidence_samples": 0, "confidence_sum": 0.0, "confidence_brier_sum": 0.0,
        "confidence_calibration_error_sum": 0.0,
        "confidence_outcomes": [],
        "table_confidence_samples": 0, "table_confidence_sum": 0.0,
        "table_confidence_brier_sum": 0.0, "table_confidence_calibration_error_sum": 0.0,
        "table_confidence_outcomes": [],
        "fields": {},
    })
    for record in records:
        schema_id = record["schema_id"]
        schema = BUNDLED_SCHEMAS.get(schema_id)
        if schema is None and not isinstance(record.get("schema"), dict):
            raise ValueError(f"unknown schema {schema_id!r}; provide an inline schema")
        schema = record.get("schema") or schema
        try:
            result = extract_local(record["page_model"], schema, str(record.get("locale", "en")))
        except ExtractionSchemaError as exc:
            raise ValueError(f"schema {schema_id!r} is invalid: {exc}") from exc
        summary = by_schema[schema_id]
        summary["documents"] += 1
        for field_name, expected in record["expected"]["fields"].items():
            if not isinstance(expected, dict):
                raise ValueError(f"expected field {field_name!r} must be an object")
            summary["fields_expected"] += 1
            field_summary = summary["fields"].setdefault(field_name, {
                "expected": 0, "normalized_matches": 0, "original_matches": 0,
                "missing_predictions": 0,
                "confidence_samples": 0, "confidence_sum": 0.0, "confidence_brier_sum": 0.0,
                "confidence_calibration_error_sum": 0.0,
            })
            field_summary["expected"] += 1
            predicted = result.get("fields", {}).get(field_name)
            if not isinstance(predicted, dict):
                summary["missing_predictions"] += 1
                field_summary["missing_predictions"] += 1
                confidence = 0.0
                correct = 0.0
            else:
                correct = float(predicted.get("normalized_value") == expected.get("normalized_value"))
                try:
                    confidence = min(1.0, max(0.0, float(predicted.get("confidence", 0.0))))
                except (TypeError, ValueError):
                    confidence = 0.0
                if predicted.get("normalized_value") == expected.get("normalized_value"):
                    summary["normalized_matches"] += 1
                    field_summary["normalized_matches"] += 1
                if predicted.get("original_value") == expected.get("original_value"):
                    summary["original_matches"] += 1
                    field_summary["original_matches"] += 1
                if predicted.get("validation"):
                    summary["invalid_predictions"] += 1
            summary["confidence_samples"] += 1
            summary["confidence_sum"] += confidence
            summary["confidence_brier_sum"] += (confidence - correct) ** 2
            summary["confidence_calibration_error_sum"] += abs(confidence - correct)
            summary["confidence_outcomes"].append((confidence, correct))
            field_summary["confidence_samples"] += 1
            field_summary["confidence_sum"] += confidence
            field_summary["confidence_brier_sum"] += (confidence - correct) ** 2
            field_summary["confidence_calibration_error_sum"] += abs(confidence - correct)
            if not isinstance(predicted, dict):
                continue
        for table_name, expected_table in (record["expected"].get("tables") or {}).items():
            if not isinstance(expected_table, dict) or not isinstance(expected_table.get("rows"), list):
                raise ValueError(f"expected table {table_name!r} must contain rows")
            predicted_rows = ((result.get("tables") or {}).get(table_name) or {}).get("rows", [])
            for row_index, expected_row in enumerate(expected_table["rows"]):
                if not isinstance(expected_row, dict):
                    raise ValueError(f"expected row {table_name}[{row_index}] must be an object")
                summary["table_rows_expected"] += 1
                predicted_fields = predicted_rows[row_index].get("fields", {}) if row_index < len(predicted_rows) else {}
                row_normalized_match = True
                for column_name, expected_cell in expected_row.items():
                    if not isinstance(expected_cell, dict):
                        raise ValueError(f"expected cell {table_name}[{row_index}].{column_name} must be an object")
                    summary["table_columns_expected"] += 1
                    predicted_cell = predicted_fields.get(column_name)
                    cell_correct = float(isinstance(predicted_cell, dict)
                                         and predicted_cell.get("normalized_value") == expected_cell.get("normalized_value"))
                    try:
                        cell_confidence = min(1.0, max(0.0, float((predicted_cell or {}).get("confidence", 0.0))))
                    except (TypeError, ValueError):
                        cell_confidence = 0.0
                    summary["table_confidence_samples"] += 1
                    summary["table_confidence_sum"] += cell_confidence
                    summary["table_confidence_brier_sum"] += (cell_confidence - cell_correct) ** 2
                    summary["table_confidence_calibration_error_sum"] += abs(cell_confidence - cell_correct)
                    summary["table_confidence_outcomes"].append((cell_confidence, cell_correct))
                    if not isinstance(predicted_cell, dict) or predicted_cell.get("normalized_value") != expected_cell.get("normalized_value"):
                        row_normalized_match = False
                    else:
                        summary["table_column_matches"] += 1
                if row_normalized_match and expected_row:
                    summary["table_rows_exact_matches"] += 1
    for summary in by_schema.values():
        total = summary["fields_expected"]
        summary["normalized_accuracy"] = summary["normalized_matches"] / total if total else None
        summary["original_accuracy"] = summary["original_matches"] / total if total else None
        row_total = summary["table_rows_expected"]
        column_total = summary["table_columns_expected"]
        summary["table_row_accuracy"] = (summary["table_rows_exact_matches"] / row_total
                                           if row_total else None)
        summary["table_column_accuracy"] = (summary["table_column_matches"] / column_total
                                               if column_total else None)
        samples = summary["confidence_samples"]
        summary["confidence_calibration"] = {
            "samples": samples,
            "mean_confidence": summary["confidence_sum"] / samples if samples else None,
            "empirical_accuracy": summary["normalized_accuracy"],
            "brier_score": summary["confidence_brier_sum"] / samples if samples else None,
            "absolute_calibration_error": summary["confidence_calibration_error_sum"] / samples if samples else None,
            "reliability_bins": _reliability_bins(summary["confidence_outcomes"]),
        }
        table_samples = summary["table_confidence_samples"]
        summary["table_confidence_calibration"] = {
            "samples": table_samples,
            "mean_confidence": summary["table_confidence_sum"] / table_samples if table_samples else None,
            "empirical_accuracy": summary["table_column_accuracy"],
            "brier_score": summary["table_confidence_brier_sum"] / table_samples if table_samples else None,
            "absolute_calibration_error": summary["table_confidence_calibration_error_sum"] / table_samples if table_samples else None,
            "reliability_bins": _reliability_bins(summary["table_confidence_outcomes"]),
        }
        for field in summary["fields"].values():
            field["normalized_accuracy"] = field["normalized_matches"] / field["expected"] if field["expected"] else None
            field["original_accuracy"] = field["original_matches"] / field["expected"] if field["expected"] else None
            field_samples = field["confidence_samples"]
            field["confidence_calibration"] = {
                "samples": field_samples,
                "mean_confidence": field["confidence_sum"] / field_samples if field_samples else None,
                "empirical_accuracy": field["normalized_accuracy"],
                "brier_score": field["confidence_brier_sum"] / field_samples if field_samples else None,
                "absolute_calibration_error": field["confidence_calibration_error_sum"] / field_samples if field_samples else None,
            }
    return {"contract": "extraction-benchmark-v1", "documents": len(records),
            "schemas": dict(sorted(by_schema.items()))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="labelled JSONL corpus")
    parser.add_argument("--output", type=Path, default=Path("artifacts/extraction-benchmark.json"))
    args = parser.parse_args()
    try:
        report = build_report(_read_corpus(args.input))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
