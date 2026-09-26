"""Measure the bounded local render and extraction paths on the current CPU.

This is an evidence collector, not a sizing promise.  It deliberately exercises
the deterministic HTML renderer and the local label extractor only; OCR/layout
engines and final PDF output require their own engine-specific benchmarks.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.extraction import BUNDLED_SAMPLES, BUNDLED_SCHEMAS, extract_local  # noqa: E402
from app.rendering import render_definition  # noqa: E402


def _process_cpu_seconds() -> float | None:
    try:
        import resource
    except ImportError:
        return time.process_time()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def _measure(label: str, operation: Callable[[], Any], iterations: int) -> dict[str, Any]:
    elapsed: list[float] = []
    cpu: list[float] = []
    output_sizes: list[int] = []
    for _ in range(iterations):
        cpu_before = _process_cpu_seconds()
        start = time.perf_counter()
        result = operation()
        elapsed.append((time.perf_counter() - start) * 1000)
        cpu_after = _process_cpu_seconds()
        if cpu_before is not None and cpu_after is not None:
            cpu.append((cpu_after - cpu_before) * 1000)
        output_sizes.append(len(json.dumps(result, ensure_ascii=False)))
    return {
        "operation": label,
        "iterations": iterations,
        "elapsed_ms": {
            "min": min(elapsed),
            "median": statistics.median(elapsed),
            "max": max(elapsed),
        },
        "cpu_ms": {
            "min": min(cpu),
            "median": statistics.median(cpu),
            "max": max(cpu),
        } if cpu else None,
        "serialized_result_bytes": {"min": min(output_sizes), "max": max(output_sizes)},
    }


def build_report(iterations: int = 3) -> dict[str, Any]:
    if iterations < 1 or iterations > 100:
        raise ValueError("iterations must be between 1 and 100")

    invoice = BUNDLED_SAMPLES["invoice"]
    definition = {
        "name": "CPU benchmark",
        "locale": invoice["locale"],
        "sample_data": invoice["expected"]["fields"],
        "blocks": [
            {"type": "text", "text": "Invoice {{invoice_number}}"},
            {"type": "text", "text": "Total {{total}}"},
        ],
    }
    page_model = invoice["page_model"]
    schema = BUNDLED_SCHEMAS["invoice"]
    operations = [
        _measure("deterministic-html-render", lambda: render_definition(definition), iterations),
        _measure("local-label-extraction", lambda: extract_local(page_model, schema, invoice["locale"]), iterations),
    ]
    return {
        "contract": "cpu-pipeline-benchmark-v1",
        "status": "observed-candidate-paths",
        "iterations": iterations,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or None,
            "logical_cpu_count": os.cpu_count(),
        },
        "operations": operations,
        "scope": {
            "rendering": "deterministic HTML candidate only",
            "extraction": "local label extractor only",
            "excluded": ["Docling layout", "PaddleOCR", "Tesseract", "PDF engine", "native-reader review"],
            "minimum_hardware": "not derived",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("artifacts/cpu-pipeline-benchmark.json"))
    args = parser.parse_args()
    try:
        report = build_report(args.iterations)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
