import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("evaluate_calibration", ROOT / "scripts" / "evaluate_calibration.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _fixture_records():
    benchmark_spec = importlib.util.spec_from_file_location(
        "benchmark_extraction", ROOT / "scripts" / "benchmark_extraction.py")
    assert benchmark_spec is not None and benchmark_spec.loader is not None
    benchmark = importlib.util.module_from_spec(benchmark_spec)
    benchmark_spec.loader.exec_module(benchmark)
    return benchmark._read_corpus(ROOT / "backend" / "tests" / "fixtures" / "extraction_benchmark.jsonl")


def test_evaluation_reports_raw_and_calibrated_metrics_without_claiming_accuracy():
    calibrate_spec = importlib.util.spec_from_file_location(
        "calibrate_extraction", ROOT / "scripts" / "calibrate_extraction.py")
    assert calibrate_spec is not None and calibrate_spec.loader is not None
    calibrate = importlib.util.module_from_spec(calibrate_spec)
    calibrate_spec.loader.exec_module(calibrate)
    records = _fixture_records()
    profile = calibrate.build_profile(records, "calibration", "a" * 64)

    report = module.evaluate(records, profile)

    assert report["contract"] == "confidence-calibration-evaluation-v1"
    assert report["overall"]["raw"]["samples"] == 8
    assert report["overall"]["calibrated"]["samples"] == 8
    assert set(report["schemas"]) == {"invoice", "purchase-order", "receipt"}


def test_evaluation_rejects_reusing_calibration_corpus():
    import hashlib

    records = _fixture_records()
    corpus_bytes = b"held-out-corpus"
    profile = {"contract": "confidence-calibration-v1", "method": "isotonic",
               "schemas": {}, "calibration_corpus": {
                   "sha256": hashlib.sha256(corpus_bytes).hexdigest()}}
    try:
        module.ensure_separate_corpus(profile, corpus_bytes)
    except ValueError as exc:
        assert "differ" in str(exc)
    else:
        raise AssertionError("calibration corpus was accepted as held-out evaluation data")
