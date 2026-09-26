import base64
import json
import os
import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.jobs import claim_next, enqueue
from app.main import create_app
from app.models import Base
from app.storage import LocalStore
from app.worker import WorkerExecutionError, _sandbox_environment, run_isolated


def test_isolated_worker_timeout_is_killed_and_next_job_can_run(monkeypatch):
    class TimedOutProcess:
        pid = 1234
        returncode = None
        calls = 0

        def communicate(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("worker", kwargs.get("timeout", 1))
            return "", ""

        def poll(self):
            return None

    killed = []
    monkeypatch.setattr("app.worker.subprocess.Popen", lambda *args, **kwargs: TimedOutProcess())
    monkeypatch.setattr("app.worker._kill_process", lambda process: killed.append(process))
    with pytest.raises(WorkerExecutionError, match="wall-time"):
        run_isolated("render", {}, timeout_seconds=1, cpu_seconds=1, memory_bytes=16 * 1024 * 1024,
                     max_output_bytes=1024)
    assert len(killed) == 1

    class CompletedProcess:
        returncode = 0

        def communicate(self, *args, **kwargs):
            return json.dumps({"ok": True, "result": {"artifact": "next job"}}), ""

        def poll(self):
            return 0

    monkeypatch.setattr("app.worker.subprocess.Popen", lambda *args, **kwargs: CompletedProcess())
    assert run_isolated("render", {}, timeout_seconds=1, cpu_seconds=1, memory_bytes=16 * 1024 * 1024,
                        max_output_bytes=1024)["artifact"] == "next job"


def test_windows_worker_kill_terminates_descendants(monkeypatch):
    class Process:
        pid = 4321

        def kill(self):
            raise AssertionError("fallback process kill should not be used on Windows")

    calls = []
    monkeypatch.setattr("app.worker.os.name", "nt")
    monkeypatch.setattr("app.worker.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    from app.worker import _kill_process

    _kill_process(Process())

    assert calls == [((["taskkill", "/PID", "4321", "/T", "/F"],), {
        "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL, "check": False,
    })]


def test_isolated_worker_output_limit_terminates_child(monkeypatch):
    class OversizedProcess:
        returncode = 0

        def communicate(self, *args, **kwargs):
            return "x" * 2048, ""

        def poll(self):
            return None

    killed = []
    monkeypatch.setattr("app.worker.subprocess.Popen", lambda *args, **kwargs: OversizedProcess())
    monkeypatch.setattr("app.worker._kill_process", lambda process: killed.append(process))
    with pytest.raises(WorkerExecutionError, match="output exceeded"):
        run_isolated("render", {}, timeout_seconds=1, cpu_seconds=1, memory_bytes=16 * 1024 * 1024,
                     max_output_bytes=1024)
    assert len(killed) == 1


def test_parent_resource_watchdog_reports_memory_exhaustion(monkeypatch):
    class CompletedProcess:
        returncode = 0

        def communicate(self, *args, **kwargs):
            return json.dumps({"ok": True, "result": {"artifact": "unused"}}), ""

        def poll(self):
            return 0

    def fake_watch(process, cpu_seconds, memory_bytes, stopped, cpu_exceeded, memory_exceeded):
        memory_exceeded.append(True)

    monkeypatch.setattr("app.worker.subprocess.Popen", lambda *args, **kwargs: CompletedProcess())
    monkeypatch.setattr("app.worker._start_windows_resource_watchdog", fake_watch)
    with pytest.raises(WorkerExecutionError, match="memory limit"):
        run_isolated("render", {}, timeout_seconds=1, cpu_seconds=1,
                     memory_bytes=16 * 1024 * 1024, max_output_bytes=1024)


def test_real_isolated_worker_output_limit_does_not_poison_next_job():
    definition = {"blocks": [{"type": "text", "text": "x" * 80} for _ in range(100)]}
    with pytest.raises(WorkerExecutionError, match="output exceeded"):
        run_isolated("render", {"definition": definition, "data": {}}, timeout_seconds=5,
                     cpu_seconds=2, memory_bytes=64 * 1024 * 1024, max_output_bytes=1024)

    result = run_isolated("render", {"definition": {"blocks": [{"type": "text", "text": "after"}]},
                                     "data": {}}, timeout_seconds=5, cpu_seconds=2,
                          memory_bytes=64 * 1024 * 1024, max_output_bytes=4096)
    assert "after" in result["artifact"]


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX RLIMIT enforcement")
def test_posix_cpu_bound_engine_is_stopped_and_next_job_completes():
    runaway = [sys.executable, "-c", "while True: pass"]
    started = time.monotonic()
    with pytest.raises(WorkerExecutionError):
        run_isolated("ocr", {
            "data_base64": base64.b64encode(b"input").decode("ascii"),
            "command": runaway, "language": "eng", "timeout_seconds": 5,
        }, timeout_seconds=5, cpu_seconds=1, memory_bytes=256 * 1024 * 1024,
           max_output_bytes=4096)
    assert time.monotonic() - started < 5
    result = run_isolated("render", {"definition": {"blocks": [{"type": "text", "text": "after CPU"}]},
                                     "data": {}}, timeout_seconds=5, cpu_seconds=2,
                          memory_bytes=256 * 1024 * 1024, max_output_bytes=4096)
    assert "after CPU" in result["artifact"]


def test_isolated_worker_environment_excludes_credentials_and_import_overrides(monkeypatch):
    source = {
        "PATH": "/usr/bin", "TEMP": "/tmp", "LANG": "C",
        "DOCPLATFORM_DB_PASSWORD": "secret", "AWS_SECRET_ACCESS_KEY": "secret",
        "PYTHONPATH": "/untrusted", "HOME": "/home/user",
    }
    monkeypatch.setenv("DOCPLATFORM_DB_PASSWORD", "secret")
    filtered = _sandbox_environment(source)
    assert filtered == {"PATH": "/usr/bin", "TEMP": "/tmp", "LANG": "C"}
    assert "DOCPLATFORM_DB_PASSWORD" not in filtered
    assert "PYTHONPATH" not in filtered
    assert "HOME" not in filtered


def test_render_job_is_durable_and_pollable(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    with TestClient(create_app(engine=engine, store=store, frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "Job template", "definition": {
            "name": "Job template", "blocks": [{"type": "text", "text": "Hello {{name}}"}]}}).json()
        assert client.post(f"/api/templates/{created['id']}/publish/{created['version_id']}").status_code == 200
        queued = client.post("/api/jobs", json={"kind": "render", "template_id": created["id"],
                                               "data": {"name": "Ada"}})
        assert queued.status_code == 202
        job_id = queued.json()["id"]
        assert client.get(f"/api/jobs/{job_id}").json()["status"] == "queued"
        done = client.post(f"/api/jobs/{job_id}/run", json={"worker_id": "test-worker"})
        assert done.status_code == 200 and "Hello Ada" in done.json()["result"]["artifact"]
    # A new application instance can still poll the terminal record.
    with TestClient(create_app(engine=engine, store=store, frontend=tmp_path)) as client:
        persisted = client.get(f"/api/jobs/{job_id}")
        assert persisted.status_code == 200 and persisted.json()["status"] == "done"


def test_large_template_render_is_queued_while_small_render_is_synchronous(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    with TestClient(create_app(settings=Settings(sync_render_max_blocks=2), engine=engine,
                              store=store, frontend=tmp_path)) as client:
        small = client.post("/api/templates", json={"name": "Small", "definition": {
            "name": "Small", "blocks": [{"type": "text", "text": "small"}]}}).json()
        assert client.post(f"/api/templates/{small['id']}/publish/{small['version_id']}").status_code == 200
        assert client.post(f"/api/templates/{small['id']}/render", json={}).status_code == 200

        large = client.post("/api/templates", json={"name": "Large", "definition": {
            "name": "Large", "blocks": [{"type": "text", "text": str(index)} for index in range(3)]}}).json()
        assert client.post(f"/api/templates/{large['id']}/publish/{large['version_id']}").status_code == 200
        queued = client.post(f"/api/templates/{large['id']}/render", json={})
        assert queued.status_code == 202
        job_id = queued.json()["id"]
        assert client.get(f"/api/jobs/{job_id}").json()["status"] == "queued"
        completed = client.post(f"/api/jobs/{job_id}/run", json={"worker_id": "threshold-test"})
        assert completed.status_code == 200 and completed.json()["status"] == "done"


def test_job_kind_and_claim_errors_are_explicit(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        assert client.post("/api/jobs", json={"kind": "unknown"}).status_code == 422
        assert client.get("/api/jobs/missing").status_code == 404


def test_enabled_supervisor_resumes_queued_job_after_application_restart(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    settings = Settings(job_worker_enabled=False)
    with TestClient(create_app(settings=settings, engine=engine, store=store, frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "Restart job", "definition": {
            "name": "Restart job", "blocks": [{"type": "text", "text": "Hello {{name}}"}]}}).json()
        assert client.post(f"/api/templates/{created['id']}/publish/{created['version_id']}").status_code == 200
        queued = client.post("/api/jobs", json={"kind": "render", "template_id": created["id"],
                                               "data": {"name": "Restarted"}})
        assert queued.status_code == 202
        job_id = queued.json()["id"]
        assert client.get(f"/api/jobs/{job_id}").json()["status"] == "queued"
    with TestClient(create_app(settings=Settings(job_worker_enabled=True, job_worker_poll_seconds=0.1),
                              engine=engine, store=store, frontend=tmp_path)) as client:
        deadline = time.monotonic() + 5
        status = "queued"
        while time.monotonic() < deadline:
            status = client.get(f"/api/jobs/{job_id}").json()["status"]
            if status in {"done", "failed"}:
                break
            time.sleep(0.05)
        assert status == "done"
        assert "Hello Restarted" in client.get(f"/api/jobs/{job_id}").json()["result"]["artifact"]


def test_worker_claims_are_partitioned_by_job_kind(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        enqueue(connection, "render", {"value": 1}, "render-job")
        enqueue(connection, "extraction", {"value": 2}, "extraction-job")
        render = claim_next(connection, "render-worker", "render")
        extraction = claim_next(connection, "extraction-worker", "extraction")
    assert render and render["kind"] == "render"
    assert extraction and extraction["kind"] == "extraction"


def test_supervisor_starts_independent_configured_pool_counts(monkeypatch, tmp_path):
    started = []

    class FakeThread:
        def __init__(self, *, target, args, name, daemon):
            self.target = target
            self.args = args
            self.name = name
            self.daemon = daemon

        def start(self):
            started.append(self)

        def join(self, timeout=None):
            return None

    monkeypatch.setattr("app.main.threading.Thread", FakeThread)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(job_worker_enabled=True, job_worker_render_count=2,
                        job_worker_extraction_count=3, job_worker_poll_seconds=0.1)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)):
        pass

    assert [thread.name for thread in started] == [
        "docplatform-render-worker-1", "docplatform-render-worker-2",
        "docplatform-extraction-worker-1", "docplatform-extraction-worker-2",
        "docplatform-extraction-worker-3",
    ]
    assert [thread.args[0] for thread in started] == ["render", "render", "extraction", "extraction", "extraction"]


def test_render_worker_pool_load_completes_with_two_pool_sizes(tmp_path):
    """Exercise both real supervisor pool sizes without a host-sensitive timing claim.

    The repeatable throughput comparison lives in benchmark_compose_workers.py;
    this unit/integration test only verifies that both configured pool sizes
    drain real isolated jobs successfully.
    """
    database_path = (tmp_path / "worker-load.db").as_posix()
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")

    with TestClient(create_app(settings=Settings(job_worker_enabled=False), engine=engine,
                               store=store, frontend=frontend)) as client:
        created = client.post("/api/templates", json={"name": "Load test", "definition": {
            "name": "Load test", "blocks": [{"type": "text", "text": "Hello {{name}}"}]}}).json()
        assert client.post(f"/api/templates/{created['id']}/publish/{created['version_id']}").status_code == 200

    def run_batch(worker_count: int) -> float:
        settings = Settings(job_worker_enabled=True, job_worker_poll_seconds=0.06,
                            job_worker_render_count=worker_count, job_worker_extraction_count=0)
        with TestClient(create_app(settings=settings, engine=engine, store=store, frontend=frontend)) as client:
            job_ids = []
            for _ in range(6):
                response = client.post("/api/jobs", json={"kind": "render", "template_id": created["id"],
                                                           "data": {"name": "Load"}})
                assert response.status_code == 202
                job_ids.append(response.json()["id"])
            started = time.monotonic()
            deadline = started + 30
            statuses = set()
            while time.monotonic() < deadline:
                statuses = {client.get(f"/api/jobs/{job_id}").json()["status"] for job_id in job_ids}
                if statuses == {"done"}:
                    return time.monotonic() - started
                assert not (statuses & {"failed"}), statuses
                time.sleep(0.05)
            pytest.fail(f"worker load did not complete: {statuses}")

    one_worker_seconds = run_batch(1)
    two_worker_seconds = run_batch(2)
    assert one_worker_seconds > 0
    assert two_worker_seconds > 0
