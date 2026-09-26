"""Measure render throughput with one and two Compose render workers.

This is an operator-run local load test. It exercises the real API, PostgreSQL
queue, standalone render-worker services, and isolated render child. It is not
a general capacity promise and does not infer multi-host or autoscaling limits.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def _request(base_url: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, method=method,
                      headers={"content-type": "application/json"} if body else {})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _scale(base_url: str, count: int) -> None:
    port = str(urlsplit(base_url).port or 8000)
    environment = dict(os.environ)
    environment["PLATFORM_HTTP_PORT"] = port
    subprocess.run(["docker", "compose", "up", "-d", "--scale", f"render-worker={count}"],
                   cwd=ROOT, env=environment, check=True, stdout=subprocess.DEVNULL)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if _request(base_url, "/health/ready").get("status") == "ready":
                return
        except Exception:  # noqa: BLE001, S110 - retry while Compose starts
            pass
        time.sleep(1)
    raise RuntimeError("Compose service did not become ready after scaling")


def _create_template(base_url: str, blocks: int) -> str:
    definition = {"name": "Compose worker throughput benchmark",
                  "blocks": [{"type": "text", "text": f"Load block {index}: {{{{name}}}}"}
                             for index in range(blocks)]}
    created = _request(base_url, "/api/templates", "POST",
                       {"name": definition["name"], "definition": definition})
    _request(base_url, f"/api/templates/{created['id']}/publish/{created['version_id']}", "POST", {})
    return str(created["id"])


def _measure(base_url: str, template_id: str, jobs: int) -> float:
    ids = []
    started = time.monotonic()
    for index in range(jobs):
        queued = _request(base_url, "/api/jobs", "POST", {
            "kind": "render", "template_id": template_id, "data": {"name": f"Load-{index}"},
        })
        ids.append(str(queued["id"]))
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        with ThreadPoolExecutor(max_workers=min(16, len(ids))) as pool:
            states = list(pool.map(lambda job_id: _request(base_url, f"/api/jobs/{job_id}"), ids))
        if any(item["status"] == "failed" for item in states):
            raise RuntimeError("worker benchmark job failed")
        if all(item["status"] == "done" for item in states):
            return round(time.monotonic() - started, 3)
        time.sleep(0.25)
    raise RuntimeError("worker benchmark timed out")


def run(base_url: str, jobs: int, blocks: int, repeats: int = 3) -> dict:
    if jobs < 2 or jobs > 100 or blocks < 1 or blocks > 500 or repeats < 1 or repeats > 7:
        raise ValueError("jobs must be 2..100, blocks must be 1..500, and repeats must be 1..7")
    template_id = _create_template(base_url, blocks)
    samples: dict[str, list[float]] = {}
    warmup: dict[str, float] = {}
    for count in (1, 2):
        _scale(base_url, count)
        warmup[str(count)] = _measure(base_url, template_id, jobs)
        samples[str(count)] = [_measure(base_url, template_id, jobs) for _ in range(repeats)]
    medians = {count: round(median(values), 3) for count, values in samples.items()}
    return {"contract": "compose-worker-throughput-v1", "status": "observed",
            "base_url": base_url, "template_id": template_id, "jobs": jobs,
            "blocks_per_template": blocks, "repeats": repeats,
            "warmup_elapsed_seconds": warmup, "sample_elapsed_seconds": samples,
            "median_elapsed_seconds": medians,
            "two_workers_faster": medians["2"] < medians["1"],
            "scope": {"workload": "queued deterministic HTML renders",
                      "excluded": ["multi-host scaling", "autoscaling", "PDF/OCR throughput"]}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--blocks", type=int, default=80)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("artifacts/compose-worker-throughput.json"))
    args = parser.parse_args()
    report = run(args.base_url, args.jobs, args.blocks, args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
