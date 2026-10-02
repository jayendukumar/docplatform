"""Verify that the ISDA review checklist refers to the current candidate artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(checklist: Path, manifest_path: Path, comparison_path: Path) -> dict:
    text = checklist.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    source_hashes = re.findall(r"Locked source SHA-256: `([0-9a-f]{64})`", text)
    candidate_hashes = re.findall(r"Foreground candidate SHA-256: `([0-9a-f]{64})`", text)
    if len(source_hashes) != 1 or len(candidate_hashes) != 1:
        failures.append("checklist must contain exactly one source and candidate SHA-256")
    else:
        source_hash = source_hashes[0]
        candidate_hash = candidate_hashes[0]
        if comparison.get("source", {}).get("sha256") != source_hash:
            failures.append("checklist source hash does not match comparison report")
        if comparison.get("candidate", {}).get("sha256") != candidate_hash:
            failures.append("checklist candidate hash does not match comparison report")
        candidate_path = Path(comparison.get("candidate", {}).get("path", ""))
        if not candidate_path.is_absolute():
            candidate_path = ROOT / candidate_path
        if candidate_path.exists() and _sha256(candidate_path) != candidate_hash:
            failures.append("checklist candidate hash does not match candidate bytes")
    if manifest.get("locked_background") != "omitted":
        failures.append("foreground manifest does not declare locked_background: omitted")
    if comparison.get("candidate_manifest", {}).get("status") != "foreground-only":
        failures.append("comparison report is not foreground-only")
    if comparison.get("page_count_match") is not True or comparison.get("page_size_match") is not True:
        failures.append("comparison report does not have matching page count and size")

    return {
        "status": "pass" if not failures else "fail",
        "checklist": str(checklist),
        "manifest": str(manifest_path),
        "comparison": str(comparison_path),
        "candidate_object_count": manifest.get("objects"),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checklist", type=Path, default=ROOT / "docs" / "isda-review-evidence-checklist.md")
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts" / "isda-foreground-baseline" / "isda-foreground.json")
    parser.add_argument("--comparison", type=Path, default=ROOT / "artifacts" / "isda-editable-comparison.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.checklist, args.manifest, args.comparison)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
