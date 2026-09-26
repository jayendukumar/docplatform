import importlib.util
import hashlib
import io
import json
import os
import tarfile
import time
from pathlib import Path
from urllib.error import HTTPError

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("sync_templates", ROOT / "scripts" / "sync_templates.py")
assert SPEC and SPEC.loader
sync_templates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_templates)
BACKUP_SPEC = importlib.util.spec_from_file_location("backup_restore", ROOT / "scripts" / "backup_restore.py")
assert BACKUP_SPEC and BACKUP_SPEC.loader
backup_restore = importlib.util.module_from_spec(BACKUP_SPEC)
BACKUP_SPEC.loader.exec_module(backup_restore)
RETENTION_SPEC = importlib.util.spec_from_file_location("purge_retention", ROOT / "scripts" / "purge_retention.py")
assert RETENTION_SPEC and RETENTION_SPEC.loader
purge_retention = importlib.util.module_from_spec(RETENTION_SPEC)
RETENTION_SPEC.loader.exec_module(purge_retention)
OFFLINE_SPEC = importlib.util.spec_from_file_location("verify_offline_bundle", ROOT / "scripts" / "verify_offline_bundle.py")
assert OFFLINE_SPEC and OFFLINE_SPEC.loader
verify_offline = importlib.util.module_from_spec(OFFLINE_SPEC)
OFFLINE_SPEC.loader.exec_module(verify_offline)


class Response:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


def test_repository_sync_creates_missing_template(monkeypatch):
    calls = []

    def fake_urlopen(request):
        calls.append((request.full_url, request.method, request.data))
        if request.full_url.endswith("/api/templates/repo-template"):
            raise HTTPError(request.full_url, 404, "missing", {}, None)
        return Response({"id": "repo-template", "version_id": "repo-template-v1"})

    monkeypatch.setattr(sync_templates.urllib.request, "urlopen", fake_urlopen)
    result = sync_templates.push_definition("http://platform", "repo-template", {"name": "Repo", "blocks": []})

    assert result == "repo-template"
    assert calls[-1][0].endswith("/api/templates")
    assert calls[-1][1] == "POST"
    assert json.loads(calls[-1][2])["id"] == "repo-template"


def test_repository_sync_updates_existing_template_version(monkeypatch):
    calls = []

    def fake_urlopen(request):
        calls.append((request.full_url, request.method, request.data))
        if request.full_url.endswith("/api/templates/repo-template"):
            return Response({"id": "repo-template"})
        return Response({"id": "repo-template-v2", "version": 2})

    monkeypatch.setattr(sync_templates.urllib.request, "urlopen", fake_urlopen)
    result = sync_templates.push_definition("http://platform", "repo-template", {"name": "Repo", "blocks": []})

    assert result == "repo-template-v2"
    assert calls[0][1] == "GET"
    assert calls[1][0].endswith("/api/templates/repo-template/versions")
    assert calls[1][1] == "POST"
    assert json.loads(calls[1][2])["change_summary"] == "Repository sync"


def test_repository_sync_pull_writes_exported_definition_and_preserves_api_key(monkeypatch, tmp_path):
    definition = {"name": "Portable", "blocks": [{"type": "text", "text": "Hello"}]}
    archive_buffer = io.BytesIO()
    with sync_templates.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"format": "docplatform-template-v1"}))
        archive.writestr("definition.json", json.dumps(definition, ensure_ascii=False))
    calls = []

    class BinaryResponse(Response):
        def __init__(self, body: bytes):
            self.body = body

    def fake_urlopen(request):
        calls.append((request.full_url, request.get_method(), dict(request.header_items())))
        return BinaryResponse(archive_buffer.getvalue())

    monkeypatch.setattr(sync_templates.urllib.request, "urlopen", fake_urlopen)
    original = os.sys.argv
    try:
        os.sys.argv = ["sync_templates.py", "pull", str(tmp_path),
                       "--base-url", "http://platform", "--api-key", "secret",
                       "--template-id", "portable"]
        assert sync_templates.main() == 0
    finally:
        os.sys.argv = original

    assert calls == [("http://platform/api/templates/portable/export", "GET", {"X-api-key": "secret"})]
    assert json.loads((tmp_path / "portable.json").read_text(encoding="utf-8")) == definition
    with sync_templates.ZipFile(tmp_path / "portable.zip") as archive:
        assert set(archive.namelist()) == {"manifest.json", "definition.json"}


def test_backup_round_trip_writes_manifest_and_restores_objects(tmp_path, monkeypatch):
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "template.json").write_text('{"name":"Example"}', encoding="utf-8")
    archive = tmp_path / "backup.tar.gz"
    calls = []
    def fake_run(command, check):
        calls.append(command)
        if command[0] == "pg_dump":
            Path(command[command.index("--file") + 1]).write_bytes(b"database dump")
    monkeypatch.setattr(backup_restore.subprocess, "run", fake_run)

    backup_restore.create_backup(archive, objects, "postgresql://test")
    assert archive.exists()
    with tarfile.open(archive, "r:gz") as bundle:
        manifest = json.loads(bundle.extractfile("manifest.json").read())
        assert manifest["format"] == "docplatform-backup-v1"
        assert manifest["database_dump"]["sha256"]
        assert bundle.extractfile("objects/template.json").read() == b'{"name":"Example"}'

    restored = tmp_path / "restored" / "objects"
    backup_restore.restore_backup(archive, restored, "postgresql://test")
    assert (restored / "template.json").read_text(encoding="utf-8") == '{"name":"Example"}'
    assert calls[0][0] == "pg_dump"
    assert calls[1][0] == "pg_restore"


def test_backup_restore_rejects_a_mismatched_database_dump(tmp_path, monkeypatch):
    archive = tmp_path / "backup.tar.gz"
    archive.with_suffix(".dump").write_bytes(b"original dump")
    with tarfile.open(archive, "w:gz") as bundle:
        manifest = json.dumps({"format": "docplatform-backup-v1",
                               "database_dump": {"sha256": "0" * 64}}).encode()
        item = tarfile.TarInfo("manifest.json")
        item.size = len(manifest)
        import io
        bundle.addfile(item, io.BytesIO(manifest))
    monkeypatch.setattr(backup_restore.subprocess, "run", lambda *args, **kwargs: pytest.fail("restore must preflight the dump"))
    with pytest.raises(ValueError, match="checksum"):
        backup_restore.restore_backup(archive, tmp_path / "objects", "postgresql://test")


def test_backup_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        info = json.dumps({"format": "docplatform-backup-v1"}).encode()
        manifest = tarfile.TarInfo("manifest.json")
        manifest.size = len(info)
        import io
        bundle.addfile(manifest, io.BytesIO(info))
        malicious = tarfile.TarInfo("../outside.txt")
        malicious.size = 1
        bundle.addfile(malicious, io.BytesIO(b"x"))
    try:
        backup_restore.restore_backup(archive, tmp_path / "objects", "postgresql://test")
    except ValueError as error:
        assert "outside" in str(error)
    else:
        raise AssertionError("unsafe archive was accepted")


def test_retention_dry_run_does_not_delete_and_real_run_deletes(tmp_path, capsys):
    old = tmp_path / "old.bin"
    fresh = tmp_path / "fresh.bin"
    old.write_bytes(b"old")
    fresh.write_bytes(b"fresh")
    old_time = time.time() - 3 * 86400
    os.utime(old, (old_time, old_time))
    # Exercise the same CLI parser used by the operator command without shelling out.
    import sys
    original = sys.argv
    try:
        sys.argv = ["purge_retention.py", str(tmp_path), "--days", "1", "--dry-run"]
        purge_retention.main()
        assert old.exists()
        assert "old.bin" in capsys.readouterr().out
        sys.argv = ["purge_retention.py", str(tmp_path), "--days", "1"]
        purge_retention.main()
    finally:
        sys.argv = original
    assert not old.exists()
    assert fresh.exists()


def test_retention_does_not_delete_an_old_symlink_target(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"preserve")
    link = root / "link.bin"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation requires OS privilege")
    old_time = time.time() - 3 * 86400
    os.utime(outside, (old_time, old_time))
    assert purge_retention.expired_files(root, time.time() - 86400) == []
    assert link.is_symlink() and outside.read_bytes() == b"preserve"


def test_retention_rejects_a_missing_root(monkeypatch):
    import sys
    original = sys.argv
    try:
        sys.argv = ["purge_retention.py", "missing-root", "--days", "1"]
        with pytest.raises(SystemExit):
            purge_retention.main()
    finally:
        sys.argv = original


def test_helm_chart_declares_database_and_independent_worker_pools():
    chart = ROOT / "charts" / "docplatform"
    helpers = (chart / "templates" / "_helpers.tpl").read_text(encoding="utf-8")
    chart_metadata = (chart / "Chart.yaml").read_text(encoding="utf-8")
    worker = (chart / "templates" / "worker.yaml").read_text(encoding="utf-8")
    database = (chart / "templates" / "postgres.yaml").read_text(encoding="utf-8")
    web = (chart / "templates" / "web.yaml").read_text(encoding="utf-8")
    assert "kind: Deployment" in worker
    assert 'define "docplatform.name"' in helpers
    assert 'define "docplatform.labels"' in helpers
    assert 'apiVersion: v2' in chart_metadata and 'type: application' in chart_metadata
    assert "range $kind, $count := .Values.workers" in worker
    assert "app.worker_service" in worker
    assert "kind: StatefulSet" in database and "volumeClaimTemplates" in database
    assert "app.serve" in web


def test_local_development_guide_uses_factory_reload_and_vite_proxy():
    guide = (ROOT / "docs" / "local-development.md").read_text(encoding="utf-8")
    vite = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert "uvicorn app.main:create_app --factory --app-dir backend --reload" in guide
    assert "npm --prefix frontend run dev -- --host 127.0.0.1" in guide
    assert "proxy" in vite and "'/api'" in vite and "'/health'" in vite


def test_retention_guide_defines_dry_run_and_operator_schedules():
    guide = (ROOT / "docs" / "local-development.md").read_text(encoding="utf-8")
    assert "purge_retention.py data/objects --days 30 --dry-run" in guide
    assert "system cron" in guide
    assert "Task Scheduler" in guide
    assert "S3 lifecycle rules remain an operator responsibility" in guide


def test_offline_bundle_verifier_checks_manifest_and_compose(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "format": "docplatform-offline-bundle-v1",
        "required_images": ["docplatform:local"],
        "network_required_at_runtime": False,
        "fonts_and_models": "not bundled",
        "verification": ["docker image inspect docplatform:local"],
    }), encoding="utf-8")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(verify_offline.subprocess, "run", fake_run)
    assert verify_offline.verify_manifest(manifest) == []
    assert verify_offline.verify_compose(tmp_path / "compose.yaml") is None
    assert calls == [["docker", "image", "inspect", "docplatform:local"],
                     ["docker", "compose", "-f", str(tmp_path / "compose.yaml"), "config", "--quiet"]]


def test_offline_bundle_verifier_rejects_runtime_network_policy(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format": "docplatform-offline-bundle-v1",
                                    "required_images": ["docplatform:local"],
                                    "network_required_at_runtime": True}), encoding="utf-8")
    assert "runtime network policy must be false" in verify_offline.verify_manifest(manifest, inspect_images=False)


def test_offline_bundle_verifier_requires_explicit_asset_and_verification_contract(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format": "docplatform-offline-bundle-v1",
                                    "required_images": ["docplatform:local"],
                                    "network_required_at_runtime": False}), encoding="utf-8")
    errors = verify_offline.verify_manifest(manifest, inspect_images=False)
    assert "fonts_and_models must explicitly describe bundled or unbundled assets" in errors
    assert "verification must be a non-empty list" in errors


def test_offline_bundle_verifier_checks_declared_asset_hashes(tmp_path):
    asset = tmp_path / "fonts" / "sample.ttf"
    asset.parent.mkdir()
    asset.write_bytes(b"font fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format": "docplatform-offline-bundle-v1",
                                    "required_images": ["docplatform:local"],
                                    "network_required_at_runtime": False,
                                    "fonts_and_models": "bundled asset fixture",
                                    "assets": [{"path": "fonts/sample.ttf",
                                                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()}],
                                    "verification": ["sha256"]}), encoding="utf-8")
    assert verify_offline.verify_manifest(manifest, inspect_images=False) == []
    asset.write_bytes(b"wrong fixture")
    assert "assets[0].sha256 does not match: fonts/sample.ttf" in verify_offline.verify_manifest(manifest, inspect_images=False)


def test_offline_bundle_verifier_rejects_asset_path_escape(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"format": "docplatform-offline-bundle-v1",
                                    "required_images": ["docplatform:local"],
                                    "network_required_at_runtime": False,
                                    "fonts_and_models": "bundled asset fixture",
                                    "assets": [{"path": "../outside.ttf", "sha256": "0" * 64}],
                                    "verification": ["sha256"]}), encoding="utf-8")
    assert "assets[0].path escapes the manifest directory" in verify_offline.verify_manifest(manifest, inspect_images=False)


def test_template_sync_workflow_is_manual_and_secret_scoped():
    workflow = (ROOT / ".github" / "workflows" / "template-sync.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow
    assert "DOCPLATFORM_SYNC_API_KEY" in workflow
    assert "python scripts/sync_templates.py push" in workflow
    assert '--template-id "${{ inputs.template_ids }}"' in workflow
    assert "for template_id in" not in workflow
    assert "permissions:" in workflow and "contents: read" in workflow


def test_template_sync_normalizes_multiple_ids_and_rejects_path_values():
    assert sync_templates.normalize_template_ids(["one, two", "one"]) == ["one", "two"]
    with pytest.raises(ValueError, match="invalid template id"):
        sync_templates.normalize_template_ids(["../outside"])
