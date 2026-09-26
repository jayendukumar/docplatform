from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_license_workflow_fails_closed_and_uploads_evidence_after_failure():
    workflow = (ROOT / ".github" / "workflows" / "license-scan.yml").read_text(encoding="utf-8")
    assert "python scripts/check_licenses.py" in workflow
    assert "if: always()" in workflow
    assert "artifacts/" in workflow
    assert "dependency-sbom-and-licence-report" in workflow
