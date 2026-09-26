import importlib.util
from pathlib import Path

from app.calibration import CalibrationProfileError, apply_profile, validate_profile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("benchmark_extraction", ROOT / "scripts" / "benchmark_extraction.py")
benchmark = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(benchmark)


def test_benchmark_reports_each_schema_and_field_accuracy():
    records = benchmark._read_corpus(ROOT / "backend" / "tests" / "fixtures" / "extraction_benchmark.jsonl")
    report = benchmark.build_report(records)
    assert report["documents"] == 4
    assert set(report["schemas"]) == {"invoice", "receipt", "purchase-order"}
    assert all(report["schemas"][schema_id]["normalized_accuracy"] == 1
               for schema_id in ("receipt", "purchase-order"))
    assert report["schemas"]["invoice"]["table_row_accuracy"] == 1
    assert report["schemas"]["invoice"]["table_column_accuracy"] == 1
    calibration = report["schemas"]["invoice"]["confidence_calibration"]
    assert calibration["samples"] == 4 and calibration["empirical_accuracy"] == 0.75
    assert len(calibration["reliability_bins"]) == 10
    assert calibration["reliability_bins"][3]["samples"] == 1
    assert calibration["reliability_bins"][9]["samples"] == 3
    assert report["schemas"]["invoice"]["table_confidence_calibration"]["samples"] == 4


def test_isotonic_profile_is_monotone_and_preserves_raw_confidence():
    profile_module = importlib.util.spec_from_file_location(
        "calibrate_extraction", ROOT / "scripts" / "calibrate_extraction.py")
    assert profile_module is not None and profile_module.loader is not None
    calibrate = importlib.util.module_from_spec(profile_module)
    profile_module.loader.exec_module(calibrate)
    profile = calibrate.build_profile(
        benchmark._read_corpus(ROOT / "backend" / "tests" / "fixtures" / "extraction_benchmark.jsonl"),
        "fixture", "a" * 64)
    assert profile["calibration_corpus"] == {"source": "fixture", "sha256": "a" * 64, "records": 4}
    mapping = profile["schemas"]["invoice"]["fields"]["invoice_number"]
    assert mapping["samples"] == 2
    assert all(left["calibrated"] <= right["calibrated"]
               for left, right in zip(mapping["points"], mapping["points"][1:]))
    result = {"schema_id": "invoice", "fields": {
        "invoice_number": {"confidence": 0.9, "normalized_value": "INV-42"}}, "tables": {}}
    calibrated = apply_profile(result, profile)
    assert calibrated["fields"]["invoice_number"]["raw_confidence"] == 0.9
    assert calibrated["confidence_calibration"]["applied"] is True
    assert result["fields"]["invoice_number"]["confidence"] == 0.9


def test_invalid_calibration_profile_is_rejected():
    try:
        validate_profile({"contract": "confidence-calibration-v1", "method": "isotonic",
                          "schemas": {"invoice": {"fields": {
                              "total": {"points": [{"raw": 0.8, "calibrated": 0.7},
                                                       {"raw": 0.4, "calibrated": 0.9}]}}}}})
    except CalibrationProfileError:
        pass
    else:
        raise AssertionError("unvalidated mapping was accepted")
