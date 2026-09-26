# Backlog analysis and implementation plan

Date: 2026-09-24. This plan interprets the [218 source stories](epics.md); it does not silently change their priority, release or acceptance criteria. The repository now contains evidence-backed MVP contract slices across E1-E14; the authoritative per-story overlay is [storyStatus.ts](../frontend/src/storyStatus.ts). Stories remain `partial` where their source acceptance still requires native-reader, OCR, licensing, calibration, or deployment evidence. Proposed choices and evidence are in the [decision register](design-decisions.md).

## Current implementation position

The delivered slices cover the local foundation, template/data contracts, bounded editor and preview flows, template governance, extraction schemas and local extraction, review/correction workflows, API/jobs/integration boundaries, security controls, and documentation/status surfaces. The current live Compose topology and full backend regression are maintained as validation evidence, not as proof that every Must story is complete.

Run `python scripts/audit_must_status.py` to verify that every `Must` row in the source backlog has an explicit status in the UI overlay. The command reports the implemented/partial/planned split and fails if a source Must ID is missing from the overlay.

The principal open Must gates are: production PDF/Word rendering and native-reader fidelity; complex-script shaping, font embedding and visual regression; Docling/PaddleOCR or another reviewed local OCR/layout engine; held-out confidence calibration and accuracy evidence; exact PDF page-image review alignment; complete hostile-parser/resource containment across supported deployments; and the selected project licence/contribution agreement. These gates remain visible in the story overlay and relevant decision records.

## Verified scope

| Release | Stories | Interpretation |
| --- | ---: | --- |
| MVP | 91 | 81 Must, 10 Should; includes 24 L stories |
| R2 | 67 | Governance, deployment/operations maturity, integrations and additional formats |
| R3 | 30 | AI assistance, advanced extraction and optimization of review |
| R4 | 30 | Hosted service, billing, advanced compliance and remaining formats |
| Total | 218 | 15 epics |

The counts were recomputed from the DOCX tables and match its summary. Sizes are relative estimates, not a calendar plan. Team composition, budget and hardware targets are unknown. The referenced market research and roadmap in the source's 'main tab' were not provided, so their claims cannot be checked here.

## Epic map and dependencies

This table adds implementation guidance. The complete original stories and goals remain in [epics.md](epics.md).

| Epic | Stories | Delivery focus | Main dependencies / validation |
| --- | ---: | --- | --- |
| E1 Platform foundation and deployment | 12 | Compose, config, storage, migrations, CPU runtime; later Helm, offline, backup and retention | Resolve runtime licences; fresh-install/migration tests; storage adapter conformance |
| E2 Template editor | 16 | DOM text editing plus page/block design, repeat tables, logic and preview | E4 rendering spike, E5 grammar, E3 persistence; native-script input and keyboard checks |
| E3 Template management and governance | 15 | Immutable versions, folders, starters, schemas, portable bundles; later approval/promotion | E1 persistence, E11 permissions, E4 round-trip renders |
| E4 Rendering engine and multi-language | 18 | Main differentiator; engine spike, fonts, shaping, bidi, line breaks, locales and translations | Begin first; depends on native-reader corpus and licence review; compare engines before selection |
| E5 Data binding and template logic | 15 | Bounded expression grammar, schema validation, formatting, approved extraction binding | E4 locale semantics, E3 template schema; E9/E10 for E5-08 |
| E6 Output formats | 15 | Designer PDF and Word merge/conversion; later spreadsheet, slides, HTML and archival/accessibility | E4 and E5; Word conversion licence and fidelity gate; output validators |
| E7 API, SDKs and integrations | 16 | REST/OpenAPI, API keys, synchronous/asynchronous jobs and signed webhooks | E11 identity, E12 jobs; E8/E9 for extraction API; later SDKs/connectors |
| E8 Digitization: ingestion and OCR | 20 | Upload routing, Docling layout, PaddleOCR, third-engine contract and source locations | E1 storage, E11 hostile-file containment, E12 limits; CPU-only benchmark |
| E9 Schema and extraction | 16 | JSON Schema, local field extraction, line items, normalization, confidence and exports | E8 page model; labelled held-out corpus; distinguish extraction scoring from OCR confidence |
| E10 Review and correction | 14 | Source overlays, corrections, keyboard triage, approval and generated output | E8 provenance, E9 results, E11 actor identity, E5 binding; concurrency and audit tests |
| E11 Identity, security and compliance | 16 | Sessions, permissions, TLS, upload isolation and licence/SBOM checks | Starts alongside E1, not after UI; later SSO, tamper evidence and hosted controls |
| E12 Operations, observability and scale | 12 | Restart-safe queue and per-job limits; later scaling, retries, dashboards and load tests | E1 database and isolated workers; kill/restart and resource-exhaustion tests |
| E13 AI assistance and agent integration | 10 | Optional local/provider models, reviewed suggestions, evaluation suite and MCP | Stable E3/E7/E9 contracts; E11 controls; no unattended publish/approve |
| E14 Ecosystem, documentation and community | 13 | Quickstart, contributor path, script matrix, i18n, examples and roadmap | Cross-cutting from MVP; release evidence feeds docs; project licence unresolved |
| E15 Hosted cloud and billing | 10 | Tenant isolation, metering, signup, plans, quotas, regions and paid-feature policy | Mature E11/E12; explicit isolation and billing reconciliation tests before hosted launch |

## Delivery sequence

### M0: feasibility and contracts (proposed preparation inside MVP)

Begin E4-01 and supporting experiments before a full editor build. Create a representative native-reviewed corpus, compare renderer candidates and test Word conversion. Draft the TemplateDefinition, PageModel, ExtractionResult and job contracts. Run a small CPU-only OCR pipeline and inventory dependency/font/model licences. Produce a benchmark methodology and record all results in the decision register.

Exit: evidence-based renderer recommendation, documented coverage gaps, a feasible dependency policy and a demonstrable CPU-only path. The bounded candidate benchmark is recorded with `scripts/benchmark_cpu_pipeline.py`; it does not substitute for the engine-specific CPU/OCR benchmark. M0 is a sequencing aid, not a new source release or a claim that MVP stories are already done.

### M1: generation with multilingual proof

Follow the source's M1 intent: MVP stories in E1-E7, excluding E5-08 and E7-05 until M2, plus E11-02 through E11-05 and E12-01/E12-02. Resolve dependencies before claiming the milestone:

1. Foundation, local identity, migration/config/storage, durable jobs and sandbox boundaries.
2. Template schema, field/loop/condition grammar, locale formatting and render API.
3. Draft/publish/version management, bundled starter templates, assets and translations.
4. DOM editor, repeat tables, page flow, font diagnostics and authoritative server-rendered preview.
5. Word merging and PDF conversion; OpenAPI explorer, API keys, webhooks and quickstart.
6. Native-reviewed script matrix, hostile-input/restart tests, licence report and SBOM.

Include E11-01 local users/roles as an enabling dependency even though its source priority is Should. Include E14-01 through E14-04 as launch foundations, and plan E14-05/E14-06 examples/roadmap before calling the full MVP complete. Treat E6-02 Word merging as necessary to demonstrate E6-03 conversion even though E6-02 is Should and E6-03 is Must. These sequencing recommendations do not rewrite source priorities.

Exit: a developer generates a PDF through the documented API, a template owner can create/publish a template, native readers approve the script matrix, and the security/licensing gates pass. M1 can be a public alpha only with an explicit scope statement; it is not the full 91-story MVP.

### M2: digitization and the closed loop

Implement the E8/E9/E10 MVP stories, E7-05 and E5-08. Start with upload and digital/scanned routing, normalized page models, then schema extraction, confidence calibration, exports, review and correction capture. Make the source coordinates testable before building overlays.

Exit: upload a scanned invoice, extract structured values with source locations, correct and approve it, bind the approved snapshot to a template and generate a PDF. Report field/line-item accuracy per schema on the held-out labelled set. Finish any remaining MVP Should stories before claiming the full source scope delivered.

### R2: production maturity

Prioritize backup/restore, upgrade tests, folder policies, review-before-publish, SSO and operations. Add multi-worker scaling, retries, dashboards, load tests, SDKs, CLI, extra formats, offline packaging and the published plugin contract. Split XL work (embedded editor E7-09 and plugin system E14-07) into independently verifiable stories before scheduling. E8-08 already needs an internal engine contract in MVP; R2 expands it into a stable ecosystem API.

### R3: advanced extraction and AI

Keep AI behind configured providers with no default data egress. Build evaluations before template/schema suggestion flows. Human approval remains mandatory for AI publication and suggested rule changes. Confidence-based auto-approval under E9-12 is a separate, explicitly configured extraction policy, not permission for AI to publish templates. Add MCP with the same API authorization and resource limits. Split XL routing/table/handwriting/scan-segmentation and AI drafting stories.

### R4: hosted and advanced controls

Design tenant isolation, metering and billing before signup. Test cross-tenant object access, signed URLs, jobs, caches and audit records. Reconcile usage to billable events and handle payment webhook retries. Treat PDF/A, accessible tagged PDF, e-signature, region enforcement and certification preparation as separate acceptance programs. No existing stack component establishes certification by itself.

## Requirements to reconcile before affected implementation

| Issue | Proposed treatment | Decision |
| --- | --- | --- |
| Literal MIT/Apache/OFL policy excludes required PostgreSQL and common runtime components | Record narrowly scoped exceptions or amend the requirement; do not declare the proposed stack compliant yet | DD-013 |
| E6-02 Should enables E6-03 Must | Plan Word merging ahead of conversion and track both source IDs | DD-008 |
| Local users are Should but secure sessions and attributable review are Must | Include local identity in the early foundation | DD-011 |
| Release quality bar requires WCAG 2.2 AA, but editor accessibility is explicitly R2 | Build keyboard/semantic foundations in MVP; do not claim full AA without audit; reconcile any release exception explicitly | DD-014 |
| Rendering support is broad in MVP; multilingual label dictionaries arrive in R2 | State generation and extraction language coverage separately; measure each OCR language/schema combination | DD-010 |
| Backlog suggests M1 without explicitly listing E14 launch work | Include quickstart, contributor/licence files, i18n and script-matrix docs in launch planning | DD-014 |
| E8-08 requires three engines while public plugin framework is R2 | Implement a private, versioned capability contract now; stabilize public extension packaging in R2 | DD-010 |
| Engine pinning is R2, but visual regression needs repeatable baselines now | Pin deployment versions and fixture manifests now; expose per-template selection in R2 | DD-007 |
| Source says all visual changes fail CI | Fail on unreviewed baseline differences; require native review and a recorded decision to intentionally change an expected output | DD-014 |

These are planning gaps, not reasons to stop documenting or prototyping. Product decisions needed before launch: licence/contribution model, permitted exceptions, exact first-release languages/locales and document types, accessibility release criteria, expected document volumes/page sizes, target deployment resources, and availability of native reviewers and labelled documents. Record answers when they become available; do not infer them from the user's timezone or workstation.

## Verification strategy

- **Unit/contract:** grammar limits, locale normalization, schema errors, role checks, storage and engine adapter conformance.
- **Integration:** transactional job creation, worker kill/restart, lease recovery, migration upgrades, immutable publishing and approved-data binding.
- **Document:** embedded fonts/glyph coverage, bidi and line breaks, repeated headers/rows, page numbers, PDF metadata and DOCX fidelity on fixed fixtures.
- **Extraction:** field precision/recall or exact-match definitions as appropriate, normalized-value accuracy, line-item row/column metrics, coverage and confidence calibration. Keep calibration/training material separate from final evaluation.
- **Security:** cross-role access, template escape, SSRF redirects, malicious archives, oversized images/fonts, parser crashes, CSRF and unauthorized draft/extraction access.
- **User experience:** keyboard-only editor/review, screen reader checks, IME and native text selection; latest two target browser versions. Playwright provides useful engine coverage but does not replace actual Safari/version testing.
- **Release:** user/API documentation, SBOM, native-reader approval and second-engineer review required by the source. This planning session supplies none of those future sign-offs.

Definition of done adds one project requirement to the source: every design choice introduced or changed by a story is recorded in `docs/design-decisions.md` with evidence and implementation references. Keep original backlog acceptance criteria intact; scope changes require an explicit decision entry.
