# Design decision register

Created: 2026-09-22. This file is the living record requested by the user. Record every design decision as implementation proceeds, including UI behavior, configuration defaults and dependency choices, not only high-level architecture.

## Recording rules

Use sequential IDs. Status is **Proposed**, **Accepted**, **Implemented**, **Rejected**, or **Superseded**. Accepted means adopted for the work, not tested or shipped. Record who or what establishes acceptance; never infer product approval from the existence of this file. A proposal can be explored without calling it final. Every implemented entry needs file references and actual validation results. Preserve previous reasoning and link replacement entries when superseding decisions.

For consequential decisions, record date, story IDs, context, choice, alternatives, consequences, validation, and implementation/evidence. Small reversible choices can share a dated batch entry if each choice and rationale is explicit. Mechanical edits can reference the existing decision. This register documents choices; it does not grant deployment, publishing or licensing authority.

## Current decisions

DD-001 through DD-015 preserve the original planning baseline. E1 implementation began later in this session; DD-016 through DD-022 record adopted foundation choices, prepared code and pending dependency/runtime validation. No application dependency has been installed yet. References to stack capabilities are linked in [the stack proposal](tech-stack.md); source requirements remain in [epics.md](epics.md).


| ID | Decision | Status |
| --- | --- | --- |
| DD-001 | Preserve source scope and keep project guidance with the repository | Implemented |
| DD-002 | Use a modular backend with isolated document workers | Proposed |
| DD-003 | Use React/TypeScript and a DOM-based ProseMirror editor | Proposed |
| DD-004 | Use Python/FastAPI and versioned contracts | Proposed |
| DD-005 | Persist relational metadata and immutable artifact versions | Proposed |
| DD-006 | Start with a PostgreSQL-backed durable job queue | Proposed |
| DD-007 | Choose PDF rendering from measured multilingual evidence | Proposed |
| DD-008 | Keep Word templates as a separate merge/conversion path | Proposed |
| DD-009 | Use a declarative template tree and bounded expression grammar | Proposed |
| DD-010 | Normalize engine output and retain field provenance | Proposed |
| DD-011 | Establish identity and approved-review snapshots early | Proposed |
| DD-012 | Separate networked orchestration from untrusted document execution | Proposed |
| DD-013 | Resolve the dependency licence conflict explicitly | Proposed |
| DD-014 | Use staged delivery and evidence-based release gates | Proposed |
| DD-015 | Defer AI, public ecosystem and hosted billing to their releases | Proposed |
| DD-016 | E1 MVP foundation scope | Accepted; verification pending |
| DD-017 | TOML configuration and sanitized errors | Accepted; verification pending |
| DD-018 | Shared local/S3 object storage | Accepted; verification pending |
| DD-019 | Serialized PostgreSQL migrations | Accepted; verification pending |
| DD-020 | Single-origin sample workspace | Accepted; verification pending |
| DD-021 | Pinned CPU foundation builds | Accepted; verification pending |
| DD-022 | Foundation licence exceptions | Accepted by user; implementation review pending |
| DD-026 | Deliver E3/E4 MVP contracts with a provisional deterministic renderer | Implemented; partial acceptance |

## DD-001: Preserve source scope and keep project guidance with the repository

- **Date:** 2026-09-22
- **Status:** Implemented
- **Scope:** All epics; user documentation/skills request

**Context:** The supplied DOCX is the only product artifact; future implementation must preserve its requirements and record choices.

**Choice:** Keep a faithful generated epics file, separate stack/delivery analysis and this appendable register. Add AGENTS.md routing to three focused skills in skills/. Use a standard-library DOCX extractor with a source checksum. Repository routing makes the skills usable without changing global configuration or claiming native menu registration.

**Alternatives:** Summary-only epics would lose acceptance criteria. Global skills would make project rules machine-specific. Native .agents/skills discovery is optional future setup rather than a prerequisite for file-based project guidance.

**Consequences:** The backlog conversion must be rerun when the original DOCX changes; analysis belongs outside generated text. Future agents must load applicable skill files through AGENTS.md.

**Validation:** Compare all six fields of every story against the DOCX, confirm 218 unique IDs and release totals, check internal links and validate each SKILL.md.

**Implementation/evidence:** Implemented in README.md, AGENTS.md, scripts/extract_backlog.py, docs/epics.md and skills/. Acceptance basis: the user explicitly requested backlog documentation, skills and an ongoing design log. Validation on 2026-09-22: all 218 unique story rows matched all six DOCX fields; release counts matched 91/67/30/30; 24 MVP L stories confirmed; all local Markdown links resolved; source checksum remained unchanged. All three skills passed direct checks of their simple frontmatter, naming, bodies and referenced files. The bundled quick_validate.py was attempted but could not run because PyYAML is absent; this is not a claim that its validation passed. No new dependency was installed. Native skill-menu registration and application tests were not performed.

## DD-002: Use a modular backend with isolated document workers

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E1, E7, E8, E11, E12

**Context:** One-command self-hosting must coexist with resource isolation for expensive untrusted document execution.

**Choice:** One repository, React SPA, modular FastAPI control plane and separate render/extraction worker supervisors. Sandbox document child processes independently from supervisors.

**Alternatives:** Microservices per epic increase deployment overhead; a single process for API and document parsing weakens failure isolation.

**Consequences:** Business contracts can be shared without network service sprawl. Worker protocol and process supervision still need explicit tests.

**Validation:** Compose smoke test, CPU-only execution, API responsiveness during a runaway job, and separate worker capacity tests.

**Implementation/evidence:** Not implemented; see tech-stack.md architecture.

## DD-003: Use React/TypeScript and a DOM-based ProseMirror editor

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E2, E4, E10, E14-04

**Context:** Complex-script text entry, keyboard use and a visual page designer must work together.

**Choice:** React/Vite SPA with ProseMirror text regions and a custom page/block layout model; CSS tokens/logical properties and i18next. Use TanStack Query for API state and PDF.js for final preview/source overlays.

**Alternatives:** Canvas-only editing risks text input/accessibility. A prebuilt PDF designer may reduce work but must first pass the same script and flow tests. Next.js adds server rendering without a demonstrated MVP need.

**Consequences:** Pagination, tables, alignment guides and undo across layout/text remain substantial engineering work. Interactive browser layout is not the final output oracle.

**Validation:** IME/caret/selection fixtures, keyboard-only editing, repeat-table pagination, and final-output preview checks.

**Implementation/evidence:** Not implemented; choices may change following E4-01/editor experiments.

## DD-004: Use Python/FastAPI and versioned contracts

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E1, E5, E7, E8, E9

**Context:** Docling and PaddleOCR make Python a natural processing runtime; the API must serve every UI operation.

**Choice:** FastAPI/Pydantic, generated OpenAPI and versioned JSON contracts. Keep domain logic independent of HTTP handlers. Select a supported Python version after checking the OCR dependency compatibility matrix.

**Alternatives:** Django/DRF offers more built-in administration; all-Node still requires bridging the named Python tools.

**Consequences:** Authentication/admin capabilities must be deliberately assembled and tested; generated API documentation alone does not establish compatible contracts.

**Validation:** OpenAPI drift tests, field-level error tests, adapter contracts and a compatible CPU-only dependency lock.

**Implementation/evidence:** Not implemented; runtime and package versions remain unselected.

## DD-005: Persist relational metadata and immutable artifact versions

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E1-03, E1-04, E3, E9, E10

**Context:** Template history, reviewed results and document files have different storage and consistency requirements.

**Choice:** PostgreSQL via SQLAlchemy/Alembic for metadata and bounded validated JSONB; local/S3 storage interface for binary artifacts. Published template and approved extraction snapshots are immutable. Portable bundles contain version manifests and relative immutable assets.

**Alternatives:** Binary files in database rows complicate size/backup behavior; a schemaless-only store weakens relational constraints. Required PostgreSQL rules out an unrecorded SQLite-only replacement.

**Consequences:** Garbage collection and backup must coordinate database references and stored blobs. Search can start with PostgreSQL; no extra search service is proposed.

**Validation:** Fresh/upgrade migration tests, local/S3 conformance, concurrent publishing tests and identical portable-template render round trips.

**Implementation/evidence:** Not implemented; PostgreSQL licence reconciliation is DD-013.

## DD-006: Start with a PostgreSQL-backed durable job queue

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E7-04, E7-06, E12-01, E12-02

**Context:** Async jobs must survive restarts without adding a broker prematurely.

**Choice:** Transactional enqueue, short SKIP LOCKED claims, expiring leases, heartbeats, attempt records and atomic output publication. Separate render/extraction job classes. Sync calls wait on this same machinery under a bounded deadline. Webhook delivery has a separate controlled dispatcher.

**Alternatives:** Celery with an external broker provides more mature operations but adds services. FastAPI in-process background tasks alone cannot satisfy durable restart recovery.

**Consequences:** At-least-once execution requires idempotent state changes and side effects. Implementing lease behavior has real cost; replace with a suitable maintained queue library if evaluated evidence favors it. Full retry/DLQ management remains R2.

**Validation:** Crash before/after claim and publication, stale lease takeover, duplicate execution, webhook signing/retry and bounded API wait tests.

**Implementation/evidence:** Not implemented; no throughput claim or exactly-once claim is made.

## DD-007: Choose PDF rendering from measured multilingual evidence

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E2-08, E4, E6-01, E6-04, E6-05

**Context:** The backlog explicitly requires a native-reader engine comparison before selecting the default.

**Choice:** Compare Chromium/Playwright and WeasyPrint on a fixed corpus. Chromium is the first candidate, not a final decision. Bundle reviewed Noto font families, including CJK separately. Final preview uses the same server artifact as generation. Record engine/font/locale manifests.

**Alternatives:** Choosing from feature lists or using different engines for preview and output could hide pagination or script differences.

**Consequences:** Deployment versions must be pinned early for regression testing; user-selectable per-template engine pinning remains R2. PDF metadata/font diagnostics may require additional vetted implementation.

**Validation:** E4-01 native-reader scores; glyph coverage, bidi, shaping, line breaking, repeated tables, page numbers, embedding and metadata checks. Record actual winners/failures before acceptance.

**Implementation/evidence:** No render spike has been run and no engine has been selected.

## DD-008: Keep Word templates as a separate merge/conversion path

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E6-02, E6-03

**Context:** MVP requires Word-template merging and converting merged Word to PDF; it does not require arbitrary designer-to-DOCX round-trip fidelity.

**Choice:** Use a constrained python-docx-template path and an isolated headless LibreOffice conversion candidate. Reject unsafe expressions, relationships/macros and oversized archives. Sequence E6-02 ahead of E6-03.

**Alternatives:** A single universal document model risks overpromising Word layout fidelity. A commercial converter may be evaluated if the local path fails and commercial distribution is acceptable.

**Consequences:** Two template families need clear UI/API capability labels. LibreOffice needs a licence decision; isolated deployment does not erase that requirement.

**Validation:** Multilingual Word fixtures with tables/images/loops, conversion fidelity and malicious-input containment.

**Implementation/evidence:** Not implemented; licence and output fidelity remain gates.

## DD-009: Use a declarative template tree and bounded expression grammar

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E2-05, E3-06, E5

**Context:** Owners need loops/conditions while templates must not execute code or make network calls.

**Choice:** Versioned JSON TemplateDefinition with text/layout nodes, bindings and condition/loop AST. Whitelist expression operators and formatters, bound execution, and report field paths. Use Decimal for money and a vetted locale-formatting adapter. Fetch URL assets only through a controlled staging path.

**Alternatives:** Arbitrary JavaScript/Python and unrestricted templating expressions are unsuitable. Persisting raw executable HTML couples security and semantics to the browser.

**Consequences:** Preview and rendering must share semantic conformance tests. CSV/Excel generation and advanced aggregation remain in their source releases.

**Validation:** Nested/empty array tests, field validation, missing-value policy, locale fixtures, resource bounds and template escape/SSRF cases.

**Implementation/evidence:** Not implemented; Babel is only a licence-conditioned formatting candidate.

## DD-010: Normalize engine output and retain field provenance

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E8, E9, E10

**Context:** Docling/PaddleOCR are named requirements; three engines and a local extractor are required in MVP.

**Choice:** Introduce private capability-aware adapters for Docling, PaddleOCR and Tesseract. Produce a versioned PageModel; use JSON as the position-preserving source and Markdown as a linked derivative. Start schema extraction with local mappings/rules and table processing. Retain raw/normalized values, source coordinates and model versions; calibrate confidence against held-out labels.

**Alternatives:** Cloud-only extraction violates local defaults. LLM-first extraction is unnecessary for MVP and does not establish grounded accuracy. Raw OCR scores alone do not measure field correctness.

**Consequences:** Different adapter capabilities must be visible. Language/script generation coverage and schema extraction coverage are separate. Public plugin packaging/version guarantees mature in R2.

**Validation:** CPU benchmark, geometry/rotation overlay tests, digital-PDF routing, field/line-item metrics and confidence reliability assessment.

**Implementation/evidence:** Not implemented; no extraction accuracy target has been fabricated.

## DD-011: Establish identity and approved-review snapshots early

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E7-02, E10, E11-01, E11-02

**Context:** Review corrections need attributable actors, and API template/extraction access requires authorization.

**Choice:** Local accounts with Argon2id, server-side sessions, secure cookies, CSRF/login limits and hashed scoped API keys. Enforce permissions in API handlers/domain operations. Review uses optimistic concurrency and immutable approved snapshots. Include the Should local-user story early as a dependency.

**Alternatives:** Client-only permissions are insufficient. Requiring a full external identity service delays self-hosted MVP; OIDC/SAML remains R2.

**Consequences:** Editing approved data creates a new revision requiring reapproval. MVP correction history does not establish the later tamper-evident admin audit capability.

**Validation:** Role/key-scope denial tests, CSRF/session tests, concurrent review conflicts and prohibition of unapproved closed-loop generation.

**Implementation/evidence:** Not implemented; exact auth packages will receive separate licence/version records.

## DD-012: Separate networked orchestration from untrusted document execution

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E1-06, E11-04, E12-02

**Context:** Workers need storage/job access while renderer and document parsers must be contained.

**Choice:** Use nonprivileged, credential-free, network-disabled child execution with staged files, bounded CPU/memory/time/output and temporary directories. Supervisors own database/storage calls; controlled gateways handle remote assets/webhooks. Compose is the initial deployment, Helm is R2.

**Alternatives:** A container label alone is not proof of containment. Disabling only template JavaScript does not block all parser or network attack paths.

**Consequences:** Exact operating-system isolation and process-tree cleanup need a technical spike. TLS proxy, image layers and sandbox dependencies join the licence inventory.

**Validation:** Hostile PDF/DOCX/image/font fixtures, blocked egress, secret isolation, timeout and process-tree termination tests.

**Implementation/evidence:** Not implemented; minimum CPU/RAM remains benchmark-dependent.

## DD-013: Resolve the dependency licence conflict explicitly

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E1-04, E6-03, E11-05, E14-02

**Context:** The default MIT/Apache-2.0/OFL list excludes the expressly required PostgreSQL licence and common runtime/transitive components.

**Choice:** Propose narrowly documented exceptions for necessary runtime/permissive components, with separate treatment for LibreOffice. Scan direct/transitive packages, native binaries, containers, fonts and model weights; publish SBOM and notices. Leave product licence/contribution agreement undecided until selected by the project owner.

**Alternatives:** Claiming all open-source software meets the literal allow-list is inaccurate. Strictly keeping the list unchanged requires reconciling PostgreSQL and conversion requirements.

**Consequences:** The proposed stack is not yet demonstrably compliant. Do not ship or install a conflicting dependency under an assumed exception. Record component/version/SPDX expression/scope and acceptance evidence when resolved.

**Validation:** Complete dependency graph inventory and CI policy tests against disallowed/unknown identifiers before distribution.

**Implementation/evidence:** No licence exception or product licence has been approved. Upstream evidence is linked in tech-stack.md.

## DD-014: Use staged delivery and evidence-based release gates

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** All epics; particularly E4-08, E9-09, E14

**Context:** 91 MVP stories and multilingual/OCR uncertainty make a single undifferentiated release risky.

**Choice:** Run preparation M0, then source-aligned M1 generation and M2 digitization. Include foundational identity/docs/i18n dependencies. Use automated contract/security/regression tests plus native-reader and accessibility reviews. Start structured redacted logs/correlation IDs early; full observability remains R2. Set performance/accuracy budgets after benchmarks.

**Alternatives:** A calendar promise from S/M/L labels ignores team size. Treating an alpha as full MVP obscures unfinished source requirements.

**Consequences:** Accessibility quality-bar timing must be reconciled with E2-13 R2. Intentional visual baseline updates require recorded review. Include all remaining MVP Should stories before claiming full source delivery.

**Validation:** Acceptance evidence by story, corpus manifests, independent/native review, release scope checklist and benchmark methodology.

**Implementation/evidence:** Not implemented; no performance, compliance or accessibility certification is claimed.

## DD-015: Defer AI, public ecosystem and hosted billing to their releases

- **Date:** 2026-09-22
- **Status:** Proposed
- **Scope:** E13, E14-07, E15

**Context:** The backlog already places AI in R3 and managed hosting in R4; MVP must work locally.

**Choice:** Keep optional provider interfaces and private adapters small. Add evaluated human-reviewed AI/MCP in R3; add tenant isolation, metering, payments and region controls in R4. MVP is single-deployment/workspace with resource authorization, not certified multi-tenancy.

**Alternatives:** Building SaaS billing, a plugin marketplace, a vector database or an agent framework now expands scope without proving generation/extraction value.

**Consequences:** Future tenant scoping affects storage/cache/job authorization and needs a dedicated migration/security design. No payment/cloud/model vendor is selected now.

**Validation:** R3 evaluation and two-client MCP tests; R4 adversarial tenant isolation, metering reconciliation, payment retries and regional enforcement.

**Implementation/evidence:** Not implemented; later concrete package/vendor choices need new decisions.

## Template for subsequent decisions

Copy this structure for a new decision; replace the bracketed fields before recording it.

```markdown
## DD-NNN: [Concrete decision]

- Date: YYYY-MM-DD
- Status: Proposed / Accepted / Implemented / Rejected / Superseded
- Scope: E?-?? and affected modules
- Acceptance basis: [Who adopted it or what authorized requirement establishes it]

Context: [Problem and constraints]
Choice: [Behavior or technology selected, including operational defaults]
Alternatives: [Viable options and reason for choosing]
Consequences: [Benefits, costs, compatibility, security and licence implications]
Validation: [Checks, corpus/environment and actual result, or still pending]
Implementation/evidence: [Relative files, tests, reports, commits or upstream sources]
Supersedes/superseded by: [Decision ID when applicable]
```

## DD-016: Implement the E1 MVP foundation before its R2 operations stories

- **Date:** 2026-09-22
- **Status:** Accepted; implementation and runtime verification in progress
- **Scope:** E1-01 through E1-06
- **Acceptance basis:** User instruction, "Start with E1"; existing release boundaries in the backlog.

**Context:** E1 contains six MVP and six R2 stories. Rendering/OCR are downstream epics and have not passed their required spikes.

**Choice:** Implement the foundation in the proposed Python/React stack: PostgreSQL, configuration, storage adapters, migration/bootstrap, health/readiness and a read-only sample workspace. Preserve R2 stories as scheduled. Mark E1-06 partial until actual E4/E8 rendering/extraction engines work on CPU; no placeholder worker is presented as a functional engine.

**Alternatives:** Implementing all later deployment capabilities now conflicts with the source sequencing. Claiming CPU rendering/OCR from a CPU-only API container would misstate acceptance.

**Consequences:** E1 can make concrete progress before the E4 spike, but cannot honestly be marked entirely complete yet. The foundation is local-only and has no E11 authentication layer.

**Validation:** Compose startup, API/UI/sample checks, configuration tests, shared local/S3 tests and PostgreSQL migration tests are defined; execution status is tracked in [E1 status](e1-foundation.md).

**Implementation/evidence:** [Compose](../compose.yaml), [backend](../backend/app/main.py), [workspace](../frontend/src/main.tsx), [tests](../backend/tests/test_foundation.py). Runtime installation remains gated by DD-022.

## DD-017: Use TOML plus explicit environment overrides and sanitized errors

- **Date:** 2026-09-22
- **Status:** Accepted; implementation awaiting behavioral verification
- **Scope:** E1-02, E1-05

**Context:** One application config file and environment overrides must be predictable, with no secret-bearing inputs in logs.

**Choice:** Pydantic validation over standard-library TOML; defaults < config file < DOCPLATFORM_ environment values. Resolve relative local-storage paths against the config directory. Reject unknown settings and an explicitly missing file. Use SecretStr for credentials/endpoints, hide validation inputs, and return fixed operational error messages. Disable HTTP access logs, SQL parameter logs and debug configuration. Default object limit is 10 MiB for the foundation; later upload limits need their own story decision.

**Alternatives:** Implicit dotenv discovery and nested settings sources add ambiguous precedence; raw parser/driver error logging may expose passwords and endpoints.

**Consequences:** Operators get dependency status rather than raw exceptions. Compose explicitly owns container host, port, DB address and volume path; those overrides are documented. Future observability must add safe structured diagnostics, not re-enable raw errors.

**Validation:** Tests cover precedence, malformed TOML, invalid values, missing S3 bucket, typo detection and secret redaction. Liveness is dependency-independent; readiness checks schema head and storage read/write/delete, plus frontend build availability.

**Implementation/evidence:** [config.py](../backend/app/config.py), [configuration](../config.toml), [config tests](../backend/tests/test_config.py), [API](../backend/app/main.py).

## DD-018: Give local and S3 storage the same bounded object contract

- **Date:** 2026-09-22
- **Status:** Accepted; shared contract tests awaiting execution
- **Scope:** E1-03

**Context:** Templates, uploads and outputs need portable object storage without forcing a bundled object-store server.

**Choice:** Byte-oriented put/get/delete/check contract with namespaced keys, overwrite semantics, idempotent delete and a typed missing-object error. Local writes use same-directory temporary files, flush/fsync and atomic replacement. Reject traversal, symlinks/junctions and Windows aliases on all platforms. S3 uses boto3 with explicit timeouts/retries, an existing bucket, optional endpoint/credentials and a configurable prefix. No bucket creation at application startup.

**Alternatives:** Arbitrary user paths expose the host filesystem; storing binaries in PostgreSQL or bundling another storage service is unnecessary for this foundation.

**Consequences:** The local volume is private to the application; hostile concurrent modification by another host process is outside the adapter's trust boundary. Switching storage backends requires moving objects; it is not an automatic migration. Credential-provider-chain support is available when explicit S3 credentials are absent. Readiness probes incur a small S3 request cost and require put/get/delete permission.

**Validation:** One parameterized suite exercises both adapters with overwrite, deletion, missing objects, all three namespaces, multilingual bytes, empty values, oversized inputs and unsafe keys. S3 tests use Moto emulation; live provider conformance is a separate environment check.

**Implementation/evidence:** [storage.py](../backend/app/storage.py), [shared storage tests](../backend/tests/test_storage.py).

## DD-019: Run serialized Alembic migrations before serving requests

- **Date:** 2026-09-22
- **Status:** Accepted; PostgreSQL verification awaiting dependency permission
- **Scope:** E1-01, E1-04, E1-05

**Context:** Fresh startup and upgrades must initialize metadata safely, including concurrent launch attempts.

**Choice:** PostgreSQL 17, SQLAlchemy, Alembic and the pure-Python pg8000 driver. A one-shot Compose migration service waits for PostgreSQL readiness; the application waits for successful migration. Hold a PostgreSQL advisory lock around Alembic upgrade and check the expected head in readiness. Add an initial template table and a second schema-version migration so upgrade preservation is directly testable. Seed one fixed-ID template idempotently with object data written before metadata.

**Alternatives:** SQLAlchemy create_all does not test schema upgrades; every HTTP worker racing an unprotected migration is unsafe. pg8000 avoids the additional libpq/driver distribution surface for this modest foundation workload; benchmark before high-throughput adoption.

**Consequences:** A failed migration or storage probe prevents application startup. The fixture's schema is preliminary and does not establish E3 publish/version semantics. Two migration revisions are not two historical product releases, so E1-07 is not claimed.

**Validation:** Real PostgreSQL tests cover fresh install, existing-row preservation from revision 0001, repeat upgrades, concurrent migrators, repeated seed and unmigrated readiness. Test DB reset is restricted to an explicitly named disposable database.

**Implementation/evidence:** [bootstrap](../backend/app/bootstrap.py), [migration runner](../backend/app/migrations.py), [revisions](../backend/migrations/versions/0002_template_schema.py), [integration tests](../backend/tests/test_foundation.py).

## DD-020: Serve the initial workspace and API from one origin

- **Date:** 2026-09-22
- **Status:** Accepted; browser/build verification pending
- **Scope:** E1-01; enabling i18n structure for E14-04

**Context:** The first installation needs a useful UI with a persistent preloaded sample, not a fake rendering demo.

**Choice:** React/TypeScript/Vite with i18next; build static assets in a Node stage and serve them with FastAPI. Show the saved template, sample data and real dependency status. Use a warm neutral/green palette, responsive single-workspace layout, semantic headings/buttons, and a read-only detail view. Keep all interface messages in the translation resource. Sample text is document content, separate from UI messages. No CDN fonts, analytics or external UI runtime requests.

**Alternatives:** A separate production frontend server/proxy adds a service without a present requirement. Editing/render buttons without functioning backends would misrepresent delivery.

**Consequences:** No CORS configuration is needed. Developer Vite proxy is optional. Only English UI strings ship in this step; i18n foundations do not complete E14's later translated UI story. The API is read-only and unauthenticated, so Compose binds to host loopback only.

**Validation:** Typecheck/build plus browser tests for sample loading/navigation and narrow-screen overflow; test unavailable dependency states at the API boundary.

**Implementation/evidence:** [React workspace](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [translations](../frontend/src/i18n.ts), [browser tests](../frontend/tests/foundation.spec.ts), [Dockerfile](../Dockerfile).

## DD-021: Pin the foundation builds and keep CPU capability claims bounded

- **Date:** 2026-09-22
- **Status:** Accepted; installation/build validation pending
- **Scope:** E1-01, E1-06

**Context:** Repeatable self-hosting requires reproducible application inputs, while the required rendering/OCR hardware baseline does not exist yet.

**Choice:** Pin direct and resolved Python dependencies, npm lockfile and Node/Python/PostgreSQL image manifest digests. Use Python 3.13 and Node 22 for this foundation; reevaluate Python against actual OCR wheels in E8. Run application as UID 10001, read-only root filesystem, private writable object volume and bounded temporary mount. Require no GPU/device passthrough. Do not add stub workers.

**Alternatives:** Floating latest image tags make future regression comparisons unreliable. Publishing an invented OCR minimum from API-only measurements would violate the benchmark plan.

**Consequences:** Pinning does not establish security or licensing compliance. The foundation may be tested on CPU now, but the full CPU rendering/extraction acceptance and measured minimum hardware guide remain pending. Later E11 sandboxing applies to actual untrusted document child processes, not this API container alone.

**Validation:** Dependency resolution and syntax checks; fresh Compose build/start, persisted sample restart, and resource observations when runtime installation is permitted.

**Implementation/evidence:** [Dockerfile](../Dockerfile), [Compose](../compose.yaml), [runtime lock](../backend/requirements.lock), [test lock](../backend/requirements-test.lock), [npm lock](../frontend/package-lock.json).

## DD-022: Review narrow licence exceptions before installing the foundation

- **Date:** 2026-09-22
- **Status:** Accepted by user selection “1”; implementation review pending
- **Scope:** E1 foundation dependencies; refines but does not replace DD-013

**Context:** PostgreSQL/PSF/BSD dependencies conflict with the source default allow-list. The E1 instruction authorizes implementation but does not explicitly resolve the earlier licence-policy gate.

**Choice:** Request a narrow foundation exception covering the named PostgreSQL/Python runtimes and reviewed permissive dependencies. Inventory runtime, build and test dependencies separately. The test graph also introduces certifi's MPL-2.0 trust-store package, and Vite introduces Lightning CSS/MPL-2.0 as build tooling; both require explicit inclusion in the reviewed exception scope. Container OS packages need their own inventory before distribution. Product licensing and LibreOffice remain undecided.

**Alternatives:** Replacing the explicitly required PostgreSQL with SQLite would violate E1-04. Assuming permission from an unanswered question contradicts the project decision record.

**Consequences:** Source implementation, tests, dry-run package resolution and manifest inspection can proceed. The documented narrow exceptions may now be installed for E1 verification. This does not approve LibreOffice, the product licence, or unrestricted future dependencies. No blanket compliance assertion or full SBOM is made from registry metadata alone.

**Validation:** Registry metadata and exact locks are recorded in [dependency inventory](dependencies.md); unknown or compound licence expressions remain visible for review.

**Implementation/evidence:** The user selected option “1” after the foundation-exception question, authorizing the documented narrow exceptions for E1 foundation components. DD-013 remains unresolved for LibreOffice, the product licence, and future dependencies.

## DD-023: Add a temporary read-only epic status view to the workspace

- **Date:** 2026-09-22
- **Status:** Implemented
- **Scope:** Implementation enabler; traceability for E1-E15, no source backlog story changed

**Context:** The user requested a small in-product view of all epics, their relative weights, aggregate completion and high-level achievements. The current platform has no project-status API or persistence model, and the generated epic catalog must remain unchanged.

**Choice:** Add a static, read-only project status banner and responsive epic-card grid to the existing React workspace. Assign each epic a one-decimal weight proportional to its source story count (12, 16, 15, 18, 15, 15, 16, 20, 16, 14, 16, 12, 10, 13, 10 out of 218), totaling exactly 100. Count only evidence-backed foundation work in the aggregate (3 verified E1 stories = 1.4 weighted points); leave other epics at zero and describe partial work explicitly in commentary.

**Alternatives:** Add a backend status endpoint and database model; this would introduce durable product scope and a new contract for a temporary planning display. Use equal epic weights; this would misrepresent the source scope because the epics contain different numbers of stories.

**Consequences:** The view is transparent and requires no new dependency, API, migration or external service. Its snapshot must be updated manually as evidence changes. The 1.4% figure is implementation progress against this weighted planning model, not a release-readiness or acceptance certification.

**Validation:** Frontend TypeScript/Vite production build completed in the Docker image; the running workspace returned HTTP 200 at `/` and the existing API/readiness smoke checks passed. Browser-level visual review and accessibility certification are not claimed.

**Implementation/evidence:** [workspace](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [translations](../frontend/src/i18n.ts).

## DD-027: Show source user stories beneath each epic in project status

- **Date:** 2026-09-23
- **Status:** Implemented; validation pending
- **Scope:** Implementation enabler; project-status view, no backlog scope change

**Context:** The project-status page previously summarized only epic-level progress. The user requested traceability down to the source stories with ID, story, priority, and size columns.

**Choice:** Keep the existing weighted progress summary, then render one grouped semantic table containing every story from `docs/epics.md`. Each epic is a group row carrying its name, status, weight and progress; story rows carry the requested four source fields. Story data is checked into a frontend module generated from the current backlog transcription so the UI remains available without a docs filesystem at runtime.

**Alternatives:** Add a runtime API or parse Markdown in the browser; both would add deployment coupling for a static planning snapshot. Show one separate table per epic; that would make cross-epic scanning and responsive overflow less consistent.

**Consequences:** The status page is longer but fully traceable to the source backlog. The generated story module must be refreshed when `docs/epics.md` changes. This view remains informational and does not claim acceptance or delivery of planned stories.

**Validation:** TypeScript/Vite build is pending because frontend dependencies are not installed in this workspace; the source backlog remains unchanged. Browser accessibility review is not claimed.

**Implementation/evidence:** [story data](../frontend/src/epicStories.ts), [status view](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [translations](../frontend/src/i18n.ts), [source backlog](epics.md).

## DD-028: Install pinned dependencies while surfacing licence flags

- **Date:** 2026-09-23
- **Status:** Implemented; licence review pending
- **Scope:** E1 foundation validation and E3/E4 frontend/backend validation

**Context:** The workspace lacked `node_modules` and the Python test environment. The user authorized installation and requested that licence conditions be flagged without stopping implementation.

**Choice:** Run `npm ci` from the existing npm lockfile and install the exact backend test lockfile into `backend/.venv`. The backend lockfile has no hashes, so version-pinned installation proceeded without `--require-hashes`; package versions were not loosened. Record declared licence exceptions and missing metadata in [dependencies.md](dependencies.md) for review.

**Alternatives:** Stop installation on every non-MIT/Apache/OFL item; that would prevent validation while leaving the same policy issue unresolved. Silently treat all transitive packages as compliant; that would violate DD-013.

**Consequences:** Local validation is available. The project still does not claim licence compliance; MPL, ISC, BSD and missing-metadata items require the unresolved policy review. The virtual environment and frontend install are developer-local artifacts, not a product redistribution decision.

**Validation:** `npm ci` succeeded with 31 packages and reported no npm audit vulnerabilities. Backend installation succeeded; `47 passed, 5 skipped` with two deprecation warnings. Frontend `npm run build` passed. Full Ruff remains non-zero on existing repository findings plus a few new formatting/exception findings; targeted test lint passed.

**Implementation/evidence:** [frontend lock](../frontend/package-lock.json), [backend test lock](../backend/requirements-test.lock), [dependency review](dependencies.md), [validation status](epic-3-4-status.md).

## DD-026: Deliver E3/E4 MVP contracts with a provisional deterministic renderer

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E3-01 through E3-07; E4-01 through E4-10 foundations

**Context:** The project had only a foundation template row and a local editor slice. E3 requires durable version governance and E4 requires a repeatable multilingual rendering experiment before selecting a final PDF engine.

**Choice:** Add immutable `template_versions`, explicit published pointers, version-safe restore, portable ZIP manifests, starter/schema endpoints, and a dependency-free HTML renderer. The renderer exposes script detection, fallback stacks, locale formatting and diagnostics while remaining explicitly provisional until native-reader comparison evidence exists.

**Alternatives:** Add a PDF dependency before the engine spike; this would turn a candidate into an undocumented selection and add an unresolved licence surface. Keep governance in object metadata; this would not provide transactional history or publish pointers.

**Consequences:** The E3 lifecycle is executable and CPU/offline friendly. The current render artifact is HTML, not the final PDF output required by E6. Noto font names are fallback declarations, not bundled font evidence. Review approval, access policy, visual baselines, native-reader grading and R2 governance remain outside this change.

**Validation:** Python compilation passed; `scripts/render_spike.py` reported all requested script families and `pending-native-review`. Contract tests were added but not run because pytest/FastAPI dependencies are absent; frontend build was not run because Node dependencies are absent. No native-reader or licence approval is claimed.

**Implementation/evidence:** [models](../backend/app/models.py), [governance migration](../backend/migrations/versions/0003_governance.py), [API](../backend/app/main.py), [renderer](../backend/app/rendering.py), [spike](../scripts/render_spike.py), [tests](../backend/tests/test_epic34.py), [status](epic-3-4-status.md).

## DD-025: Begin E2-01 with a local editor slice before persistence and rendering

- **Date:** 2026-09-23
- **Status:** Implemented, partial acceptance
- **Scope:** E2-01; editor foundation only

**Context:** E2-01 requires draggable text blocks, formatting, and persistence in preview/output. E3 persistence and the E4 renderer comparison are not complete, so a full acceptance claim would be premature.

**Choice:** Add a clearly labeled local draft editor to the existing sample-template detail view. It supports text block creation/editing, drag reordering, bold/italic/color/alignment controls and an immediate browser preview. The draft is held in React state only; no backend save or final document output is presented as implemented.

**Alternatives:** Wait for all E3/E4 prerequisites; this would provide no executable editor feedback. Add an API save contract now; that would create premature template-version semantics and a persistence contract outside the current foundation.

**Consequences:** E2-01 has a demonstrable interaction slice and a safe path for editor usability checks, but remains partial until persisted template definitions and authoritative rendered output exist. This slice does not establish multilingual caret/IME correctness or final pagination.

**Validation:** Docker frontend build/typecheck and application readiness are required for this slice. Manual drag, formatting and text-entry review remain pending; no accessibility certification is claimed.

**Implementation/evidence:** [workspace](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [Epic 2 criteria](../docs/epics.md).

## DD-024: Make project status a linked table view

- **Date:** 2026-09-22
- **Status:** Implemented
- **Scope:** Implementation enabler; clarification of DD-023, no source backlog story changed

**Context:** The requested status information should not dominate the home workspace. The user clarified that the home page needs a project-status link and that the destination should show a table with epic ID, name, description, weight and status, with a simple overall percentage above it.

**Choice:** Keep a compact project-status banner on the home page with a `View project status` link. Toggle a dedicated in-app status view without adding a backend route or dependency. Render the 15-epic snapshot as a semantic, horizontally scrollable table and show the weighted completion percentage above it.

**Alternatives:** Keep the epic cards inline on the home page; this obscures the primary template workspace. Add client-side routing or a backend status endpoint; both are unnecessary for this temporary static view.

**Consequences:** The status view is easy to discover and preserves the home page focus. It remains a manually maintained planning snapshot and is not persisted or authorization-controlled.

**Validation:** The changed frontend will be verified with the Docker TypeScript/Vite production build and HTTP readiness check. Browser-level interaction and accessibility certification remain unclaimed.

**Implementation/evidence:** [workspace](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [translations](../frontend/src/i18n.ts).
