"""Standalone durable-job worker for independently scalable job pools."""
from __future__ import annotations

import os
import signal
import socket
import sys
import threading
from uuid import uuid4

from app.config import load_settings
from app.database import create_database
from app.jobs import claim_next
from app.main import create_app
from app.storage import create_store


def main() -> int:
    kind = (os.environ.get("DOCPLATFORM_WORKER_KIND") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip().lower()
    if kind not in {"render", "extraction"}:
        raise SystemExit("DOCPLATFORM_WORKER_KIND must be render or extraction")
    # Worker identity is a process selector, not an application setting.
    # Remove it before the strict configuration loader validates DOCPLATFORM_*.
    os.environ.pop("DOCPLATFORM_WORKER_KIND", None)
    settings = load_settings()
    engine = create_database(settings)
    # Constructing the app supplies the shared, validated executor. Its HTTP
    # lifespan is not entered, so this process does not start embedded threads.
    app = create_app(settings=settings, engine=engine, store=create_store(settings))
    execute_job = app.state.execute_job
    stopping = threading.Event()

    def stop(*_args):
        stopping.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    worker_id = f"service-{kind}-{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:8]}"
    try:
        while not stopping.is_set():
            try:
                with engine.begin() as connection:
                    job = claim_next(connection, worker_id, kind)
                if job is not None:
                    try:
                        execute_job(job, worker_id)
                    except Exception:  # noqa: BLE001, S112
                        # The executor records failure; keep the pool alive for
                        # later jobs and let the lease contract handle crashes.
                        continue
                else:
                    stopping.wait(settings.job_worker_poll_seconds)
            except Exception:  # noqa: BLE001
                # A transient database/network error must not terminate a pool.
                stopping.wait(settings.job_worker_poll_seconds)
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
