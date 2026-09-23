# E1 foundation: implementation and verification

Date: 2026-09-22. Scope: the six E1 MVP stories. The six R2 stories retain their original release. Source implementation is present; runtime dependency installation and behavioral testing are pending the licence exception in [DD-022](design-decisions.md). Do not interpret the commands below as evidence that they have run successfully.

## Story status

| Story | Implementation | Acceptance evidence / remaining work |
| --- | --- | --- |
| E1-01: one-command start | Compose PostgreSQL + one-shot bootstrap + application; React workspace and persistent sample template | Compose syntax passes; image build, fresh startup and browser verification pending |
| E1-02: configuration | One TOML file; typed DOCPLATFORM_ overrides; secret fields and sanitized errors | Configuration/redaction tests written, not run yet |
| E1-03: local/S3 storage | Shared bounded put/get/delete/check interface and both adapters | Same parameterized suite written for local and Moto-emulated S3, not run yet; live-provider conformance not claimed |
| E1-04: PostgreSQL/migrations | Two Alembic revisions, serialized upgrade, idempotent seed and schema-aware readiness | Fresh/upgrade/data-preservation/concurrency tests written for actual PostgreSQL, not run yet |
| E1-05: health/readiness | Application liveness/readiness and PostgreSQL native health probe | Outage/redaction tests written, not run yet |
| E1-06: CPU-only | CPU-only service definitions; no GPU runtime/devices; deployment guidance below | Partial: renderer/OCR do not exist yet, so their CPU execution and measured minimum hardware acceptance are pending E4/E8 |
| E1-07 through E1-12 | Scheduled R2 | No historical-release upgrades, Helm/offline bundle/backup/retention features claimed; contributor commands below are setup aids, not full E1-12 acceptance |

Implemented design choices and remaining approval/verification state are in DD-016 through DD-022. The original generated backlog is unchanged.

## Quickstart (after resolving dependency exceptions)

Prerequisites: Docker Engine with Compose v2.24+ (optional env_file support) or a compatible newer Compose release; initial registry network access. No local Node/Python installation is needed for the container application.

From the repository root:

```sh
docker compose up --build
```

For later starts with built images, `docker compose up` is sufficient. The first build installs pinned dependencies, creates the static UI, waits for PostgreSQL, applies migrations, checks storage and seeds the sample. `web` only starts after `migrate` succeeds.

- Workspace: `http://localhost:8000/`
- API explorer: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Templates: `http://localhost:8000/api/templates`
- Sample definition: `http://localhost:8000/api/templates/sample-welcome`
- Process liveness: `http://localhost:8000/health/live`
- Dependency readiness: `http://localhost:8000/health/ready`

The sample is a stored definition with sample data, not a generated document. Editing, rendering, OCR and authentication belong to their respective epics. Compose exposes only the application on host loopback; PostgreSQL has no host port in the normal stack. This is a local foundation environment, not an authenticated public deployment.

Persistent named volumes hold PostgreSQL data and objects. `docker compose down` stops/removes containers while preserving those volumes. Do not add `--volumes` unless you intend to erase local data. Container rebuilds do not overwrite an existing seeded template.

## Configuration

Normal precedence: built-in defaults < the selected TOML file < `DOCPLATFORM_` environment variables. `DOCPLATFORM_CONFIG_FILE` selects a file; explicitly missing files fail. With no selector, the application looks for repository-root `config.toml`. Unknown `DOCPLATFORM_` keys and unknown TOML fields fail closed. Relative local paths are relative to the TOML file's directory. Environment booleans use values such as `true`/`false`.

For Compose, copy `.env.example` to `.env` when overrides are needed. `.env` is ignored by source control and injected through Compose, not loaded implicitly by Python. `PLATFORM_CONFIG_PATH` changes the read-only mounted config file. Compose controls container bind host, application port, database connection location and object-volume path through explicit environment values; those take precedence over the mounted TOML. Container application port can be changed with `DOCPLATFORM_PORT`; `PLATFORM_HTTP_PORT` controls the host-facing port.

| TOML key | Environment key | Default / behavior |
| --- | --- | --- |
| `app_name` | `DOCPLATFORM_APP_NAME` | Document Platform; API title |
| `host` | `DOCPLATFORM_HOST` | 127.0.0.1 built-in; sample file/Compose use 0.0.0.0 inside container |
| `port` | `DOCPLATFORM_PORT` | 8000; 1-65535 |
| `log_level` | `DOCPLATFORM_LOG_LEVEL` | info; critical/error/warning/info only |
| `db_host` | `DOCPLATFORM_DB_HOST` | localhost; Compose overrides with database service |
| `db_port` | `DOCPLATFORM_DB_PORT` | 5432 |
| `db_name` | `DOCPLATFORM_DB_NAME` | docplatform |
| `db_user` | `DOCPLATFORM_DB_USER` | docplatform |
| `db_password` | `DOCPLATFORM_DB_PASSWORD` | docplatform-local, for local development only; secret |
| `db_connect_timeout_seconds` | `DOCPLATFORM_DB_CONNECT_TIMEOUT_SECONDS` | 5; 1-60; also bounds pool checkout |
| `storage_backend` | `DOCPLATFORM_STORAGE_BACKEND` | local or s3; default local |
| `local_storage_path` | `DOCPLATFORM_LOCAL_STORAGE_PATH` | data/objects; Compose fixes /data/objects to persistent volume |
| `s3_bucket` | `DOCPLATFORM_S3_BUCKET` | Required for s3; bucket must already exist |
| `s3_endpoint_url` | `DOCPLATFORM_S3_ENDPOINT_URL` | Optional HTTP(S) endpoint; default AWS service discovery; no credentials/query/fragment in URL |
| `s3_region` | `DOCPLATFORM_S3_REGION` | us-east-1 |
| `s3_prefix` | `DOCPLATFORM_S3_PREFIX` | docplatform; safe slash-separated namespace, empty allowed |
| `s3_addressing_style` | `DOCPLATFORM_S3_ADDRESSING_STYLE` | path; path/virtual/auto |
| `s3_access_key_id` | `DOCPLATFORM_S3_ACCESS_KEY_ID` | Optional secret; paired with secret access key |
| `s3_secret_access_key` | `DOCPLATFORM_S3_SECRET_ACCESS_KEY` | Optional secret |
| `s3_session_token` | `DOCPLATFORM_S3_SESSION_TOKEN` | Optional secret; requires explicit paired credentials |
| `s3_timeout_seconds` | `DOCPLATFORM_S3_TIMEOUT_SECONDS` | 5; connect and read timeout, 1-60 |
| `s3_max_attempts` | `DOCPLATFORM_S3_MAX_ATTEMPTS` | 2 total attempts, including initial call; 1-5 |
| `max_object_bytes` | `DOCPLATFORM_MAX_OBJECT_BYTES` | 10485760 (10 MiB); 1 byte to 1 GiB; foundation guard, not the eventual upload policy |
| `seed_sample` | `DOCPLATFORM_SEED_SAMPLE` | true; false skips sample creation |

Compose-only variables are `PLATFORM_HTTP_PORT` (8000), `PLATFORM_CONFIG_PATH` (./config.toml), and `PLATFORM_TEST_DB_PORT` (55432 in the test stack). PostgreSQL container initialization uses the same DOCPLATFORM_DB_NAME/USER/PASSWORD values. Changing a password environment value does not rotate the password already stored inside an existing database volume; perform an actual PostgreSQL credential rotation rather than deleting data.

For S3, supply an existing bucket and endpoint/region as needed, and either explicit credentials or an available boto3 credential provider (such as a role). AWS provider-chain variables are owned by boto3, not application TOML. Do not put credentials in endpoint URLs. Allow get/put/delete under the configured prefix, including the health subprefix. The application neither creates buckets nor changes IAM policies. A backend switch requires copying referenced objects; empty S3 storage cannot magically recover documents held on local disk.

Application configuration objects hide credential representations. Startup, API and readiness errors expose fixed messages rather than raw driver or S3 errors. HTTP access logging is disabled. Operator tools such as `docker inspect`, `docker compose config` without `--quiet`, shell environment dumps and debugging can still expose secrets; application redaction cannot sanitize those external tools.

## Health semantics

- `/health/live` means the HTTP process is alive; it does not query dependencies.
- `/health/ready` returns 200 only when PostgreSQL responds with the expected migration revision, a write/read/delete storage probe succeeds and the UI build exists. A failure returns 503 with dependency names and ready/unavailable states, never connection strings or raw errors.
- PostgreSQL uses `pg_isready` in Compose. It is a database service, not an HTTP server. Its probe is not a substitute for the application's schema readiness check.
- `migrate` is a one-shot service. Successful completion is its readiness gate; it has no long-lived HTTP endpoint.

Storage probes use unique temporary keys and clean up after themselves. They validate actual read/write/delete permissions and incur S3 calls. High S3 timeout/retry overrides can exceed the reference Docker healthcheck deadline; adapt orchestration healthcheck timing when changing those limits. A health check does not certify end-to-end document processing, since those engines are not implemented yet.

## CPU and hardware guidance

The current foundation needs no CUDA, GPU drivers or GPU passthrough. Docker definitions use ordinary CPU images. As an unbenchmarked starting allocation for development, reserve 2 CPU cores and 4 GiB RAM for Docker, with at least 5 GiB free space for images/build cache plus database and documents. This is a planning allocation, **not a measured minimum** and not an OCR sizing promise.

E1-06 remains partial until E4/E8 are implemented and run on CPU. At that point record CPU model, core/thread allocation, RAM limit, model/font versions, document languages, page count/resolution, cold/warm runtime and peak memory. Derive supported minimum hardware and concurrency from those measurements. Do not mark extraction/rendering CPU acceptance from an API smoke test.

## Verification commands (not yet executed)

Create a repository-local virtual environment and install the reviewed test lock only after DD-022 is resolved:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-test.lock
npm --prefix frontend ci
npm --prefix frontend run build
```

Run dependency-independent unit/adapter tests from the backend directory:

```powershell
Push-Location backend
../.venv/Scripts/python -m pytest -q -m "not integration"
../.venv/Scripts/python -m ruff check app tests
Pop-Location
```

The storage suite parameterizes the same cases over local disk and the real boto3 adapter using Moto's S3 emulator. That is contract verification, not a claim of testing every S3-compatible vendor.

Use the dedicated disposable PostgreSQL stack for integration tests:

```powershell
docker compose -f compose.test.yaml up -d --wait
$env:TEST_DB_PORT = "55432"
Push-Location backend
../.venv/Scripts/python -m pytest -q
Pop-Location
Remove-Item Env:TEST_DB_PORT
docker compose -f compose.test.yaml down
```

The fixture resets only the explicitly configured `docplatform_test` database, using dedicated credentials. Do not point it at a production database. Normal application volumes are separate. Its two migration revisions validate an upgrade path, not the source's R2 requirement to test two previous product releases.

For browser verification with the normal Compose application running:

```powershell
Push-Location frontend
npx playwright install chromium
npm run test:e2e
Pop-Location
```

A different application URL can be provided through `PLATFORM_TEST_URL`. Browser tests check real sample retrieval/navigation and narrow-screen overflow. Native-reader rendering review, full WCAG audit, real Safari coverage, hostile document processing and second-engineer sign-off are not claimed by these tests.

## Verification performed so far

- `python -m compileall -q backend` passed: Python syntax only.
- `docker compose config --quiet` passed: Compose model validation only.
- Registry dependency dry-runs completed; runtime/test locks and frontend package-lock generated.
- Node, Python and PostgreSQL image manifests were inspected and pinned.
- No application package installation, container build/start, pytest run, TypeScript build or browser run has been completed. Those require resolving DD-022 first.
