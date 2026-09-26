import json
from pathlib import Path
import subprocess
import sys


def test_license_scan_fails_unknown_metadata_and_writes_sbom(tmp_path):
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"components": [
        {"ecosystem": "pypi", "scope": "runtime", "name": "allowed", "version": "1", "license_metadata": "MIT"},
        {"ecosystem": "pypi", "scope": "runtime", "name": "blocked", "version": "1", "license_metadata": "BSD-3-Clause"},
    ]}), encoding="utf-8")
    sbom = tmp_path / "sbom.json"
    report = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_licenses.py"
    command = [sys.executable, str(script), "--inventory", str(inventory),
               "--sbom", str(sbom), "--report", str(report)]
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode == 1
    assert sbom.is_file() and report.is_file()
    assert json.loads(report.read_text(encoding="utf-8"))["findings"][0]["name"] == "blocked"

    allowed = subprocess.run(command + ["--allow-findings"], capture_output=True, text=True)
    assert allowed.returncode == 0
