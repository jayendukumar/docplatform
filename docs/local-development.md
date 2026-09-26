# Local development without Docker

The supported contributor path uses the repository Python environment and the Vite development server. PostgreSQL is still required for the full application; use the disposable Compose database or a local PostgreSQL instance.

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-test.lock
backend/.venv/Scripts/python -m uvicorn app.main:create_app --factory --app-dir backend --reload
npm --prefix frontend ci
npm --prefix frontend run dev -- --host 127.0.0.1
```

This is a development workflow, not an offline-install claim. PDF/OCR engines, fonts, models and database credentials remain deliberate operator configuration.

## Offline bundle input check

After loading the required images into the local Docker cache, run:

```powershell
python scripts/verify_offline_bundle.py
```

The command validates the bundle manifest, checks each required image with `docker image inspect`, and validates `compose.yaml`. It does not claim that installation was performed without network access; that requires an operator-run network-isolated install.

## Repository template sync

The manual `template-sync` workflow pushes JSON definitions under `templates/sync` through the API. Set the repository secret `DOCPLATFORM_SYNC_API_KEY`, then provide the platform base URL and comma-separated template IDs when dispatching the workflow. Repeated pushes create a new template version instead of replacing history. The workflow is deliberately manual and does not claim remote Git conflict resolution or signed-commit enforcement.

## Scheduled retention purge

The purge command is intentionally one-shot so it can run under an operator-owned scheduler and does not become an unbounded web-process daemon. Preview the deletion first:

```powershell
python scripts/purge_retention.py data/objects --days 30 --dry-run
```

For Linux, schedule the non-dry-run command with a system cron entry such as `17 2 * * * /srv/docplatform/backend/.venv/bin/python /srv/docplatform/scripts/purge_retention.py /srv/docplatform/data/objects --days 30 >> /var/log/docplatform-retention.log 2>&1`. On Windows, create a daily Task Scheduler action invoking `backend/.venv/Scripts/python.exe` with arguments `scripts/purge_retention.py data/objects --days 30`. Set separate schedules and retention values for upload and output roots when they are stored separately. The command currently covers local object storage; S3 lifecycle rules remain an operator responsibility.
