"""Check the checked-in dependency inventory and emit a machine-readable SBOM.

This is deliberately metadata-only: it does not infer approval from package
names, network lookups, or the presence of a source repository. Unknown and
compound expressions fail the strict allow-list check.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ALLOWED = {"MIT", "Apache-2.0", "OFL-1.1", "OFL"}
ALIASES = {"Apache License 2.0": "Apache-2.0", "Apache License, Version 2.0": "Apache-2.0"}


def normalized_license(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    return ALIASES.get(value, value)


def scan(inventory_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    findings: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    for item in inventory.get("components", []):
        raw = item.get("license_metadata")
        normalized = normalized_license(raw)
        allowed = normalized in ALLOWED
        if not allowed:
            findings.append({"name": item.get("name"), "version": item.get("version"),
                             "ecosystem": item.get("ecosystem"), "scope": item.get("scope"),
                             "license_metadata": raw, "reason": "unknown or outside allow-list"})
        licenses = []
        if normalized:
            licenses.append({"license": {"id": normalized}})
        components.append({"type": "library", "group": item.get("ecosystem"),
                           "name": item.get("name"), "version": item.get("version"),
                           "purl": f"pkg:{item.get('ecosystem')}/{item.get('name')}@{item.get('version')}",
                           "licenses": licenses, "properties": [
                               {"name": "docplatform.scope", "value": str(item.get("scope", ""))},
                               {"name": "docplatform.metadata_license", "value": str(raw)},
                           ]})
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"tools": [{"vendor": "docplatform", "name": "check_licenses.py"}],
                          "source": str(inventory_path)}, "components": components,
            "properties": [{"name": "docplatform.allow_list", "value": ",".join(sorted(ALLOWED))},
                           {"name": "docplatform.finding_count", "value": str(len(findings))}]}
    return sbom, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("docs/dependency-inventory.json"))
    parser.add_argument("--sbom", type=Path, default=Path("artifacts/sbom.cdx.json"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/license-report.json"))
    parser.add_argument("--allow-findings", action="store_true", help="write evidence without failing")
    args = parser.parse_args()
    sbom, findings = scan(args.inventory)
    args.sbom.parent.mkdir(parents=True, exist_ok=True)
    args.sbom.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps({"inventory": str(args.inventory), "allow_list": sorted(ALLOWED),
                                       "findings": findings}, indent=2) + "\n", encoding="utf-8")
    print(f"components={len(sbom['components'])} findings={len(findings)} sbom={args.sbom}")
    if findings:
        for finding in findings:
            print(f"disallowed: {finding['ecosystem']}:{finding['name']}=={finding['version']} ({finding['license_metadata']!r})")
    return 0 if not findings or args.allow_findings else 1


if __name__ == "__main__":
    sys.exit(main())
