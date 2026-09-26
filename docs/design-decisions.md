# DD-160 — Defer OCR/layout engine adoption pending dependency and runtime evidence

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; adoption deferred
- **Affected stories:** E8-03, E8-04, E8-08, E6-01, E6-03
- **Context:** The remaining Must stories name Docling and PaddleOCR, while the implementation must remain CPU-capable, locally executable, isolated from credentials and networks, and compliant with the unresolved DD-013 licence policy. A package name or top-level licence is not sufficient evidence for transitive dependencies, model weights, native binaries, language data, or document-output acceptance.
- **Choice:** Do not add Docling, PaddleOCR, pytesseract, Tesseract, model weights, or their transitive graphs to the application image or lockfiles yet. Preserve the plugin registry, deterministic local extractor, and explicit `unavailable` OCR metadata so callers can distinguish configured-but-unavailable OCR from successful extraction. Revisit adoption only through a bounded CPU/offline spike with dependency/model SBOM evidence, isolated execution tests, and the relevant PageModel/rendering acceptance evidence.
- **Alternatives:** Add the named packages immediately; rejected because Docling's wheel delegates to `docling-slim`, PaddleOCR delegates to PaddleX, and pytesseract does not contain the OCR engine. Treat top-level Apache metadata as approval; rejected because DD-013 requires the full dependency/model/runtime review and the policy conflict remains unresolved. Remove the named integrations; rejected because the source backlog explicitly identifies them and the registry contract should remain ready for a deliberate adapter.
- **Consequences:** E8-03 and E8-04 remain partial. E8-08 is implemented as a validated engine contract and discovery surface, not as evidence that optional engines are installed. The service remains smaller, offline-safe and reproducible; actual OCR/layout accuracy, model licensing, native dependencies and language-pack support remain open work.
- **Validation:** `pip download --no-deps` inspected `docling==2.130.0`, `paddleocr==3.7.0` and `pytesseract==0.3.13` without installation. Wheel metadata showed Docling's `docling-slim` dependency, PaddleOCR's `paddlex[ocr-core]` dependency and the direct licence fields recorded in `docs/dependencies.md`. No model download or external-engine execution was performed. Existing engine-registry and ingestion tests continue to validate the local fallback and unavailable-OCR contract.
- **Implementation/evidence:** [dependency review](dependencies.md), [engine registry](../backend/app/engines.py), [ingestion contract](ingestion-contract.md), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-161 — Add conservative local layout roles to the PageModel

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-03 remains partial
- **Affected stories:** E8-03, E8-06, E9-03
- **Context:** The bounded digital-PDF path already returned ordered text elements and source boxes, but consumers had no explicit reading-order list or stable role metadata for simple headings, list items, and delimited table rows.
- **Choice:** Add page-level `layout` metadata and per-text-element roles using explicit markers (`#` headings, list markers, pipe-delimited rows) plus a conservative all-caps heading rule. Keep the original text and coordinates authoritative, and expose the result as a deterministic local contract rather than presenting heuristics as general layout analysis.
- **Alternatives:** Infer layout from font transforms and PDF resources; rejected because the current parser intentionally does not interpret arbitrary PDF operators. Treat every text element as a heading/table; rejected because it would fabricate structure. Add Docling immediately; deferred under DD-160 pending dependency, model, isolation and acceptance evidence.
- **Consequences:** Local extraction consumers can preserve a stable reading-order sequence and distinguish bounded role hints without external calls. Complex layout, columns, spanning tables, font-size hierarchy, rotated text and scanned-page analysis remain incomplete; E8-03 stays partial.
- **Validation:** Added an ingestion regression covering heading, list and delimited-table role metadata and reading order; the existing ingestion, extraction and security suites remain the relevant validation set. No Docling-equivalence or production layout-accuracy claim is made.
- **Implementation/evidence:** [PageModel implementation](../backend/app/ingestion.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-162 — Add repository issue templates without selecting a project licence

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E14-02 remains partial
- **Affected stories:** E14-02, E11-05
- **Context:** The repository already had a contributor guide, code-of-conduct draft, and structured YAML bug/feature templates, but no dedicated security-report template. E14-02 also requires a chosen contribution agreement and a matching licence file; DD-013 and the project-licence decision remain unresolved.
- **Choice:** Add a security-report template that requires sanitized impact/reproduction details and directs sensitive reports to a private maintainer channel. Preserve the existing contributor, conduct, bug, and feature documents as-is; do not add a licence, contribution agreement, or public-launch claim.
- **Alternatives:** Choose an open-source licence and contribution agreement by convention; rejected because that is a project governance decision not supplied by the backlog. Leave issue intake unstructured; rejected because it weakens traceability and security reporting. Add a generic public security address; rejected because no maintainer contact has been selected.
- **Consequences:** Contributors have repository-local intake forms and explicit guidance not to publish secrets or customer documents. E14-02 remains partial until maintainers select the project licence, contribution agreement, enforcement contact, and launch governance.
- **Validation:** Confirmed `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and the existing YAML bug/feature templates; added `.github/ISSUE_TEMPLATE/security_report.md` and verified its private-disclosure guidance. No licence or agreement was inferred.
- **Implementation/evidence:** [contributor guide](../CONTRIBUTING.md), [code of conduct](../CODE_OF_CONDUCT.md), [issue templates](../.github/ISSUE_TEMPLATE), [dependency/licence review](dependencies.md), [story status](../frontend/src/storyStatus.ts).

# DD-163 — Add orphan and widow constraints to the pagination candidate

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-07 remains partial
- **Affected stories:** E2-07, E4-01, E6-01
- **Context:** The candidate renderer already emitted explicit page-break and keep-together rules for blocks and table rows, but paragraph flow could still leave very short fragments at page boundaries.
- **Choice:** Emit CSS `orphans: 3` and `widows: 3` on rendered paragraphs while retaining the existing break and keep-together controls. Treat these as renderer hints, not proof of final pagination behavior.
- **Alternatives:** Insert hard page breaks around every paragraph; rejected because it destroys natural flow. Claim CSS support proves the acceptance criterion; rejected because the selected PDF engine and fixed visual corpus are still pending. Implement a bespoke paginator now; deferred until E4-01 engine comparison selects a production path.
- **Consequences:** Candidate engines receive stronger, deterministic pagination guidance and the contract is explicit about the intended behavior. Actual orphaned-heading and split-row outcomes remain engine- and fixture-dependent; E2-07 stays partial.
- **Validation:** Added a renderer regression for the emitted orphan/widow declarations; the focused template/rendering suite and lint are the relevant checks. No PDF pagination or native-reader claim is made.
- **Implementation/evidence:** [renderer](../backend/app/rendering.py), [template tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-164 — Keep E12-02 partial after Windows CPU-limit probe

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** The worker attaches Windows children to a Job Object and applies configured CPU/memory limits, but the existing evidence covered only API attachment and portable wall-time/output behavior. A direct tight-loop child probe was needed to establish whether per-process CPU termination was observable on the supported development host.
- **Choice:** Retain the Windows Job Object implementation and the portable wall-time guard, but do not promote E12-02 based on attachment alone. Treat wall-time termination and serialized-output containment as verified boundaries; require a stable native CPU/memory exhaustion fixture and deployment-level evidence before claiming the full story.
- **Alternatives:** Mark CPU enforcement complete because `AssignProcessToJobObject` returned success; rejected because the probe did not terminate stably at the configured CPU limit. Remove native limits and rely only on wall time; rejected because CPU/memory caps remain required. Increase the wall-time budget until the probe appears successful; rejected because it would hide the resource-enforcement question.
- **Consequences:** The service keeps a bounded outer timeout and does not claim stronger Windows resource guarantees than the evidence supports. E12-02 remains partial, and E11-04 remains partial for full hostile-parser and deployment containment evidence.
- **Validation:** A direct Windows child probe confirmed Job Object attachment but did not produce stable per-process CPU termination; simple isolated renders still complete, and the existing real-child output-limit/recovery tests pass. The operational contract now records this host-specific evidence and the remaining gate.
- **Implementation/evidence:** [worker limits](../backend/app/worker.py), [worker child](../backend/app/worker_child.py), [jobs contract](jobs-contract.md), [job tests](../backend/tests/test_jobs.py), [story status](../frontend/src/storyStatus.ts).

# DD-165 — Add a parent-side Windows CPU watchdog

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** DD-164 recorded that Job Object attachment was successful but did not yield stable CPU-runaway termination evidence on the current host. The worker needed a second, observable enforcement path without adding a native Python dependency.
- **Choice:** Add a Windows-only daemon watchdog that reads the child user-mode CPU clock through `GetProcessTimes`, kills the child at the configured limit, and reports a distinct CPU-limit failure when that path is observed. Retain the Job Object and wall-time timeout as independent safeguards.
- **Alternatives:** Depend solely on the Job Object; rejected because the local probe did not make its CPU termination observable. Add psutil or another native dependency; deferred because the dependency/licence graph is unnecessary for this narrow platform adapter. Poll process wall time as a CPU substitute; rejected because it would conflate CPU starvation with elapsed time.
- **Consequences:** Windows workers now have an additional parent-observable CPU enforcement path while preserving the existing containment layers. Native CPU/memory exhaustion acceptance and deployment-level evidence remain open, so E12-02 is not promoted.
- **Validation:** Existing real-child worker tests pass (`11 passed`); Ruff is clean for the worker path after the change. The previous tight-loop probe remains recorded as unstable rather than being rewritten as a success.
- **Implementation/evidence:** [worker watchdog](../backend/app/worker.py), [jobs contract](jobs-contract.md), [job tests](../backend/tests/test_jobs.py), [story status](../frontend/src/storyStatus.ts).

# DD-166 — Reject common PDF active content before storage

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E8-01, E8-02
- **Context:** Uploads already enforce type/size limits and can invoke an optional scanner, but accepted PDFs could still contain common action, script, launch, embedded-file, rich-media, or XFA declarations. Future parsers or renderers may interpret those constructs even when the current bounded text path does not.
- **Choice:** Add a fail-closed lexical check for common active-content name tokens on PDF bytes before scanner execution and object storage. Keep the optional scanner and isolated worker boundary because compressed or obfuscated objects are outside this check.
- **Alternatives:** Allow active content because the current parser ignores it; rejected because future engines and consumers may interpret it. Strip the declarations and store the rewritten PDF; rejected because silent rewriting changes the source artifact and provenance. Claim antivirus coverage from the lexical check; rejected because it is not a malware scanner or complete PDF parser.
- **Consequences:** Common active PDF features are rejected before storage, reducing parser attack surface while preserving the original bytes for accepted files. Obfuscated/compressed threats, image decoder safety, scanner availability, and full sandbox containment remain open E11-04 gates.
- **Validation:** Added direct token regressions and an API regression proving `/OpenAction` is rejected before local storage. Focused security/ingestion tests and lint pass; no complete malicious-file containment claim is made.
- **Implementation/evidence:** [security gate](../backend/app/security.py), [ingestion route](../backend/app/main.py), [security tests](../backend/tests/test_security.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-167 — Scan bounded compressed PDF streams for active content

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E8-01
- **Context:** DD-166's raw-byte PDF gate could not see active-content names inside bounded FlateDecode streams. The ingestion path already uses decompression bounds for routing, so the security gate can inspect the same limited class without adopting a full PDF parser.
- **Choice:** Decompress only Flate streams matching the existing bounded structural pattern, with 1 MiB compressed, 4 MiB per-stream, and 16 MiB aggregate limits, and scan the inflated bytes with the same active-content token gate. Ignore malformed/oversized streams for this check and leave them to the scanner and isolated parser boundary.
- **Alternatives:** Inflate every PDF stream; rejected because decompression bombs are untrusted input. Treat any Flate stream as malicious; rejected because safe digital PDFs may use compression. Add a full parser immediately; deferred pending dependency/licence and hostile-input review.
- **Consequences:** Common active-content declarations in bounded compressed streams now fail closed before storage without weakening the local/offline path. Obfuscated encodings, malformed parsers, image decoder safety, and antivirus effectiveness remain outside this bounded check.
- **Validation:** Added a compressed JavaScript regression alongside raw-token and pre-storage API rejection tests; focused security/ingestion tests pass. E11-04 remains partial.
- **Implementation/evidence:** [security gate](../backend/app/security.py), [security tests](../backend/tests/test_security.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-159 — Preserve OCR selection and unavailable-engine state in ingestion

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; OCR execution remains incomplete
- **Affected stories:** E8-02, E8-04, E8-08
- **Context:** Upload routing distinguished digital PDFs from scans, but callers could not record the requested OCR language/engine and the PageModel did not explain why a scan had no OCR text. Silently returning an empty result would confuse routing with OCR completion.
- **Choice:** Accept bounded `ocr_language` and `ocr_engine` query parameters, persist them in the versioned PageModel processing metadata, report OCR as `skipped` for digital text and `unavailable` for scans when the named dependency is absent. Reject invalid language/engine values before storage and never synthesize OCR output.
- **Alternatives:** Treat every scan as processed with an empty PageModel; rejected because it hides a missing OCR engine. Auto-download models or call a cloud OCR service; rejected because local CPU/offline operation and deliberate data egress are requirements. Add a database column immediately; deferred because the versioned PageModel is already the authoritative processing contract and avoids a migration for this metadata.
- **Consequences:** API and review clients can distinguish routing, requested OCR configuration, and actual engine availability. PaddleOCR/Tesseract execution, language-pack licensing, OCR confidence, layout mapping, and scan accuracy remain open gates.
- **Validation:** Added digital-route OCR-skip, scan language/engine preservation, and invalid-selection regressions; focused ingestion tests and existing security/render checks pass. E8-02/E8-04/E8-08 remain partial.
- **Implementation/evidence:** [ingestion route](../backend/app/main.py), [ingestion contract](ingestion-contract.md), [ingestion tests](../backend/tests/test_ingestion.py), [story status](../frontend/src/storyStatus.ts).

# DD-158 — Sanitize inline SVGs before candidate rendering

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; full image-parser and malware containment remain separate E11-04 gates
- **Affected stories:** E11-04, E2-03
- **Context:** Image data URIs were bounded and signature-shaped, but SVG payloads are markup and could contain script, event-handler, entity, foreign-object, CSS URL, or external-reference constructs. The renderer does not fetch network resources, but unsafe markup should still be rejected at the contract boundary.
- **Choice:** Decode inline SVGs locally, require a bounded UTF-8 document with an SVG root, and reject executable markup, entity declarations, foreign objects, CSS `url(...)`, event handlers, and external HTTP/protocol references. Keep raster handling and uploaded-asset scanning on their existing paths.
- **Alternatives:** Allow all SVG because the preview iframe is sandboxed; rejected because output consumers and future engines may not preserve that boundary. Strip suspicious tags and continue; rejected because silent rewriting could change logos and hide unsafe input. Reject every SVG; rejected because bounded vector logos are a supported template need.
- **Consequences:** Safe inline vector assets remain available offline while common active-content and external-reference forms fail closed. This does not establish complete SVG XML-parser safety, raster decoder safety, antivirus effectiveness, or final PDF embedding.
- **Validation:** Added hostile SVG cases for script, external image reference, and entity declaration plus a safe SVG regression; focused template tests, lint, Docker rebuild, and readiness validation pass.
- **Implementation/evidence:** [renderer and upload validation](../backend/app/rendering.py), [security helper](../backend/app/security.py), [image security tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-157 — Make candidate directionality explicit at mixed-content boundaries

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; native bidi, shaping, and line-breaking review remain open
- **Affected stories:** E4-04, E4-05, E2-08
- **Context:** The candidate renderer used `dir="auto"` on text paragraphs but did not expose locale-level page direction or the same boundary on table cells and header/footer content. Mixed RTL/LTR values could therefore be interpreted inconsistently across candidate surfaces.
- **Choice:** Set the document direction for RTL locale families and retain `dir="auto"` with plaintext bidi styling on paragraphs, table headers/cells, headers, and footers. Keep direction metadata in the HTML candidate rather than inferring visual correctness from string order.
- **Alternatives:** Force every document LTR; rejected because RTL locale layout needs an explicit page direction. Force every block RTL; rejected because mixed values and numbers need isolated auto boundaries. Claim native bidi/line-breaking correctness from HTML attributes; rejected because browser/PDF engine and native-reader evidence is still missing.
- **Consequences:** Candidate artifacts now carry inspectable directionality intent across the main mixed-content surfaces. Actual bidi ordering, shaping, CJK/Thai line breaking, pagination, and native-reader acceptance remain partial.
- **Validation:** Added an Arabic mixed-script paragraph/table/header regression; existing rendering tests and frontend/live checks remain applicable. The story statuses remain partial.
- **Implementation/evidence:** [candidate renderer](../backend/app/rendering.py), [mixed-direction test](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-156 — Make shipped preview locale profiles explicit

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; complete CLDR coverage remains out of scope
- **Affected stories:** E4-09, E2-08
- **Context:** The preview selector exposed English, German, Arabic, Hindi, Thai, Chinese, Japanese and Korean-related locales, but the formatter used a small fallback profile for several of them. That made currency output implicit and inconsistent with the locale switch.
- **Choice:** Add explicit deterministic profiles for `en`, `en-GB`, `de`, `fr`, `hi`, `ar`, `th`, `zh`, `ja`, and `ko`, covering decimal/grouping separators, currency symbol and symbol placement. Resolve regional tags to their language profile when no regional override exists.
- **Alternatives:** Claim the existing fallback is CLDR-complete; rejected because it was not. Add Babel immediately; deferred until dependency licensing and the desired CLDR surface are reviewed. Implement locale-specific numeral/calendar systems now; rejected because those are separate acceptance dimensions and need fixtures.
- **Consequences:** Supported preview locales now have inspectable, stable currency behavior and regression coverage. Full CLDR behavior, native digits, calendars, accounting formats, time zones and final PDF formatting remain partial.
- **Validation:** Added a nine-locale currency matrix regression; existing locale/date tests remain green; lint and frontend/live checks are run with this change. E4-09 remains partial because the matrix is bounded rather than complete CLDR evidence.
- **Implementation/evidence:** [locale formatter](../backend/app/template_logic.py), [locale tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-155 — Validate extraction plugin results at the engine boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; named external engines remain optional/unavailable until their dependencies are selected and validated
- **Affected stories:** E8-08
- **Context:** The versioned extraction registry discovered optional engines and Python entry-point plugins, but accepted any dictionary result. That allowed an adapter to omit schema versioning, confidence bounds, fields/tables structure, or provenance shape while still appearing available.
- **Choice:** Validate `extraction-engine-v1` results immediately after adapter execution. Require schema version 1, object-valued fields/tables, confidence values from 0 through 1, dictionary-or-null scalar provenance, list validation findings, and structured table rows/cells. Reject malformed plugin output explicitly and do not fall back to the local engine.
- **Alternatives:** Trust each plugin and validate only at persistence; rejected because incompatible results could reach review or storage. Normalize missing fields or clamp confidence values; rejected because that fabricates evidence and hides adapter defects. Install Docling/PaddleOCR now solely to demonstrate the registry; rejected because dependency/model licence and CPU evidence remain unresolved.
- **Consequences:** The private engine seam is safer to extend and consumers receive a predictable result envelope. This does not claim Docling, PaddleOCR, or a third engine is installed, nor does it close layout/OCR capability acceptance.
- **Validation:** Added an invalid-plugin confidence regression and retained the local-engine contract regression; focused engine tests and lint pass. Documentation now states the enforced envelope.
- **Implementation/evidence:** [engine registry](../backend/app/engines.py), [engine tests](../backend/tests/test_engines.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-185 — Keep the source preview on the selected provenance page

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 and E10-01 remain partial
- **Affected stories:** E8-07, E10-01, E10-02
- **Context:** The review surface stored page numbers with every extracted source, but selecting a field from a non-visible page only changed the active highlight state. The preview could remain on another page, making a valid highlight appear missing.
- **Choice:** When the active source page changes, locate the matching PageModel page and switch the preview to that page. Preserve the existing manual page controls and keep the stored page number authoritative.
- **Alternatives:** Search all pages and render overlays simultaneously; rejected because it would reduce page readability and complicate image/PDF alignment. Reset to page one after each selection; rejected because it hides the selected provenance. Infer page order from array position; rejected because the contract identifies pages by their explicit page number.
- **Consequences:** Multi-page field and table-cell selections now reveal their exact element and field box without manual navigation. Native PDF pixel alignment, rotation handling and rasterized page interaction remain outside the current evidence, so E8-07/E10-01 remain partial.
- **Validation:** Frontend typecheck/build passed after the change; the focused live browser suite passed four tests, including a mocked multi-page result whose selected field provenance is on page 2. The effect is limited to explicit matching PageModel page numbers.
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-179 — Add a bounded offline DOCX merge enabler

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as a bounded enabler; E6-02 and E6-03 remain partial
- **Affected stories:** E6-02, E6-03, E6-01, E11-04
- **Context:** The implementation plan sequences Word merging before the Must Word-to-PDF story, but the repository had no safe DOCX package boundary. The source requires text, table and image merging, while dependency/licence and conversion-fidelity evidence for python-docx-template/LibreOffice is unresolved under DD-008 and DD-013.
- **Choice:** Add a dependency-free `docx-merge-v1` path that validates ZIP/package safety, preserves non-target parts, replaces bounded scalar tokens, and repeats same-row table loops. Process only main document/header/footer XML; reject macros, external relationships, unsafe paths and oversized decompression. Preserve existing images but do not interpret image placeholders.
- **Alternatives:** Add python-docx-template immediately; deferred because its dependency and transitive licence/runtime behavior require review. Parse arbitrary Word fields and relationships; rejected because it would enlarge the untrusted document surface. Convert with LibreOffice now; deferred because the engine/licence decision and Word-authored fidelity corpus are not approved.
- **Consequences:** A local CPU/offline merge foundation exists for safe scalar/table fixtures, and the Must conversion path has a testable predecessor. Split-run placeholders, image binding, arbitrary Word constructs, conversion, PDF fidelity and native-reader evidence remain open; no E6-03 completion claim is made.
- **Validation:** Added DOCX package/API tests for scalar replacement, repeated rows, malformed archives and external relationships; `tests/test_word_merge.py tests/test_epic34.py` passed (`12 passed, 3 warnings`) and the changed merge files pass Ruff. The API matrix includes `POST /api/word/merge`.
- **Implementation/evidence:** [merge implementation](../backend/app/word_merge.py), [merge tests](../backend/tests/test_word_merge.py), [Word contract](word-contract.md), [source plan](implementation-plan.md), [story status](../frontend/src/storyStatus.ts).

# DD-180 — Add an explicit optional Word-to-PDF conversion boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as a boundary; E6-03 remains partial
- **Affected stories:** E6-03, E6-01, E6-04, E6-05, E11-04
- **Context:** The bounded DOCX merge path now produces a validated package, but there was no API boundary for a future Word-to-PDF engine. Installing or selecting LibreOffice before resolving its licence, isolation and layout-fidelity evidence would overclaim the Must conversion story.
- **Choice:** Add an optional `word_converter_command` and timeout setting. Invoke the operator-provided executable as fixed arguments plus temporary input/output paths, with `shell=False`, reduced environment, bounded time and output, DOCX package validation, PDF signature validation and the existing active-content gate. Return candidate status and explicit metadata-not-assessed evidence; return 503 when no converter is configured.
- **Alternatives:** Bundle LibreOffice now; rejected because DD-013's licence conflict and deployment isolation are unresolved. Treat the Chromium candidate as a Word converter; rejected because it prints HTML and does not preserve arbitrary Word layout. Accept any output bytes; rejected because a converter boundary must fail closed on missing/invalid PDF output.
- **Consequences:** Self-hosters can deliberately connect a reviewed converter without changing the application template grammar, and later fidelity fixtures have a stable API boundary. No converter is enabled by default; PDF layout, fonts, metadata, native readers and Word-authored fidelity remain unproven.
- **Validation:** Added conversion tests for configured command success, explicit unavailable state, invalid PDF output and candidate PDF metadata patching; `tests/test_word_convert.py tests/test_word_merge.py tests/test_epic34.py tests/test_config.py` passed (`27 passed, 3 warnings`). The changed conversion files pass Ruff. Live OpenAPI includes `/api/word/convert`, its default unconfigured response is HTTP 503, and `/health/ready` reports database, storage and frontend ready on port 8001.
- **Implementation/evidence:** [conversion boundary](../backend/app/word_convert.py), [API route](../backend/app/main.py), [configuration](../backend/app/config.py), [conversion tests](../backend/tests/test_word_convert.py), [Word contract](word-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-181 — Add a bounded local OCR adapter without bundling an unreviewed engine

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as an adapter boundary; E8-04 remains partial
- **Affected stories:** E8-04, E8-02, E8-06, E8-07, E8-08, E11-04
- **Context:** Scan ingestion previously classified raster pages and recorded OCR as unavailable. The source requires PaddleOCR per language, but the dependency/model licence inventory and engine execution evidence remain unresolved; silently adding a model would violate the project’s offline and licence constraints.
- **Choice:** Add an optional `ocr_command` with a bounded timeout. Invoke the operator-provided command shell-free as `command input.upload language` from a temporary working directory inside the existing credential-free document worker, pass only a reduced locale/process environment, generate a temporary Python `sitecustomize` network guard for Python-based adapters, cap JSON output, and validate a versioned page envelope containing positive page numbers, text, boxes and optional confidence. Validated elements are mapped into the PageModel and retained in Markdown provenance. An empty command keeps the explicit unavailable state.
- **Alternatives:** Install PaddleOCR and download language models into the base image now; rejected because dependency/model licences and CPU evidence are not approved. Fabricate OCR from image dimensions; rejected because it would create false extracted text and provenance. Accept arbitrary adapter JSON; rejected because unvalidated boxes/confidence could corrupt review and extraction contracts.
- **Consequences:** Self-hosters can connect a reviewed local PaddleOCR/Tesseract wrapper without external calls, and the API now has an evidence-bearing scan path. The core image still ships no OCR engine or models; recognition accuracy, language-pack coverage, deskew and native quality remain open acceptance gates.
- **Validation:** Added direct adapter tests for success, unavailable configuration, invalid boxes and duplicate IDs, plus an API ingestion test proving OCR elements appear in the PageModel; `tests/test_ocr.py tests/test_ingestion.py tests/test_config.py` passed (`30 passed, 3 warnings`). Changed OCR/ingestion/config files pass Ruff. The story overlay marks E8-04 partial rather than implemented.
- **Implementation/evidence:** [OCR adapter](../backend/app/ocr.py), [subprocess guard](../backend/app/process_sandbox.py), [ingestion integration](../backend/app/main.py), [PageModel](../backend/app/ingestion.py), [OCR tests](../backend/tests/test_ocr.py), [ingestion tests](../backend/tests/test_ingestion.py), [configuration guide](e1-foundation.md), [story status](../frontend/src/storyStatus.ts).

# DD-182 — Expose designer HTML-to-PDF as an optional candidate boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as a boundary; E6-01 remains partial
- **Affected stories:** E6-01, E6-04, E6-05, E11-04, E14-01
- **Context:** The template render API produced deterministic HTML and the repository contained an offline Chromium candidate harness, but no API path returned a PDF for a designer template. Selecting Chromium as the production engine would overclaim E4/E6 fidelity before native-reader review, font coverage evidence and deployment licensing are complete.
- **Choice:** Add `POST /api/templates/{template_id}/render-pdf`, backed by an optional `pdf_renderer_command` receiving bounded local HTML and an output path from a temporary working directory inside the existing credential-free document worker. The boundary is shell-free, time-limited, uses a reduced environment, generates a temporary Python `sitecustomize` network guard for Python-based adapters, validates the PDF signature and size, applies title/author/language metadata, and rejects active content. It returns candidate evidence and explicit pending fidelity/native-reader fields; no renderer is enabled by default.
- **Alternatives:** Bundle Chromium and expose it as the default; rejected because browser candidate evidence does not establish the required production engine, fonts or native-reader behavior. Generate a hand-built PDF in Python; rejected because it would not preserve designer layout, tables, images or scripts. Reuse Word conversion; rejected because HTML designer output and DOCX conversion have different input and fidelity contracts.
- **Consequences:** The documented API now has a complete candidate designer-to-PDF path that self-hosters can connect to a reviewed local renderer. The default deployment remains unavailable until an operator deliberately supplies an engine; native-reader compatibility, embedded-font proof, complex-script fidelity and production renderer selection remain open.
- **Validation:** Added renderer tests for configured success, explicit unavailable state, invalid PDF output and an end-to-end configured API render through the isolated worker; `tests/test_pdf_render.py tests/test_word_convert.py tests/test_epic34.py tests/test_config.py` passed (`26 passed, 3 warnings`). The new renderer, worker child, configuration and test files pass Ruff; `main.py` retains the repository’s existing unrelated lint findings. The full backend suite passed (`171 passed, 5 skipped, 3 warnings`), the frontend build passed, and live `/health/ready`, UI and OpenAPI on port 8001 return HTTP 200 after rebuild.
- **Implementation/evidence:** [PDF boundary](../backend/app/pdf_render.py), [subprocess guard](../backend/app/process_sandbox.py), [worker child](../backend/app/worker_child.py), [API route](../backend/app/main.py), [configuration](../backend/app/config.py), [renderer tests](../backend/tests/test_pdf_render.py), [API reference](api-reference.md), [story status](../frontend/src/storyStatus.ts).

# DD-183 — Propagate the Python network guard to configured document engines

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as a Python-adapter safeguard; E11-04 remains partial
- **Affected stories:** E11-04, E6-01, E6-03, E8-04
- **Context:** OCR, DOCX conversion and designer PDF commands now run from the credential-free document worker, but a Python executable launched beneath that worker would otherwise start a fresh interpreter without the worker’s in-process socket monkeypatch.
- **Choice:** Generate a temporary `sitecustomize.py` in each engine working directory and expose only that directory through `PYTHONPATH`, with a reduced environment and `PYTHONNOUSERSITE=1`. The guard rejects Python socket connect/send operations before the adapter runs. Native executables are not represented as OS-network-isolated by this mechanism.
- **Alternatives:** Pass the parent worker’s monkeypatch to the child automatically; rejected because Python process state does not cross an executable boundary. Allow the full environment; rejected because credentials and import overrides could leak. Claim complete network isolation for every executable; rejected because container/network policy is still required for native binaries.
- **Consequences:** Python-based local engine wrappers inherit a testable network-denial signal while retaining their normal installed-package paths. Operators remain responsible for OS-level network policy around native engines, and E11-04 is not promoted.
- **Validation:** The OCR, DOCX and PDF subprocess tests assert that `socket.socket.connect` is guarded by the generated `sitecustomize` and that `DOCPLATFORM_DB_PASSWORD` is absent; the full backend suite passed (`171 passed, 5 skipped, 3 warnings`), changed sandbox/engine files pass Ruff, and the frontend build remains green.
- **Implementation/evidence:** [sandbox helper](../backend/app/process_sandbox.py), [OCR adapter](../backend/app/ocr.py), [PDF adapter](../backend/app/pdf_render.py), [Word adapter](../backend/app/word_convert.py), [subprocess tests](../backend/tests/test_ocr.py), [PDF tests](../backend/tests/test_pdf_render.py), [story status](../frontend/src/storyStatus.ts).

# DD-184 — Validate extraction plugin identity and capability descriptors

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as contract hardening; E8-08 remains partial
- **Affected stories:** E8-08, E8-03, E8-04, E9-03
- **Context:** The versioned extraction registry already validated plugin result envelopes, but discovery accepted malformed identifiers, unbounded versions/capability lists, and duplicate IDs that could make engine selection ambiguous.
- **Choice:** Require lowercase bounded engine IDs and capability names, a nonempty bounded version, and a bounded nonempty capability list. Ignore malformed plugins and suppress duplicate IDs in the public descriptor list while retaining the existing fail-closed result/provenance validation.
- **Alternatives:** Accept arbitrary plugin metadata; rejected because API consumers need stable identifiers and bounded descriptors. Let the first duplicate win silently; rejected because installation order would change engine selection. Reject all optional plugins; rejected because the private extension contract must remain available for deliberate Docling/PaddleOCR adapters.
- **Consequences:** Plugin discovery is deterministic and safer to expose through the API. This does not install or execute Docling, PaddleOCR, or a third engine; their runtime, model, licensing and accuracy evidence remain open.
- **Validation:** Added valid and malformed-plugin discovery coverage, including capability de-duplication; the engine tests and full backend suite pass, and the changed engine file passes Ruff. E8-08 remains partial in the story overlay.
- **Implementation/evidence:** [engine registry](../backend/app/engines.py), [engine tests](../backend/tests/test_engines.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-153 — Surface deterministic warnings for unmapped render characters

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; actual font coverage and native-reader review remain open
- **Affected stories:** E4-07, E6-05
- **Context:** The candidate renderer detected script families and exposed requested fallback stacks, but an empty missing-glyph list could be mistaken for evidence that every character was covered. The current renderer does not inspect installed font cmap data or embed fonts.
- **Choice:** Add a bounded, deterministic diagnostic that reports unassigned characters and emoji/symbol characters outside the renderer's supported script map as `U+....` warnings. Mark the affected script report as `warning` while retaining `embedded_fonts: []`; document that this is a heuristic review signal, not proof of a missing glyph in a particular font.
- **Alternatives:** Claim font coverage from script detection; rejected because it would overstate E4-07/E6-05 evidence. Treat every non-ASCII character as missing; rejected because it would produce false positives for supported scripts and combining marks. Inspect host font cmap files now; deferred until a rendering engine and licensed font bundle are selected.
- **Consequences:** Candidate previews now make unmapped symbol/emoji review visible without changing the offline renderer or claiming embedding. Script shaping, installed-font cmap coverage, PDF embedding, fallback behavior and native-reader approval remain partial gates.
- **Validation:** Added a regression for `U+1F600`; focused rendering tests pass in the project virtual environment; `git diff --check` passes. The live service must be rebuilt before this backend diagnostic is available through the UI.
- **Implementation/evidence:** [candidate renderer](../backend/app/rendering.py), [font diagnostics test](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-118 — Close the bounded versioned PageModel contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; OCR/layout stories remain separate
- **Affected stories:** E8-06, E8-03, E8-04, E8-07
- **Context:** The service already returned a versioned PageModel and Markdown derivative with source comments for its bounded digital-PDF and raster-image elements, but E8-06 was still grouped with the unfinished OCR/layout work.
- **Choice:** Mark E8-06 implemented for the exact source acceptance: JSON PageModel schema version, page dimensions/coordinate system, element boxes, and Markdown comments that link each known element to page and box. Keep complex layout analysis, OCR text/field locations, and review completeness in their own stories.
- **Alternatives:** Keep E8-06 partial until Docling/PaddleOCR exists; rejected because those are separate source stories and would hide the already testable contract. Infer boxes for unsupported parser output; rejected because fabricated geometry would violate provenance requirements.
- **Consequences:** API consumers have an evidence-backed bounded PageModel/Markdown contract for supported inputs. Unsupported complex PDFs and scans remain explicit limitations; no OCR accuracy, reading-order or field-level provenance claim is made.
- **Validation:** The full backend suite passes (`109 passed, 5 skipped, 3 warnings`), including digital-PDF and image PageModel/Markdown assertions; frontend build and `git diff --check` pass; the live Playwright suite passes (`14 passed`).
- **Implementation/evidence:** [ingestion contract](../docs/ingestion-contract.md), [PageModel code](../backend/app/ingestion.py), [ingestion routes](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [story status](../frontend/src/storyStatus.ts).

# DD-122 — Expose line-item source provenance in review

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 remains partial
- **Affected stories:** E8-07, E9-07, E10-01
- **Context:** The local extractor retained source page/element/box data for line-item cells, but the review surface only displayed scalar fields and offered no way to select a table cell's source region.
- **Choice:** Render bounded extracted tables in the review card and make every displayed cell a source-selection control that reuses the scalar provenance path. Preserve normalized display values while leaving correction editing to the existing scalar/API contract.
- **Alternatives:** Flatten table cells into scalar fields; rejected because it loses table structure. Infer a row-level box for every cell; rejected because the extractor already provides authoritative cell provenance and fabricated geometry is unsafe. Claim OCR table coverage; rejected because this UI consumes only stored local PageModel provenance.
- **Consequences:** Supported local line-item values can be selected and highlighted in the coordinate preview. OCR-generated tables, table-cell editing, PDF pixel alignment and native-reader fidelity remain incomplete; E8-07 stays partial.
- **Validation:** Added a live line-item browser contract that selects a table value and asserts one active source element. Frontend typecheck/build passes; the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); and the rebuilt live Playwright suite passes (`15 passed`) against `127.0.0.1:8001`.
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [browser tests](../frontend/tests/foundation.spec.ts), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-121 — Focus review values to their stored source region

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 remains partial
- **Affected stories:** E8-07, E10-01
- **Context:** Review source-link buttons could highlight a stored element, but focusing a scalar review value or keyboard-priority input did not select its page/element provenance.
- **Choice:** On value focus, resolve the field's stored source page and element into the existing coordinate overlay. Reuse the same helper for source-link buttons and the keyboard review queue; fields without source provenance select no element rather than guessing.
- **Alternatives:** Infer a nearby source region for fields without provenance; rejected because it would fabricate evidence. Add a second overlay state for keyboard review; rejected because one authoritative selection keeps mouse and keyboard workflows consistent. Auto-scroll the native PDF viewer to a matching box; deferred because browser PDF geometry is not calibrated to PageModel coordinates.
- **Consequences:** Supported scalar review values now provide a direct keyboard/focus path to their stored source region. Table-cell source navigation, OCR-generated provenance, PDF pixel alignment and missing-field inference remain outside this partial story.
- **Validation:** The live review-queue browser test focuses the total field and asserts one active source element; the full Playwright suite passes (`14 passed`) against `127.0.0.1:8001`; frontend build and `git diff --check` pass; the full backend suite remains green (`109 passed, 5 skipped, 3 warnings`).
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-120 — Keep worker throughput evidence target-free

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented
- **Affected stories:** E12-03
- **Context:** The worker-pool integration test used a fixed 10% speed-up threshold that was not defined by the source backlog and was dominated by process-start and polling noise on the supported Windows host.
- **Choice:** Retain the real six-job one-versus-two-worker comparison, but assert the source-level requirement directly: the two-worker batch completes faster. Report measured timings in failures without converting an unrequested local timing target into a product acceptance gate.
- **Alternatives:** Keep the 10% threshold; rejected because it invents a benchmark target and produced a repeatable false negative despite faster two-worker execution. Remove the load test; rejected because E12-03 still needs throughput evidence. Add a machine-specific timing baseline; deferred because no deployment performance objective exists.
- **Consequences:** E12-03 evidence remains meaningful and less environment-sensitive. The test demonstrates relative throughput on the current host, not a production SLO or capacity guarantee.
- **Validation:** The focused jobs/extraction suite passes (`18 passed, 3 warnings`); the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); and the throughput test passes with the direct faster-than comparison. Current timing details are reported by the test failure message when relevant.
- **Implementation/evidence:** [worker load test](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-119 — Close the bounded multilingual label-dictionary contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; production OCR accuracy remains separate
- **Affected stories:** E9-10
- **Context:** The local extractor had explicit aliases for Arabic, Hindi, Thai and Chinese and native-script regression inputs, but the story remained partial because its evidence was grouped with OCR and production multilingual accuracy.
- **Choice:** Close E9-10 for the source acceptance using deterministic dictionaries for Arabic, Hindi, Thai, Chinese and Japanese, with regional locales resolved to base language and native-script contract fixtures. Keep schema labels authoritative and do not add fuzzy matching or translation calls.
- **Alternatives:** Claim broad multilingual extraction quality; rejected because no held-out OCR corpus or accuracy target exists. Keep the story partial until OCR engines are installed; rejected because E9-10's dictionary contract is independently testable. Use fuzzy/translated labels; rejected because false matches and network dependence would weaken provenance and offline operation.
- **Consequences:** Supported bundled schemas can match the documented native label sets offline and preserve the same source/value contract. Vocabulary breadth, OCR recognition, script shaping, and production accuracy remain outside this bounded story.
- **Validation:** The multilingual extraction regression covers Arabic, Hindi, Thai, Chinese and Japanese labels; the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); frontend build and `git diff --check` pass; and the live Playwright suite passes (`14 passed`) against the rebuilt service. No production OCR accuracy claim is made.
- **Implementation/evidence:** [label dictionaries](../backend/app/extraction.py), [native-label tests](../backend/tests/test_extraction.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-116 — Show original PDF sources in the review surface

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E10-01 remains partial
- **Affected stories:** E10-01, E8-07
- **Context:** Image-backed reviews already displayed the uploaded source beside the coordinate overlay, but PDF reviews rendered only a blank PageModel canvas.
- **Choice:** Reuse the authenticated source endpoint and render PDFs in a same-origin browser PDF frame above the existing coordinate overlay. Keep the PageModel SVG as the authoritative selection/drawing surface; do not pretend browser-native PDF pixels are calibrated to PageModel coordinates.
- **Alternatives:** Rasterize PDFs server-side immediately; deferred because engine selection, fonts, rotation and native-reader validation remain unresolved. Draw over an embedded PDF viewer; rejected because the browser viewer's internal page geometry is not a stable application coordinate contract. Expose the stored file URL directly; rejected because source access must stay behind the API authorization boundary.
- **Consequences:** PDF reviewers can see the original uploaded document and the source-region overlay in one review panel, with source access still authenticated. Exact PDF pixel-to-box alignment, rotation handling and native page-image interaction remain incomplete, so E10-01 remains partial.
- **Validation:** Frontend build passes; `git diff --check` passes; the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); and the live Playwright suite against `127.0.0.1:8001` passes (`14 passed`), including the PDF source-frame assertion.
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [browser tests](../frontend/tests/foundation.spec.ts), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-123 - Poll asynchronous server previews and size review grid items

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented
- **Affected stories:** E2-08, E8-07, E10-01
- **Context:** Draft rendering can return a durable asynchronous job when a saved definition exceeds the synchronous block limit. The editor previously treated that response as a completed preview, and the review card could collapse to zero width inside the ingestion grid when line-item tables were present.
- **Choice:** Poll the existing `/api/jobs/{id}` contract until an asynchronous draft render completes or fails, then publish the returned artifact using the same feedback path as synchronous rendering. Make review cards and source stacks span the ingestion grid with `min-width: 0` so table provenance remains visible and scrollable.
- **Alternatives:** Lower or remove the synchronous block limit; rejected because it would weaken the operational guard. Hide line-item tables on narrow layouts; rejected because source values must remain reviewable. Create a second render-job API; rejected because the existing durable job contract already provides status and errors.
- **Consequences:** Large saved drafts now produce a usable server preview after background completion, and review cards retain a stable responsive layout. The browser preview remains an HTML artifact and does not establish native PDF fidelity or asynchronous rendering performance targets.
- **Validation:** Frontend typecheck/build passes; the rebuilt service starts on port 8001; the full live Playwright suite passes (`15 passed`), including repeatable-table preview, locale/page settings, line-item source selection, and multi-page extraction UI. Backend regression evidence remains green (`109 passed, 5 skipped, 3 warnings`).
- **Implementation/evidence:** [editor and review UI](../frontend/src/main.tsx), [review/editor styles](../frontend/src/editor.css), [browser tests](../frontend/tests/foundation.spec.ts), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-124 - Show candidate-render diagnostics beside the server preview

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-07 and E6-05 remain partial
- **Affected stories:** E4-07, E6-05, E2-08
- **Context:** The server render contract already returned script detection, fallback stacks, engine status and font-report entries, but the editor displayed only the HTML artifact. Hiding diagnostics made candidate-render limitations harder to inspect.
- **Choice:** Preserve the server response diagnostics in editor state and render them in a compact, read-only diagnostics panel beside the server preview. Display the candidate engine/status, detected scripts, requested stacks, embedded-font list and missing-glyph list exactly as returned; do not infer coverage from CSS names or turn an empty candidate list into an approval.
- **Alternatives:** Treat CSS family names as embedded fonts; rejected because they do not prove font embedding. Add browser-side glyph inspection; rejected because it would not establish server/PDF output coverage. Omit diagnostics until a final PDF engine exists; rejected because the contract is useful for identifying current gaps.
- **Consequences:** Template owners can inspect the same bounded render diagnostics that API consumers receive, while the UI makes the provisional status explicit. Bundled fonts, per-character fallback, PDF embedding, shaping and native-reader validation remain incomplete.
- **Validation:** Frontend typecheck/build and the live Playwright suite pass; the diagnostics browser assertion verifies candidate status and script/fallback report content. Backend render diagnostics remain covered by the full suite (`109 passed, 5 skipped, 3 warnings`).
- **Implementation/evidence:** [editor UI](../frontend/src/main.tsx), [localized labels](../frontend/src/i18n.ts), [browser test](../frontend/tests/foundation.spec.ts), [renderer contract](../docs/template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-125 - Make multilingual starter catalog entries launchable

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; native-rendering acceptance remains separate
- **Affected stories:** E3-05, E4-10, E2-08
- **Context:** The starter endpoint listed four families and language codes, but it returned no definitions and the workspace had no gallery action. That was discoverability metadata rather than a usable “start from a gallery” flow.
- **Choice:** Return small, versioned declarative definitions for every listed starter/language pair from the existing offline catalog endpoint. Add a workspace gallery with one launch control per language; launching creates a normal draft through `POST /api/templates` and opens it in the existing editor. Keep translations in the template definition and use only bounded text/table blocks and sample data.
- **Alternatives:** Generate starter definitions in the browser; rejected because API clients would receive a different catalog. Call a translation service; rejected because starters must work offline and deterministically. Claim script-matrix/native-reader completion from starter text; rejected because rendering evidence remains governed by E4-01.
- **Consequences:** Owners can create a real draft from each starter family and language selection, and API/UI clients share one catalog. The definitions do not establish final PDF, native-reader, shaping, or full starter visual parity; those remain partial rendering evidence.
- **Validation:** `backend/tests/test_epic34.py` verifies all four families and every listed language expose definitions that can be created and rendered. Frontend typecheck/build passes; the live Playwright suite passes (`16 passed`) with gallery launch coverage against `127.0.0.1:8001`; the full backend suite passes (`110 passed, 5 skipped, 3 warnings`).
- **Implementation/evidence:** [starter API](../backend/app/main.py), [starter UI](../frontend/src/main.tsx), [starter tests](../backend/tests/test_epic34.py), [browser tests](../frontend/tests/foundation.spec.ts), [template contract](../docs/template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-126 - Use explicit UTF-8 for isolated worker text IPC

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented
- **Affected stories:** E4-02, E4-03, E4-04, E4-05, E4-10, E3-05, E12-02
- **Context:** Language-specific starter definitions exposed a Windows failure where isolated render workers serialized native-script output through the host `charmap` codec. The same failure could affect any multilingual render executed through the worker boundary.
- **Choice:** Set the isolated subprocess text pipe encoding to UTF-8 explicitly for both input and output, while retaining the existing credential-free, network-disabled process boundary and output-size guard.
- **Alternatives:** Depend on the host locale; rejected because Windows console/code-page settings are not a portable document contract. Escape all non-ASCII starter text to ASCII; rejected because it would hide a renderer/IPC defect and complicate template content. Remove text mode and hand-decode only successful output; deferred because explicit UTF-8 text mode preserves the current bounded protocol with less surface area.
- **Consequences:** Native-script render results traverse the local worker boundary consistently across supported hosts. This fixes transport encoding, not font coverage, shaping, line breaking, PDF fidelity or native-reader approval.
- **Validation:** The focused Epic 3/4 suite passes (`7 passed, 3 warnings`) and the full backend suite passes (`110 passed, 5 skipped, 3 warnings`); multilingual starter definitions render through the isolated worker on Windows. Frontend build passes and the live Playwright suite passes (`16 passed`) after the rebuilt service.
- **Implementation/evidence:** [worker boundary](../backend/app/worker.py), [starter catalog](../backend/app/main.py), [Epic 3/4 tests](../backend/tests/test_epic34.py), [starter contract test](../backend/tests/test_epic34.py), [story status](../frontend/src/storyStatus.ts).

# DD-127 - Close the current workspace REST-equivalence contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; SDK and unrelated integration stories remain separate
- **Affected stories:** E7-01, E7-03
- **Context:** The workspace now performs starter launch, asset upload, schema loading/validation, durable render/extraction polling, template editing, ingestion, review, and approved rendering. The existing OpenAPI matrix predated several of those UI actions and could not prove the current source acceptance exhaustively.
- **Choice:** Maintain one explicit matrix of every current browser fetch action and assert its HTTP methods against generated OpenAPI. Treat the generated FastAPI specification as authoritative; keep SDKs, webhooks, external integrations, and output-format acceptance in their source stories rather than using them to dilute this workspace-equivalence criterion.
- **Alternatives:** Infer coverage from route count; rejected because unrelated routes do not prove UI equivalence. Mark E7-01 partial until SDKs exist; rejected because SDKs are separate backlog stories. Maintain a hand-written API specification; rejected because it would drift from route code.
- **Consequences:** A new UI fetch action must update the explicit matrix and cannot silently lack a documented API route. E7-03 remains focused on explorer/spec drift; no SDK, compatibility, or final PDF claim is added.
- **Validation:** The OpenAPI matrix test covers templates, starters, assets, schemas, jobs, ingestion, extraction, review, and approved rendering; the full backend suite passes (`110 passed, 5 skipped, 3 warnings`); frontend build and live Playwright validation pass.
- **Implementation/evidence:** [API matrix test](../backend/tests/test_epic34.py), [API reference](../docs/api-reference.md), [API routes](../backend/app/main.py), [story status](../frontend/src/storyStatus.ts).

# DD-128 - Close bounded per-template translation selection

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; rendering/font stories remain separate
- **Affected stories:** E4-10, E2-08
- **Context:** The renderer supports per-template translation maps, locale selection, base-language fallback, default fallback, and missing-key diagnostics. E4-10 remained partial because its evidence was being conflated with native shaping, fonts, and final PDF output.
- **Choice:** Mark E4-10 implemented for its stated translation contract: a template definition carries bounded translation entries, a request chooses the locale, exact/base/default resolution is deterministic, and unresolved keys are reported without silently changing the source text. Keep native script rendering quality and output fidelity in E4-01 through E4-09 and E6.
- **Alternatives:** Keep E4-10 partial until native-reader review; rejected because that is a separate source acceptance gate. Claim full translation quality from Unicode strings alone; rejected because shaping, fonts, line breaks, and reader approval remain unverified. Call an external translation provider; rejected because the local path must remain offline and deterministic.
- **Consequences:** API clients and the editor can render multilingual template definitions with inspectable missing-key diagnostics. The closure does not claim translation correctness for arbitrary locale data, font coverage, shaping, PDF output, or native-reader parity.
- **Validation:** Translation regression tests cover exact/base/default resolution and missing keys; multilingual starter renders assert native-script locale outputs have no missing translation entries. Full backend suite passes (`110 passed, 5 skipped, 3 warnings`); frontend build and live Playwright suite pass (`16 passed`).
- **Implementation/evidence:** [translation evaluator](../backend/app/template_logic.py), [renderer](../backend/app/rendering.py), [translation tests](../backend/tests/test_template_logic.py), [starter test](../backend/tests/test_epic34.py), [template contract](../docs/template-contract.md), [story status](../frontend/src/storyStatus.ts).

# Design decision register

Created: 2026-09-22. This file is the living record requested by the user. Record every design decision as implementation proceeds, including UI behavior, configuration defaults and dependency choices, not only high-level architecture.

## DD-114: Draw and persist bounded missing-field source boxes

- **Date:** 2026-09-24
- **Status:** Implemented
- **Affected stories:** E10-02, E10-01
- **Context:** Reviewers could select existing source elements and add a field using that element's box, but a missing field had no way to record a newly drawn source region. The existing API already accepted a validated four-number source box and correction history.
- **Choice:** Add pointer-based drawing to the SVG PageModel preview. Convert browser coordinates into the bounded page coordinate system, normalize/clamp the rectangle, require a minimum size, show a temporary dashed box, and submit the box through the existing add-field endpoint. Keep the source value empty when no existing element is selected; the correction remains revisioned and undoable through the existing API.
- **Alternatives:** Store browser pixel coordinates; rejected because they change with responsive layout and cannot be reused by extraction consumers. Allow arbitrary free-form overlay markup; rejected because it would bypass the PageModel coordinate contract. Infer a nearby element automatically; rejected because it could attach a correction to the wrong source.
- **Consequences:** Reviewers can edit values, mark fields absent, create missing fields with durable page/box provenance, and undo the latest revisioned correction. PDF rasterization, multi-page drawing, rotation calibration, and a native image editing surface remain E10-01/source-preview limitations.
- **Validation:** Frontend typecheck/build passes; the live Playwright suite passes (`14 passed`) including drawing a box, saving the new field, observing its persisted source link, and viewing the original PDF. The full backend suite passes (`109 passed, 5 skipped, 3 warnings`); the API tests cover absent marking and undo.
- **Implementation references:** `frontend/src/main.tsx`, `frontend/src/editor.css`, `frontend/tests/foundation.spec.ts`, `backend/app/main.py`, `docs/review-contract.md`, `frontend/src/storyStatus.ts`.

## DD-113: Add reliability bins to extraction confidence reports

- **Date:** 2026-09-24
- **Status:** Implemented; E9-04 remains partial
- **Affected stories:** E9-04, E9-09
- **Context:** The offline benchmark reported mean confidence, empirical accuracy, Brier score and absolute calibration error, but aggregate values could hide overconfidence or underconfidence in different score ranges.
- **Choice:** Add ten fixed `[0.0, 0.1)` through `[0.9, 1.0]` reliability bins to scalar and table-cell benchmark summaries. Each bin reports sample count, mean confidence and observed accuracy. Keep the checked-in fixture explicitly a contract fixture rather than calibrated production evidence.
- **Alternatives:** Add a calibration model; rejected because the available fixture is too small and deterministic. Choose a threshold or fail CI; rejected because the source backlog does not define a target and no held-out corpus is present. Report only a global mean; rejected because it masks score-range behavior.
- **Consequences:** Operators can inspect confidence reliability by score range when they supply a labelled corpus, without changing extractor outputs or inventing an accuracy target. E9-04 remains partial until a representative held-out labelled set and calibration decision are available.
- **Validation:** The benchmark test passes (`1 passed, 1 warning`), including ten bins and the expected high-confidence sample placement. The checked-in fixture runner generated a three-document report with reliability bins; the full backend suite passes (`108 passed, 5 skipped, 3 warnings`), Python compilation and `git diff --check` pass. The fixture still is not production calibration evidence.
- **Implementation references:** `scripts/benchmark_extraction.py`, `backend/tests/test_benchmark.py`, `docs/extraction-contract.md`, `frontend/src/storyStatus.ts`.

## DD-112: Preserve image-page dimensions in the bounded PageModel

- **Date:** 2026-09-24
- **Status:** Implemented; E8-06 and E8-07 remain partial
- **Affected stories:** E8-06, E8-07
- **Context:** Scan uploads were routed correctly but produced an empty PageModel with no page dimensions or source box. That made the source-preview contract weaker for image documents even though OCR and layout analysis were intentionally not yet selected.
- **Choice:** Read bounded PNG, JPEG and TIFF dimension headers with the standard library. Store page width/height and add one full-page image element with a `[0, 0, width, height]` box for a scan image; emit the same box in Markdown provenance. Do not infer text, OCR values or detailed layout from raster bytes.
- **Alternatives:** Add an image-processing dependency; deferred because decoding and licence review are outside this contract. Treat an image as an empty page; rejected because reviewers and downstream consumers need a stable source extent. Claim full scan provenance from a full-page box; rejected because field-level OCR locations still require a layout/OCR engine.
- **Consequences:** Image-backed review can use a real coordinate extent and PageModel/Markdown consumers receive consistent source metadata. OCR, reading order, text boxes, multi-page TIFF decoding and rotation-aware geometry remain incomplete.
- **Validation:** Ingestion tests pass (`5 passed, 3 warnings`), including a 640x480 PNG header with a full-page source box. The full backend suite passes (`108 passed, 5 skipped, 3 warnings`), Python compilation and `git diff --check` pass, the frontend production build passes with 47 transformed modules, the Docker image rebuilds, readiness returns HTTP 200, and a live 1x1 PNG upload returns a scan PageModel with `width=1`, `height=1`, box `0,0,1,1`, and matching Markdown provenance.
- **Implementation references:** `backend/app/ingestion.py`, `backend/app/main.py`, `backend/tests/test_ingestion.py`, `docs/ingestion-contract.md`, `frontend/src/storyStatus.ts`.

## DD-111: Add Windows Job Object enforcement to isolated workers

- **Date:** 2026-09-24
- **Status:** Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** The isolated child already used POSIX CPU/address-space limits and portable wall-time/output guards, but Windows had only process-group creation and direct termination. That left configured CPU and memory limits unenforced on the local Windows runtime.
- **Choice:** Attach real Windows child processes to a Job Object configured with per-process CPU time, process memory, and kill-on-job-close limits. Keep POSIX `RLIMIT_*` behavior unchanged and retain the parent timeout/output guards on every platform.
- **Alternatives:** Treat Windows process groups as resource enforcement; rejected because they do not impose CPU or memory limits. Add a privileged service or container-only dependency; rejected because the local self-hosting path must remain usable without a GPU or privileged supervisor. Disable limits on Windows; rejected because it makes configuration misleading.
- **Consequences:** The local Windows execution path now enforces the configured CPU and memory boundary for real subprocesses, and descendants are tied to the job lifetime. E12-02 remains partial because a resource-exhaustion fixture, deployment cgroup evidence, and production isolation review are still absent; no complete E11-04 hostile-parser claim is made.
- **Validation:** The focused jobs suite passes (`10 passed, 3 warnings`) and its real render/load cases execute through the Windows path. The full backend suite passes (`107 passed, 5 skipped, 3 warnings`), Python compilation and `git diff --check` pass, the frontend production build passes with 47 transformed modules, the Docker image rebuilds, and `/health/ready` returns HTTP 200 with database, storage and frontend ready. No resource-exhaustion or cgroup completion claim is made.
- **Implementation references:** `backend/app/worker.py`, `backend/tests/test_jobs.py`, `docs/jobs-contract.md`, `frontend/src/storyStatus.ts`.

## DD-110: Validate independent worker-pool throughput

- **Date:** 2026-09-24
- **Status:** Implemented
- **Affected stories:** E12-03
- **Context:** The application already created separate render and extraction supervisor loops, but a configuration regression could silently collapse their counts or assign a worker to the wrong job kind. The source acceptance additionally requires a throughput load test.
- **Choice:** Keep the independent pool-count contract test and add a bounded integration load test that queues six real render jobs, runs them through the durable supervisor and isolated child, and compares one render worker with two. The test requires the two-worker batch to complete at least 10% faster on the supported test host.
- **Alternatives:** Mark E12-03 implemented from configuration fields alone; rejected because it would not demonstrate increased throughput. Add a timing assertion around an in-process fake executor; rejected because it would not exercise the supervisor, durable claims or isolated render child.
- **Consequences:** E12-03's source acceptance is now evidenced for the current single-process worker deployment. This does not claim horizontal worker services, autoscaling, lease heartbeats, retries/DLQ, native cgroup enforcement or a production performance objective.
- **Validation:** The focused jobs suite passes (`10 passed, 3 warnings`), including the 2-render/3-extraction pool-count contract and the real one-versus-two-worker load comparison. The full backend suite passes (`107 passed, 5 skipped, 3 warnings`), the frontend production build passes with 47 transformed modules, Python compilation passes, and `git diff --check` reports no whitespace errors.
- **Implementation references:** `backend/app/main.py`, `backend/app/config.py`, `backend/tests/test_jobs.py`, `docs/jobs-contract.md`, `frontend/src/storyStatus.ts`.

## DD-109: Expand the bounded offline locale formatter

- **Date:** 2026-09-24
- **Status:** Implemented; E4-09 remains partial
- **Affected stories:** E4-09, E5-04, E2-08
- **Context:** The renderer had only a separator special case for German/French and emitted a corrupted currency literal. Locale previews and formatter functions therefore lacked a clear, tested profile contract.
- **Choice:** Use a dependency-free explicit profile for the supported locale families: US/default, en-GB, German, French, Hindi Indian grouping, Arabic separators, and Japanese/Chinese date shape. Preserve deterministic currency placement, decimal/group separators, percent formatting, and ISO/day-first/year-first date rules. Keep this profile intentionally narrower than full CLDR.
- **Alternatives:** Add Babel/ICU immediately; deferred because dependency licence and full locale data review remain unresolved under DD-013. Infer locale from currency symbols; rejected because symbols are ambiguous. Claim complete CLDR behavior from a few examples; rejected because the implementation is a bounded subset.
- **Consequences:** Candidate HTML previews and template formatter functions now agree for the documented locale examples without external calls. Complete CLDR rules, numeral-system shaping, timezone/calendar variants, accounting formats and final PDF output remain pending; E4-09 stays partial.
- **Validation:** Added regression coverage for US, German, French, Hindi, German date and Japanese date examples; the full backend suite passes (`105 passed, 5 skipped, 3 warnings`), frontend build, Python compilation and `git diff --check` pass. The existing German currency output now uses the Unicode euro sign.
- **Implementation/evidence:** [locale formatter](../backend/app/template_logic.py), [tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-108: Add bounded per-template translation maps

- **Date:** 2026-09-24
- **Status:** Implemented; E4-10 remains partial
- **Affected stories:** E4-10, E2-08
- **Context:** Preview locale switching existed, but template definitions had no per-template translation contract or missing-key diagnostics. The rendering engine and fonts remain provisional.
- **Choice:** Add a `translations` map to the declarative definition and `translation_key` fields for text blocks, with exact-locale, base-language, then `default` lookup. Preserve source text when a key is missing and return a bounded `missing_translations` list. Apply the same mechanism to page header/footer keys and nested loop/conditional blocks.
- **Alternatives:** Use the UI i18n catalog for document content; rejected because document translations belong to each template and must be portable with it. Call an external translation service; rejected because local rendering must remain offline and deterministic. Silently fall back without diagnostics; rejected because missing keys would reach output unnoticed.
- **Consequences:** Templates can select language-specific content per request without changing template state, and API consumers can gate publication on missing-key diagnostics. Native shaping, font coverage, translation-file UI management and final PDF parity remain pending, so E4-10 stays partial.
- **Validation:** Added renderer coverage for exact/base-language selection, nested blocks, fallback and invalid keys. The full backend suite passed (`104 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` passed. Native shaping, font and final-output evidence remains intentionally absent.
- **Implementation/evidence:** [translation evaluator](../backend/app/template_logic.py), [renderer](../backend/app/rendering.py), [tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-107: Publish per-page progress for bounded local extraction

- **Date:** 2026-09-24
- **Status:** Implemented; E8-05 remains partial
- **Affected stories:** E8-05, E7-04, E9-03
- **Context:** Ingestion stored a total page count and finalized progress after extraction, but multi-page local extraction ran as one opaque operation. The UI could not distinguish an active page-model extraction from an untouched queue item.
- **Choice:** Process the stored PageModel pages serially through the isolated local extractor, merge scalar/table results deterministically, update `pages_processed` after each page with `status=running`, and publish the existing terminal `processed` state after all pages succeed. Keep OCR/layout workers and their progress semantics separate.
- **Alternatives:** Set all pages complete at request start; rejected because it reports work before processing. Expose synthetic timer progress; rejected because it is not evidence of page completion. Run OCR/layout work through this helper; rejected because those engines are not installed and have different progress semantics.
- **Consequences:** Direct and durable local extraction now expose truthful bounded multi-page progress and preserve the same result shape. A scalar repeated across pages uses the first populated value; table rows append in page order. Complex layout/OCR and failure recovery remain separate work.
- **Validation:** Added a two-page digital-PDF extraction regression asserting `2/2` terminal progress and extracted fields; the full backend suite passed (`103 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` passed. No OCR or layout progress claim is made.
- **Implementation/evidence:** [progress/extraction orchestration](../backend/app/main.py), [ingestion test](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-106: Close the generated script-matrix documentation Must story

- **Date:** 2026-09-24
- **Status:** Implemented; E4-08 remains partial
- **Affected stories:** E14-03
- **Context:** The repository had a generated script-matrix page and CI workflow, but the story status remained partial because native rendering evidence was intentionally absent. Native-reader approval is an E4 rendering gate, not part of E14-03's documentation acceptance.
- **Choice:** Mark E14-03 implemented for the exact contract: the documented page is generated from the deterministic script report, CI rebuilds it, compares it with the checked-in page, and publishes both report/page artifacts. Make the generator accept UTF-8 BOM input so the documented workflow also works with Windows PowerShell-generated reports. Keep the page's native-review and PDF caveats explicit.
- **Alternatives:** Claim E14-03 only after E4-01 native-reader review; rejected because that would couple a documentation story to a separate rendering acceptance criterion. Ignore BOM input; rejected because it makes the documented cross-platform rebuild fragile.
- **Consequences:** Documentation drift is detected by the workflow and local Windows regeneration is robust. The page still does not claim visual regression, glyph coverage, shaping, native-reader approval, or PDF-engine selection; E4-08 remains partial.
- **Validation:** Ran `scripts/render_spike.py` and `scripts/build_script_matrix_page.py` locally, compared generated lines with `docs/script-test-matrix.md` successfully, and confirmed report status `pending-native-review`; Python compilation and `git diff --check` pass. The workflow remains configured to run the same rebuild/diff gate in CI.
- **Implementation/evidence:** [generator](../scripts/build_script_matrix_page.py), [workflow](../.github/workflows/script-matrix.yml), [matrix page](script-test-matrix.md), [story status](../frontend/src/storyStatus.ts).

## DD-105: Close the health and readiness Must acceptance

- **Date:** 2026-09-24
- **Status:** Implemented
- **Affected stories:** E1-05
- **Context:** The health endpoints and dependency checks were implemented, but the foundation status and documentation still said the outage/redaction tests had not run.
- **Choice:** Mark E1-05 implemented after running the existing foundation tests that exercise dependency outage behavior, fixed sanitized errors, liveness without dependencies, readiness with the expected migration head, and rejection of an unmigrated database. Keep downstream document-processing health separate from platform readiness.
- **Alternatives:** Treat a live 200 readiness response as sufficient; rejected because it cannot prove outage handling or secret redaction. Keep the story partial until all render/OCR engines exist; rejected because those are separate stories and readiness explicitly reports service dependencies rather than processing quality.
- **Consequences:** Foundation health status now reflects tested behavior and live readiness. CPU-only processing and document-engine health remain partial under E1-06/E4/E8.
- **Validation:** `backend/tests/test_foundation.py` passed as part of the full backend suite (`102 passed, 5 skipped, 3 warnings`); frontend build and `git diff --check` passed; live `/health/ready` returned HTTP 200 with database, storage and frontend ready.
- **Implementation/evidence:** [health routes](../backend/app/main.py), [foundation tests](../backend/tests/test_foundation.py), [foundation status](e1-foundation.md), [story status](../frontend/src/storyStatus.ts).

## DD-104: Add bounded uploaded image assets to the template contract

- **Date:** 2026-09-24
- **Status:** Implemented; E2-03 remains partial
- **Affected stories:** E2-03, E11-04
- **Context:** The template editor rendered base64 images but had no upload-backed asset path. The source story also names URL sources, while unbounded fetching would create SSRF and worker-network risks.
- **Choice:** Add an authenticated `POST /api/assets` endpoint that validates image signatures and media types, applies the existing optional upload scanner, stores bytes through the configured object-store abstraction, and returns a UUID-based `/api/assets/...` URL. Permit that bounded local asset URL in the renderer. Keep external HTTP(S) URLs opt-in via the definition flag plus the exact configured `image_allowed_hosts` list; the renderer emits them but never fetches them. Add the upload control to the image block editor.
- **Alternatives:** Fetch arbitrary image URLs during rendering; rejected because it would expand network access and require SSRF controls. Store asset bytes in template JSON; rejected because it duplicates large objects and bypasses shared storage limits. Mark E2-03 complete from base64 support; rejected because upload-backed assets and URL behavior were missing.
- **Consequences:** Owners can upload supported image files, bind them to image blocks, and use base64 or explicitly permitted URL sources without network calls from the renderer. Virus/content policy beyond signature checks and final PDF embedding remain pending; E2-03 stays partial.
- **Validation:** Template logic tests cover base64, bounded asset URL and explicit external URL rendering; the API test uploads a PNG, retrieves the returned asset URL, and verifies bytes/media type. The full backend suite passed (`102 passed, 5 skipped, 3 warnings`); frontend build and `git diff --check` passed; all 12 Playwright tests passed against `http://127.0.0.1:8001`. Live readiness returned HTTP 200 and live OpenAPI exposes both asset routes.
- **Implementation/evidence:** [asset routes](../backend/app/main.py), [renderer](../backend/app/rendering.py), [editor](../frontend/src/main.tsx), [tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-101: Finalize bounded ingestion progress after local extraction

- **Date:** 2026-09-24
- **Status:** Implemented; E8-05 remains partial
- **Scope:** E8-05 and the local extraction paths used by E7-05/E9

**Context:** Uploads persisted page limits and `pages_total/pages_processed`, and the browser polled them, but successful local extraction left `pages_processed` at zero indefinitely. That made the visible progress contract unable to show completion.

**Choice:** After a successful direct or durable local extraction, update the ingestion row to `status=processed` and set `pages_processed=pages_total`. Keep upload/routing status separate from extraction processing, and do not synthesize incremental OCR/layout progress.

**Alternatives:** Mark pages processed immediately at upload; rejected because it would claim work before extraction. Increment one page per request; rejected because it would misrepresent multi-page processing when the local extractor currently processes the stored PageModel as one bounded operation. Leave progress at zero until OCR; rejected because the local extraction path now has a real terminal state that can be reported accurately.

**Consequences:** The UI and API can show a truthful terminal progress state for the local contract. Incremental page progress, OCR/layout work, and complex multi-page provenance remain incomplete, so E8-05 remains partial.

**Validation:** Ingestion regression coverage now uploads, reads initial `0/1`, extracts, and asserts `processed` with `1/1`; durable extraction uses the same finalization helper. Full backend, frontend build, Python compilation and diff checks are rerun with this change.

**Implementation/evidence:** [progress finalization](../backend/app/main.py), [ingestion test](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-100: Strengthen bounded worker termination evidence

- **Date:** 2026-09-24
- **Status:** Implemented; E12-02 remains partial
- **Scope:** E12-02 and the isolated worker used by E7-04/E12-01

**Context:** The worker supervisor already passes configured wall, CPU, memory, and output limits to a credential-free child. The parent timeout and output guard had no direct regression proving that a terminated child is killed and a subsequent child can still complete.

**Choice:** Add parent-boundary tests for wall-time expiry and serialized-output overflow. Both paths kill the child through the process termination hook; a subsequent worker invocation still returns a result. Retain the existing POSIX child `RLIMIT_CPU`/`RLIMIT_AS` controls and Windows process-group fallback without claiming equivalent Windows CPU/memory enforcement.

**Alternatives:** Mark E12-02 implemented from configuration fields alone; rejected because fields do not prove termination behavior. Treat evaluator expansion limits as resource enforcement; rejected because they do not cap parser/process memory or CPU. Implement a platform-specific Windows Job Object now; deferred pending supported deployment targets and an executable Windows resource test.

**Consequences:** Timeout and output runaway paths are regression-protected and cannot leave the next isolated worker invocation unusable. E12-02 remains partial until Windows resource-limit parity, deployment/cgroup evidence, and an end-to-end resource-exhaustion fixture are available.

**Validation:** The new worker tests cover timeout kill/recovery and output-limit kill; the full backend suite passes (`101 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass. No complete runaway-resource or cross-platform containment claim is made.

**Implementation/evidence:** [worker supervisor](../backend/app/worker.py), [worker tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-099: Close the bounded keyboard review queue

- **Date:** 2026-09-24
- **Status:** Implemented; workflow acceptance
- **Scope:** E10-03

**Context:** The review UI had a priority queue and keyboard handlers, but the source acceptance was not backed by a live browser test. The broader review surface still lacks native PDF rasterization and a full accessibility audit.

**Choice:** Mark E10-03 implemented for the specified workflow: failed-rule fields sort first, then low-confidence fields, and Enter/Arrow navigation moves focus between queue inputs. Keep WCAG certification, IME coverage, and full mouse-free operation across every control outside this story's evidence.

**Alternatives:** Claim keyboard completeness from DOM ordering alone; rejected because focus movement must be exercised in a browser. Claim accessibility certification from Playwright; rejected because the source requires a broader accessibility program than this focused interaction test.

**Consequences:** Reviewers can triage failed/low-confidence fields through the queue with keyboard movement, while the project status accurately distinguishes this workflow from E10-01/E10-02's image/drawing gaps.

**Validation:** Live Playwright coverage uploads a deterministic PDF, extracts a result with two failed fields, verifies both failed fields are first, and moves focus with ArrowDown. The full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass.

**Implementation/evidence:** [review queue](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-098: Close persisted review-state and correction audit acceptance

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E10-04, E10-06

**Context:** Review state events and correction rows were persisted separately, but the status overlay remained conservative because tests covered only an approval path and only partial CSV content.

**Choice:** Treat the existing append-only `review_events` contract as the E10-04 audit log for all four source states (`new`, `in_review`, `approved`, `rejected`). Treat the correction table plus `/corrections.csv` as the E10-06 exportable log containing original value, new value, authenticated actor, and timestamp. Keep state history and value corrections distinct.

**Alternatives:** Infer state history from the current extraction status; rejected because it loses prior transitions. Export only correction values; rejected because actor/time and original values are part of the source acceptance. Merge state events into correction rows; rejected because approval/rejection is not a field correction.

**Consequences:** Review and audit consumers can reconstruct both state transitions and value-level changes after reload. The current browser does not provide a full queue/assignment system, and drawing arbitrary boxes/native PDF previews remain separate partial stories.

**Validation:** The extraction contract test cycles through all four review states and asserts the terminal event actor; the correction CSV assertion verifies its header, changed value, actor, and timestamp column. The full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass.

**Implementation/evidence:** [review routes](../backend/app/main.py), [review models](../backend/app/models.py), [review tests](../backend/tests/test_extraction.py), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-097: Close the documented scan submission and result API

- **Date:** 2026-09-24
- **Status:** Implemented; local contract boundary
- **Scope:** E7-05

**Context:** The service already accepted bounded scan/digital uploads, persisted ingestion status and PageModel results, and persisted extraction results. The API reference listed individual routes but did not present the complete developer flow required by E7-05.

**Choice:** Document the four-step upload, status/PageModel, extraction, and result-read sequence and mark E7-05 implemented for that API contract. Keep OCR, complex layout, and production scan accuracy separate from API submission/result behavior.

**Alternatives:** Claim E7-05 only after OCR is complete; rejected because the source acceptance asks for upload, status, result endpoints and documentation, while OCR is separately specified by E8-04. Document only upload/status; rejected because developers also need the extraction trigger and persisted result read to complete the API flow.

**Consequences:** API consumers have a copy-pasteable local scan-to-result path with stable IDs and documented result fields. The endpoint does not imply that a scan has been OCR-processed or that extraction accuracy is production-calibrated.

**Validation:** Ingestion tests cover upload, route, status, PageModel/Markdown result, and limits; extraction tests cover persisted extraction and result retrieval; the generated OpenAPI action matrix includes the routes. The full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass.

**Implementation/evidence:** [API reference](api-reference.md), [ingestion contract](ingestion-contract.md), [extraction contract](extraction-contract.md), [ingestion tests](../backend/tests/test_ingestion.py), [extraction tests](../backend/tests/test_extraction.py), [status](../frontend/src/storyStatus.ts).

## DD-096: Close bounded extraction export and webhook delivery

- **Date:** 2026-09-24
- **Status:** Implemented; bounded delivery contract
- **Scope:** E9-08

**Context:** The platform exposed JSON, CSV, and dependency-free XLSX result exports plus an explicitly allow-listed webhook route, but status remained partial because earlier decisions deferred retries, delivery history, and spreadsheet-reader compatibility.

**Choice:** Mark E9-08 implemented for the source acceptance: each export and webhook payload carries field values with confidence and review status. Keep the webhook synchronous, bounded, allow-listed, optionally signed, and non-retrying; treat retries/history and reader-specific compatibility as later operational evidence rather than hidden requirements for this story.

**Alternatives:** Claim completion from route presence alone; rejected because metadata coverage must be asserted in payloads. Add durable webhook retries now; deferred because it changes delivery semantics and belongs to operations work. Claim universal spreadsheet compatibility; rejected because the current evidence verifies a valid OOXML package, not every spreadsheet reader.

**Consequences:** Integrators can choose JSON, CSV, or XLSX and can explicitly deliver the same result to an allow-listed endpoint without external services by default. Failed delivery is reported to the caller and is not silently retried or treated as approval.

**Validation:** Extraction tests assert JSON confidence/review metadata, CSV headers, and XLSX content type; webhook tests assert the delivered JSON contains confidence/review metadata and the signature/allow-list boundary. The full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass.

**Implementation/evidence:** [export routes](../backend/app/main.py), [XLSX writer](../backend/app/exports.py), [export tests](../backend/tests/test_extraction.py), [webhook tests](../backend/tests/test_epic34.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-095: Treat the offline extraction engine contract as complete for E9-03

- **Date:** 2026-09-24
- **Status:** Implemented; bounded acceptance
- **Scope:** E9-03; E8-08 remains partial

**Context:** The source story requires a pluggable extractor contract, a bundled local option that makes no external calls, and optional provider/plugin paths. The repository has a versioned engine registry, local deterministic implementation, entry-point discovery, worker selection, and explicit unavailable-engine errors, but Docling, PaddleOCR, and a third engine are not installed or validated.

**Choice:** Mark E9-03 implemented for the documented contract and offline local option. Keep external engine execution, provider licence review, and the three-engine requirement of E8-08 separate and partial.

**Alternatives:** Claim E9-03 only after installing external engines; rejected because the source explicitly makes those plug-ins optional and local extraction is the required default. Claim E8-08 from descriptors alone; rejected because it requires three engines to run behind the same contract.

**Consequences:** Developers can select the local extractor or register a versioned entry-point plugin without changing result shape, and unavailable engines fail explicitly. No third-party engine capability, OCR quality, or licence compliance is implied.

**Validation:** Engine contract tests cover local availability, descriptor reporting, plugin selection/error behavior and worker integration; the full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass.

**Implementation/evidence:** [engine registry](../backend/app/engines.py), [worker selector](../backend/app/worker_child.py), [engine tests](../backend/tests/test_engines.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-094: Close schema validation failure reporting for E9-05

- **Date:** 2026-09-24
- **Status:** Implemented; bounded rule set
- **Scope:** E9-05

**Context:** The local extractor supports required/type checks plus configured ranges, patterns, Luhn checksums, and scalar-versus-table totals. Its status had remained partial because the decision record correctly avoided claiming general financial validation, even though the source acceptance only requires failed rules to flag the field for review.

**Choice:** Mark E9-05 implemented for the documented rule set. Preserve each finding in the field result, lower heuristic confidence, and set the result to `needs_review`; do not coerce invalid values.

**Alternatives:** Mark the story partial until all financial and checksum standards are supported; rejected because that exceeds the source acceptance and would conflate bounded validation with domain certification. Hide failed rules behind a UI-only indicator; rejected because API, export, worker and review consumers need the same result contract.

**Consequences:** Range, checksum, pattern, required/type, and total failures are machine-readable and review-triggering. Luhn is the only checksum, totals use explicit configured columns/tolerance, and confidence calibration remains E9-04 work.

**Validation:** `test_validation_rules_report_range_checksum_and_total_failures` passes; the full backend suite passes (`99 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and diff checks pass. No financial certification or held-out calibration claim is made.

**Implementation/evidence:** [validation implementation](../backend/app/extraction.py), [extraction tests](../backend/tests/test_extraction.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-093: Close bounded multi-file intake with per-file state

- **Date:** 2026-09-24
- **Status:** Implemented; bounded acceptance
- **Scope:** E8-01

**Context:** The upload endpoint accepts the supported PDF/image types one request at a time, and the browser already submits each selected file independently. The remaining evidence gap was that a multi-file selection and independent result states were not covered by a live browser test.

**Choice:** Keep the native multi-file control and sequential per-file API submissions. Replace each temporary uploading row with the server-assigned ID, route, and queued status, while retaining independent failures and errors per file. Treat the source story as implemented for multi-file upload/status; keep OCR, layout, and processing progress in their separate partial stories.

**Alternatives:** Upload all files as one multipart server request; rejected because it would obscure per-file failures and change the existing API contract. Mark E8-01 complete from a single-file API test; rejected because the source acceptance explicitly requires multi-file status behavior.

**Consequences:** Operators can select PDF, PNG, JPEG, or TIFF files together and see each file's server status and routing independently. Upload status is not extraction/OCR completion, and the current UI does not claim page processing progress.

**Validation:** The live Playwright ingestion test selects a digital PDF and PNG together and verifies distinct queued rows with digital and scan routing; the full backend suite, frontend build, Python compilation, and diff checks pass. E8-02 and E8-05 remain partial for OCR routing and processing progress.

**Implementation/evidence:** [upload UI](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [ingestion contract](ingestion-contract.md), [status](../frontend/src/storyStatus.ts).

## DD-092: Separate durable restart recovery from resource enforcement

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E12-01; E12-02 remains partial

**Context:** PostgreSQL-backed jobs, leases, and the application-lifespan supervisor are exercised by a test that queues work, closes the application, starts it again, and observes completion. Earlier documentation grouped E12-01 with E12-02 because the same isolated runner also has incomplete platform-specific resource-limit evidence.

**Choice:** Mark E12-01 implemented on the basis of the restart-resumption acceptance evidence. Keep E12-02 partial until runaway-job termination is verified across supported platforms and deployment boundaries. Keep E12-03 partial because the current pools are daemon threads in one application process and have no throughput/load-test evidence.

**Alternatives:** Keep E12-01 partial until E12-02 is complete; rejected because the source acceptance criteria are independently testable. Mark all operational stories implemented from the existence of a queue; rejected because restart, resource enforcement, and scaling have distinct evidence requirements.

**Consequences:** The project status distinguishes proven durable recovery from unproven resource and scale guarantees. Queued jobs survive application recreation and are claimed by the configured supervisor without client replay; no cgroup, Windows-limit, horizontal-throughput, retry/DLQ, or production worker claim is made.

**Validation:** `test_enabled_supervisor_resumes_queued_job_after_application_restart` passes in the backend suite; the Compose supervisor is enabled by default and live readiness remains healthy. Full suite, frontend build, Python compilation, and diff checks are rerun with the next validation batch.

**Implementation/evidence:** [job supervisor](../backend/app/main.py), [durable job helpers](../backend/app/jobs.py), [restart test](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-091: Complete the approved extraction-to-template handoff

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E5-08, E10-05

**Context:** The render-approved API already refused unapproved extraction results and built top-level data from normalized field names, but the contract lacked an integration test. The browser action rendered an artifact in the review card without opening the destination template or replacing its sample data.

**Choice:** Preserve the approval gate and exact field-name mapping. Return the bound data alongside the artifact. After a successful one-click action, open the first listed template in the editor, replace its sample data with the returned approved data, and show the server-rendered artifact in the editor preview. Keep template choice explicit in the documentation as the current first-template operational default.

**Alternatives:** Allow any extraction state to render; rejected because approval is the closed-loop safety boundary. Put the data only in the review card; rejected because the source story requires the template to open with bound data and a preview. Add a template picker in this slice; deferred because it changes the one-click flow and is not required to prove field binding.

**Consequences:** Approved normalized values are visible in the opened template editor and its server preview, while rejected or unapproved results remain blocked. The first listed template is deterministic but not yet user-selectable.

**Validation:** The extraction integration test covers unapproved rejection, approved named-field binding, rendered output, and rejection after status changes. The full backend suite passes (`99 passed, 5 skipped, 3 warnings`); the frontend build, Python compilation, and `git diff --check` pass.

**Implementation/evidence:** [render route](../backend/app/main.py), [closed-loop test](../backend/tests/test_extraction.py), [review UI](../frontend/src/main.tsx), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-090: Route large template renders to durable jobs

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E7-04

**Context:** The platform had a synchronous isolated render endpoint and a durable job API, but the source story requires small documents to render synchronously and larger documents to use async status polling. The boundary was previously an explicit caller choice rather than a documented server policy.

**Choice:** Add the typed `sync_render_max_blocks` setting, defaulting to 100. The template render endpoint remains synchronous at or below the threshold; larger definitions, or requests with `async: true`, enqueue a render job and return HTTP 202 with a polling URL. Job state remains queued/running/done/failed in PostgreSQL, and execution uses the same isolated child runner.

**Alternatives:** Queue every render; rejected because the source explicitly requires small synchronous renders. Keep only a caller-provided `sync` flag; rejected because it permits large work to bypass the durable path. Use output byte size as the only threshold; rejected because the definition block count is available before execution and is a deterministic bounded routing signal.

**Consequences:** API clients have a predictable small/large routing contract and can poll durable jobs. The threshold is an operational default, not a performance benchmark; memory/CPU enforcement and independently scalable workers remain E12 partial concerns.

**Validation:** Queue tests cover synchronous small templates, threshold-triggered large templates, queued polling and isolated completion; the full backend suite passes (`98 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` pass. No throughput claim is made.

**Implementation/evidence:** [render route](../backend/app/main.py), [settings](../backend/app/config.py), [jobs tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [configuration reference](e1-foundation.md), [status](../frontend/src/storyStatus.ts).

## DD-089: Evidence scoped API-key rotation

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E7-02

**Context:** API keys were generated as hashed secrets and scope checks covered read/render operations, but the automated evidence did not exercise all three scope labels and an explicit revoke-and-reissue rotation sequence.

**Choice:** Keep keys bearer secrets returned only at creation, store only SHA-256 digests, enforce `read`, `render`, and `admin` scope boundaries at the API, and define rotation as revoking the old key followed by issuing a replacement. Keep key administration behind an authenticated session and CSRF boundary.

**Alternatives:** Allow API keys to manage other keys; rejected because a browser session is the current administrative boundary. Mutate a key's secret in place; rejected because revocation and re-issuance make the old credential unambiguously invalid. Treat an unscoped key as admin; rejected because scope omission must not widen authority.

**Consequences:** Integrations can use least-privilege keys and rotate credentials without exposing stored secrets. Full role/folder authorization and a login UI remain outside this Must story.

**Validation:** Authentication tests pass (`5 passed, 3 warnings`) covering all three scopes, read/render denial, hashed one-time display, revocation, and replacement-key rotation; the full backend suite passes (`97 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` pass. Live readiness is checked after deployment.

**Implementation/evidence:** [auth routes](../backend/app/main.py), [key primitives](../backend/app/auth.py), [scope tests](../backend/tests/test_auth.py), [auth contract](auth-contract.md), [status](../frontend/src/storyStatus.ts).

## DD-088: Close the generated OpenAPI explorer story

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E7-03

**Context:** FastAPI already served an interactive explorer and generated OpenAPI JSON, and the repository had route-presence tests, but the project status still treated E7-03 as partial because the evidence was not explicitly tied to the source acceptance criterion.

**Choice:** Treat the framework-generated `/docs` explorer and `/openapi.json` document as the API authority, and maintain an explicit browser-action matrix test against that generated document. Document the explorer URL and the matrix's limits in the API reference.

**Alternatives:** Maintain a separate hand-written OpenAPI document; rejected because it would drift from route code. Claim full SDK/client compatibility from explorer availability; rejected because the story only requires the built-in explorer and generated spec, while behavior and SDK coverage remain separate.

**Consequences:** Developers can inspect and try the current API through the built-in explorer, and route drift for current UI actions fails tests. E7-01 and E7-04 remain separate partial stories for broader API behavior and job routing.

**Validation:** OpenAPI explorer/spec and action-matrix tests pass within the full backend suite (`96 passed, 5 skipped, 3 warnings`); frontend build, compilation, `git diff --check`, and live readiness pass. No SDK or production compatibility claim is made.

**Implementation/evidence:** [API reference](api-reference.md), [OpenAPI tests](../backend/tests/test_epic34.py), [generated routes](../backend/app/main.py), [story status](../frontend/src/storyStatus.ts).

## DD-087: Keep the licence scan fail-closed with post-failure evidence

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E11-05

**Context:** The source story requires CI to scan against the literal MIT/Apache-2.0/OFL allow-list, fail on a disallowed licence, and publish an SBOM. The checked-in dependency inventory contains known findings, and DD-013's policy conflict remains unresolved.

**Choice:** Keep `check_licenses.py` strict: unknown, compound, or outside-allow-list metadata creates a finding and a nonzero exit, while SBOM and JSON findings are written before exit. Configure the workflow artifact upload with `if: always()` so a red scan still publishes its evidence. Do not normalize current findings into compliance.

**Alternatives:** Make the workflow informational; rejected because it would violate the source gate. Upload only on success; rejected because it hides the evidence needed to resolve findings. Add blanket exceptions for PostgreSQL, BSD, MPL or compound metadata; rejected because the project owner has not accepted those policy changes.

**Consequences:** Disallowed dependency metadata blocks CI and remains inspectable in artifacts. The current repository is expected to fail the strict scan until the allow-list decision and component review are resolved; this story implementation is not a licence-compliance approval.

**Validation:** Synthetic disallowed-metadata and workflow contract tests pass; the real inventory scan reports 154 components and 45 findings, writes both artifacts, and exits 1 as required. The full backend suite passes (`96 passed, 5 skipped, 3 warnings`), the frontend build passes with 47 transformed modules, Python compilation and `git diff --check` pass. No licence-compliance approval is claimed.

**Implementation/evidence:** [scanner](../scripts/check_licenses.py), [workflow](../.github/workflows/license-scan.yml), [tests](../backend/tests/test_license_scan.py), [workflow test](../backend/tests/test_license_workflow.py), [inventory](dependency-inventory.json), [status](../frontend/src/storyStatus.ts).

## DD-086: Close the documented TLS deployment story

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E11-03

**Context:** E11-03's source acceptance criterion requires a reference proxy setup in the install guide. The repository had Caddy and Nginx examples, secure-cookie configuration and README linkage, but the documentation was not protected by a regression test and the status remained partial because no live certificate service was available.

**Choice:** Treat the documented reverse-proxy contract as the story boundary: Caddy and Nginx examples forward to the private application endpoint, operators enable `secure_cookies` for HTTPS, and the guide states the limits of the reference. Add a content contract test so the examples and secure-cookie instruction cannot silently disappear.

**Alternatives:** Claim production TLS from snippets alone; rejected because certificates, renewal, HSTS and proxy hardening require deployment evidence. Terminate TLS in the application container; rejected because it expands key lifecycle and container responsibilities.

**Consequences:** The source Must story is implemented as documented, reproducible deployment guidance. Live certificate issuance, domain ownership, renewal testing and security certification remain operator/deployment concerns and are not claimed.

**Validation:** TLS documentation/auth focused tests pass (`5 passed, 3 warnings`), the full backend suite passes (`95 passed, 5 skipped, 3 warnings`), the frontend build passes with 47 transformed modules, and the live Compose service remains ready. No live TLS endpoint was started.

**Implementation/evidence:** [TLS guide](tls.md), [documentation test](../backend/tests/test_tls_docs.py), [settings](../backend/app/config.py), [cookie handling](../backend/app/main.py), [story status](../frontend/src/storyStatus.ts).

## DD-085: Evidence the local authentication lockout contract

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E11-02

**Context:** Local setup, PBKDF2 password storage, sessions, CSRF checks, API-key scopes and secure-cookie configuration were implemented, but the automated suite did not explicitly exercise the configured failed-login threshold.

**Choice:** Add a regression test that creates the first account, submits five invalid passwords, and verifies that a valid password is rejected with HTTP 429 while the lockout window is active. Document the complete tested control set and the selected PBKDF2 parameters without presenting them as a universal deployment recommendation.

**Alternatives:** Test only that a valid login succeeds; rejected because it misses brute-force protection. Use a real-time 15-minute sleep; rejected because it makes the suite slow and nondeterministic. Lower the production threshold for the test; rejected because the test must exercise the configured default.

**Consequences:** E11-02's source acceptance criterion now has direct automated evidence for the rate-limit control in addition to session, CSRF and storage tests. Fine-grained user roles are E11-01 (Should), and independent security review remains outside this story.

**Validation:** The focused authentication suite passes (`4 passed, 3 warnings`), including lockout after five failures; the full backend suite passes (`94 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` pass. No penetration-test or algorithm-certification claim is made.

**Implementation/evidence:** [auth tests](../backend/tests/test_auth.py), [auth primitives](../backend/app/auth.py), [auth contract](auth-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-084: Close the declarative expression-sandbox contract

- **Date:** 2026-09-24
- **Status:** Implemented
- **Scope:** E5-06

**Context:** The template evaluator used a whitelist path/formatter grammar and bounded loop/depth budgets, but the hostile-expression coverage did not exercise attribute-like dunder paths, function calls, operators, imports, or HTML/script-shaped data together.

**Choice:** Reject any path containing dunder segments in addition to the existing path grammar, and add a hostile-expression matrix covering imports, calls, operators and dunder access. Verify that untrusted data is escaped as output and cannot turn into executable HTML. Keep network denial and process-resource isolation in the separate E11-04/E12-02 worker contract.

**Alternatives:** Use Python `eval` with a restricted globals dictionary; rejected because the source requirement is no code execution and the grammar does not need evaluation. Treat dunder paths as ordinary missing fields; rejected because explicit rejection makes the boundary auditable and prevents future object-backed data changes from widening access. Claim OS-level sandboxing from this evaluator test; rejected because that belongs to worker containment.

**Consequences:** E5 template expressions are demonstrably data-only, bounded and escaped. The evaluator still does not provide arbitrary aggregation or remote data access, and this decision does not close the separate document-parser sandbox story.

**Validation:** The focused template suite passes (`17 passed, 1 warning`); the full backend suite passes (`93 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` pass. No E11-04 or final-output claim is made.

**Implementation/evidence:** [evaluator](../backend/app/template_logic.py), [security tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-083: Minimize the isolated worker environment and socket surface

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E11-04, E12-02 worker containment

**Context:** The document child process already removed several known database/cloud secrets and blocked TCP connect calls, but inherited environment variables and higher-level socket helpers were broader than necessary for untrusted rendering and extraction.

**Choice:** Start child workers with an allow-listed environment containing only process-launch, temporary-directory, locale and output-encoding variables. Also deny `socket.create_connection`, UDP `sendto`, and `sendmsg` in addition to socket connect methods. Keep the existing subprocess wall-time, output, CPU and address-space limits.

**Alternatives:** Continue removing a growing blacklist of credential names; rejected because new secrets or import overrides could be inherited. Remove all environment variables; rejected because platform process launch and temporary-file behavior need a minimal portable set. Rely on container networking alone; rejected because the child boundary must remain defensive when run outside the reference Compose network.

**Consequences:** Child workers cannot receive configured credentials or `PYTHONPATH` import overrides through the inherited environment, and common TCP/UDP socket entry points fail closed. Filesystem isolation, Windows resource-limit parity, hostile parser coverage and a production sandbox remain incomplete; E11-04/E12-02 remain partial.

**Validation:** The focused worker/security suite passes (`8 passed, 3 warnings`), including the environment-boundary regression; the full backend suite passes (`92 passed, 5 skipped, 3 warnings`); Python compilation and `git diff --check` pass. No claim of complete malicious-file containment is made.

**Implementation/evidence:** [worker supervisor](../backend/app/worker.py), [worker child](../backend/app/worker_child.py), [worker tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md).

## DD-082: Derive project-status progress from story evidence

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E14-04 status UI, cross-epic status visibility

**Context:** The status page listed each story's evidence-backed label, but epic progress and state were hard-coded from the initial foundation snapshot and had become stale as stories were implemented.

**Choice:** Derive each epic's completion from the current story status map: implemented counts as 1, partial as 0.5, and planned as 0. Epic progress is the weighted average of its catalogued stories, and the epic state is planned, in progress, or verified from those same labels. Keep all source stories visible, including Should and Could items, while preserving the source priority labels.

**Alternatives:** Maintain manually edited epic summaries; rejected because they drift from story evidence. Count partial stories as complete; rejected because it overstates acceptance. Hide non-Must stories; rejected because the requested project status page covers every source user story.

**Consequences:** The project status page now updates automatically when evidence-backed story labels change and cannot report an old zero-progress epic after implementation work. A partial story still contributes only half credit and no story is marked implemented without an explicit status-map entry.

**Validation:** Frontend production build passed with 47 transformed modules, and the live Playwright suite passed 10 tests including the project-status flow against `http://127.0.0.1:8001`. The rebuilt Compose service returned ready with database, storage and frontend dependencies ready. This improves status fidelity but does not change any story's acceptance status.

**Implementation/evidence:** [status derivation](../frontend/src/main.tsx), [story evidence map](../frontend/src/storyStatus.ts), [source catalogue](../frontend/src/epicStories.ts).

## DD-081: Generate the script matrix page from the deterministic CI report

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E14-03, with E4-08 as the enabling contract

**Context:** The script-matrix workflow produced a deterministic JSON artifact, while `docs/script-test-matrix.md` could drift if maintained manually. The project needs a visible status page without implying native rendering or reader approval.

**Choice:** Generate the Markdown page from `scripts/render_spike.py` output with a deterministic Python script. CI rebuilds the page, compares it with the checked-in documentation, and uploads both the JSON report and generated page. The page keeps explicit native-review and PDF-engine caveats.

**Alternatives:** Manually maintain the page; rejected because it permits report/document drift. Publish only raw JSON; rejected because it is less discoverable for project status review. Have CI commit generated changes; deferred because this workflow should remain a validation gate rather than mutate the branch.

**Consequences:** Script-family coverage is visible and drift is detected in CI. The page reports only deterministic contract evidence; it does not claim visual fidelity, shaping correctness, native-reader approval, or final PDF-engine selection.

**Validation:** Local report generation and page comparison pass, workflow YAML parses, and `git diff --check` passes. Hosted CI, native visual baselines, and native-reader review were not run; E14-03 remains partial.

**Implementation/evidence:** [page generator](../scripts/build_script_matrix_page.py), [workflow](../.github/workflows/script-matrix.yml), [script matrix](script-test-matrix.md), [story status](../frontend/src/storyStatus.ts).

## Recording rules

Use sequential IDs. Status is **Proposed**, **Accepted**, **Implemented**, **Rejected**, or **Superseded**. Accepted means adopted for the work, not tested or shipped. Record who or what establishes acceptance; never infer product approval from the existence of this file. A proposal can be explored without calling it final. Every implemented entry needs file references and actual validation results. Preserve previous reasoning and link replacement entries when superseding decisions.

For consequential decisions, record date, story IDs, context, choice, alternatives, consequences, validation, and implementation/evidence. Small reversible choices can share a dated batch entry if each choice and rationale is explicit. Mechanical edits can reference the existing decision. This register documents choices; it does not grant deployment, publishing or licensing authority.

## Current decisions

## DD-070: Maintain a generated-OpenAPI matrix for browser actions

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E7-01 and E7-03

**Context:** The workspace had REST calls for templates, drafts, preview, ingestion, extraction, review, and approved generation, but route drift could leave a UI action without an API equivalent.

**Choice:** Document the implemented browser-action-to-route mapping and assert its methods against FastAPI's generated OpenAPI document. Keep the generated specification as the authority rather than maintaining a second hand-written API schema.

**Alternatives:** Test only `/docs` reachability; rejected because it would not detect missing action routes. Maintain a manually copied OpenAPI file; rejected because it would drift. Treat every future UI affordance as covered automatically; rejected because the matrix is deliberately explicit and must be extended with new actions.

**Consequences:** Route drift for the current workspace action set fails the contract test and the API reference makes the current boundary discoverable. E7-01 remains partial because final PDF actions, webhooks, SDKs, and broader endpoint behavior are not complete.

**Validation:** The focused API suite passes (`5 passed, 3 warnings`), the full backend suite passes (`87 passed, 5 skipped, 6 warnings`), the frontend build passes (`47 modules`), Python compilation and `git diff --check` pass, and the existing live service remains healthy. No SDK or production API compatibility claim is made.

**Implementation/evidence:** [API matrix](api-reference.md), [OpenAPI test](../backend/tests/test_epic34.py), [API routes](../backend/app/main.py), [story status](../frontend/src/storyStatus.ts).

## DD-069: Verify direct multilingual editor entry with native text controls

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-09

**Context:** The editor uses browser text controls rather than a canvas text bitmap, but no browser regression covered direct entry of the backlog's non-Latin script families.

**Choice:** Add a Playwright flow that fills one editor text block with Arabic, Devanagari, Thai, Chinese, and Japanese, verifies the DOM value, saves the draft, and verifies the same UTF-8 text in the server preview. Keep native IME composition, caret/selection behavior, shaping, and reader approval outside this contract.

**Alternatives:** Claim script support from the renderer's script labels; rejected because that does not test editing. Add synthetic keyboard events only; rejected because filling the native control provides a stronger persistence/render regression while remaining deterministic. Claim full localization acceptance; rejected because IME and native-reader evidence are absent.

**Consequences:** Direct multilingual text survives the editor-to-draft-to-preview path. E2-09 remains partial pending real IME/caret/selection testing across target platforms and final output shaping evidence.

**Validation:** `npm run build` passes (`47 modules`), and all nine live Playwright tests pass against the rebuilt healthy service, including the multilingual direct-entry flow. Python compilation and `git diff --check` remain clean; no accessibility, IME-composition, caret/selection, or native-reader certification is claimed.

**Implementation/evidence:** [editor](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-068: Expose font diagnostics before selecting a PDF engine

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E4-06 and E6-05

**Context:** Candidate render responses reported script names and fallback stacks, but downstream output and review flows had no explicit per-script diagnostic structure for embedded fonts or missing glyphs.

**Choice:** Add a bounded `font_report` to every candidate render result. It records each detected script, requested fallback stack, embedded font list, missing-glyph list, and `candidate` status. The current HTML renderer reports empty embedding because no font bundle or PDF engine has been selected.

**Alternatives:** Claim the CSS Noto stack as embedded fonts; rejected because a CSS family name is not an embedded-font measurement. Add a font package now; deferred until E4-01 engine comparison and licence review establish the actual bundle. Omit diagnostics until PDF generation; rejected because the contract is needed by the editor/API before engine selection.

**Consequences:** Consumers have a stable diagnostics shape and cannot confuse fallback declarations with embedded coverage. E4-06 and E6-05 remain partial pending custom/bundled font handling, glyph measurement, final PDF output, and reader evidence.

**Validation:** The focused renderer suite covers Arabic/CJK report entries and candidate embedding status; the full backend suite passes (`86 passed, 5 skipped, 6 warnings`), the frontend build passes (`47 modules`), and Python compilation/diff checks pass. The rebuilt Docker service is healthy with readiness dependencies ready; a live candidate render returned `font_report` with the requested stack, empty embedding list, empty missing-glyph list, and `candidate` status. No bundled-font or PDF embedding claim is made.

**Implementation/evidence:** [renderer](../backend/app/rendering.py), [font contract](template-contract.md), [tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

## DD-067: Gate the deterministic script matrix in CI

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E4-08 and the E4-01 rendering evidence gate

**Context:** The repository had an offline script report, but changes to the renderer were not automatically checked against its supported script families.

**Choice:** Add a GitHub Actions contract job that installs the pinned runtime lock, runs `scripts/render_spike.py`, asserts the seven currently covered script families and no reported missing glyphs, and uploads the JSON report. Keep the report status `pending-native-review` and avoid presenting this as visual regression or native-reader evidence.

**Alternatives:** Add screenshot baselines now; rejected because no PDF engine, font bundle, or native-reviewed baseline has been selected. Run only the local script; rejected because regressions would not be gated in CI. Claim zero missing glyphs as font proof; rejected because the current renderer reports contract diagnostics, not actual font coverage.

**Consequences:** The deterministic contract is reproducible in CI and its artifact is inspectable. E4-08 remains partial until visual baselines, exact environment manifests, native-reader review, and a selected renderer exist.

**Validation:** The local report passes with all seven contract families and `missing_glyphs: []`; the workflow syntax and hosted-run result remain to be verified by CI.

**Implementation/evidence:** [workflow](../.github/workflows/script-matrix.yml), [spike](../scripts/render_spike.py), [matrix](script-test-matrix.md), [renderer](../backend/app/rendering.py), [story status](../frontend/src/storyStatus.ts).

## DD-066: Generate QR and barcode blocks locally as SVG

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-04

**Context:** E2-04 requires QR, Code 128, and EAN output bound to fields. The current renderer had no machine-readable code blocks, and handcrafted encoders would add unnecessary correctness risk.

**Choice:** Add pinned `qrcode` and `python-barcode` runtime dependencies and generate SVG in the isolated renderer for QR, Code 128, and EAN-13 blocks. Accept fixed values or bounded data-path bindings, validate EAN digit shape, escape the accessible label, and expose the same controls in the editor.

**Alternatives:** Emit a visual placeholder; rejected because it would not be scannable. Handwrite all symbology encoders; rejected because standards correctness would be difficult to establish within the current slice. Fetch remote barcode images; rejected because it violates offline/no-egress defaults.

**Consequences:** Code blocks are deterministic and do not need raster or network services. Dependency metadata is recorded but remains subject to the unresolved literal MIT/Apache-2.0/OFL allow-list decision. Native-reader/scanner tests and final PDF embedding are still pending, so E2-04 is partial.

**Validation:** Renderer tests cover all three SVG types and invalid EAN input. The full backend suite passes (`85 passed, 5 skipped, 6 warnings`), the frontend build passes (`47 modules`), Python compilation and `git diff --check` pass, and the metadata-only licence scan reports `154` components with `45` existing/unresolved findings (including qrcode's declared BSD metadata); no compliance claim is made. The rebuilt Docker image imports both generators, reports readiness for database/storage/frontend, and a live template render returned candidate HTML containing three SVGs for QR, Code 128, and EAN-13.

**Implementation/evidence:** [code generators](../backend/app/codes.py), [renderer](../backend/app/rendering.py), [editor](../frontend/src/main.tsx), [dependency lock](../backend/requirements.lock), [tests](../backend/tests/test_template_logic.py), [contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-065: Keep image rendering bounded and offline by default

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-03

**Context:** The editor and renderer supported text and tables but had no declarative image/logo block. Image sources are untrusted inputs, and unrestricted remote fetching would violate the offline and SSRF constraints.

**Choice:** Add an `image` block with bounded dimensions, escaped alt text, base64 image data URI support, and optional binding from a data path. Reject HTTP(S) sources unless the template explicitly opts into `allow_external_sources`; even then, the renderer emits the URL without fetching it. Add the corresponding editor controls and persist the safe block definition.

**Alternatives:** Fetch every URL during rendering; rejected because it creates SSRF and data-egress risk. Accept arbitrary HTML; rejected because it bypasses the declarative template safety contract. Add an image package immediately; deferred because standard-library validation is sufficient for source and markup safety while asset storage and final PDF embedding remain unresolved.

**Consequences:** Fixed and bound base64 images can be previewed and rendered through the current HTML candidate. Upload-backed asset references, an external URL allow-list, image decoding/virus policy, and final PDF-reader evidence remain pending; E2-03 is not complete.

**Validation:** Two renderer tests cover a bound base64 PNG and default external-source rejection. The full backend suite passes (`83 passed, 5 skipped, 6 warnings`), the frontend build passes (`47 modules`), Python compilation and `git diff --check` pass, and the rebuilt Docker service is healthy with all readiness dependencies ready on `127.0.0.1:8001`. A live template-create/render smoke test returned HTML containing the image class and escaped alt text.

**Implementation/evidence:** [renderer](../backend/app/rendering.py), [editor](../frontend/src/main.tsx), [template contract](template-contract.md), [tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

## DD-064: Provide dependency-free XLSX extraction exports

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-08

**Context:** Extraction results already had JSON and CSV endpoints, but the `Must` story also names spreadsheet export. Adding a spreadsheet library would expand the dependency and licence surface before the unresolved allow-list decision is settled.

**Choice:** Emit a minimal OOXML workbook with inline string cells using Python's standard library. Export the same field-level original value, normalized value, confidence, review status, source page/box, validation findings and result status as the JSON/CSV views. Keep values as strings so provenance and locale-shaped originals are not silently coerced by the writer.

**Alternatives:** Add an XLSX package; this would offer richer formatting but introduce an additional dependency and licence review. Export CSV with an `.xlsx` name; rejected because spreadsheet applications would not receive a valid workbook. Add webhook delivery in the same change; deferred because outbound network destinations require an explicit SSRF-resistant allow-list and delivery contract.

**Consequences:** Consumers can download a valid offline workbook without a new runtime dependency. E9-08 remains partial: webhook delivery, line-item-specific tabular shaping, and measured export compatibility across spreadsheet readers are not claimed.

**Validation:** The workbook contract test verifies the OOXML package, worksheet, provenance headers, Unicode original values and review status; the OpenAPI contract includes the new route. The focused backend suite passes (`15 passed, 3 warnings`), the full non-integration suite passes (`81 passed, 5 skipped, 6 warnings`), the frontend build passes (`47 modules`), and the rebuilt Docker service is running/healthy on `127.0.0.1:8001` with all readiness dependencies ready. A live upload → local extraction → `/export.xlsx` smoke test returned HTTP 200, the OOXML content type, a 1,905-byte payload, and the `PK` ZIP signature.

**Implementation/evidence:** [export writer](../backend/app/exports.py), [API route](../backend/app/main.py), [tests](../backend/tests/test_epic34.py), [story status](../frontend/src/storyStatus.ts), [source story](epics.md#e9-schema-and-extraction).

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
| DD-029 | Bound declarative template evaluation | Implemented; partial acceptance |

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
- **Status:** Implemented; E1-06 remains partial
- **Scope:** E1-01 through E1-06
- **Acceptance basis:** User instruction, "Start with E1"; existing release boundaries in the backlog.

**Context:** E1 contains six MVP and six R2 stories. Rendering/OCR are downstream epics and have not passed their required spikes.

**Choice:** Implement the foundation in the proposed Python/React stack: PostgreSQL, configuration, storage adapters, migration/bootstrap, health/readiness and a read-only sample workspace. Preserve R2 stories as scheduled. Mark E1-06 partial until actual E4/E8 rendering/extraction engines work on CPU; no placeholder worker is presented as a functional engine.

**Alternatives:** Implementing all later deployment capabilities now conflicts with the source sequencing. Claiming CPU rendering/OCR from a CPU-only API container would misstate acceptance.

**Consequences:** E1 can make concrete progress before the E4 spike, but cannot honestly be marked entirely complete yet. The foundation is local-only and has no E11 authentication layer.

**Validation:** Rebuilt Compose startup completed migrations and served the UI/API on `127.0.0.1:8001`; live health and sample API checks returned 200. The frontend build and two Playwright tests passed. Configuration, shared local/Moto-S3, and disposable-PostgreSQL migration suites passed. E1-06 remains partial pending actual downstream rendering/OCR evidence.

**Implementation/evidence:** [Compose](../compose.yaml), [backend](../backend/app/main.py), [workspace](../frontend/src/main.tsx), [tests](../backend/tests/test_foundation.py). Runtime installation remains gated by DD-022.

## DD-017: Use TOML plus explicit environment overrides and sanitized errors

- **Date:** 2026-09-22
- **Status:** Implemented; E1-05 is outside Must scope and E1-06 remains partial
- **Scope:** E1-02, E1-05

**Context:** One application config file and environment overrides must be predictable, with no secret-bearing inputs in logs.

**Choice:** Pydantic validation over standard-library TOML; defaults < config file < DOCPLATFORM_ environment values. Resolve relative local-storage paths against the config directory. Reject unknown settings and an explicitly missing file. Use SecretStr for credentials/endpoints, hide validation inputs, and return fixed operational error messages. Disable HTTP access logs, SQL parameter logs and debug configuration. Default object limit is 10 MiB for the foundation; later upload limits need their own story decision.

**Alternatives:** Implicit dotenv discovery and nested settings sources add ambiguous precedence; raw parser/driver error logging may expose passwords and endpoints.

**Consequences:** Operators get dependency status rather than raw exceptions. Compose explicitly owns container host, port, DB address and volume path; those overrides are documented. Future observability must add safe structured diagnostics, not re-enable raw errors.

**Validation:** Tests cover precedence, malformed TOML, invalid values, missing S3 bucket, typo detection and secret redaction, and passed in the backend suite. Liveness/readiness checks passed live; readiness checks schema head and storage read/write/delete, plus frontend build availability.

**Implementation/evidence:** [config.py](../backend/app/config.py), [configuration](../config.toml), [config tests](../backend/tests/test_config.py), [API](../backend/app/main.py).

## DD-018: Give local and S3 storage the same bounded object contract

- **Date:** 2026-09-22
- **Status:** Implemented; live-provider conformance remains environment-specific
- **Scope:** E1-03

**Context:** Templates, uploads and outputs need portable object storage without forcing a bundled object-store server.

**Choice:** Byte-oriented put/get/delete/check contract with namespaced keys, overwrite semantics, idempotent delete and a typed missing-object error. Local writes use same-directory temporary files, flush/fsync and atomic replacement. Reject traversal, symlinks/junctions and Windows aliases on all platforms. S3 uses boto3 with explicit timeouts/retries, an existing bucket, optional endpoint/credentials and a configurable prefix. No bucket creation at application startup.

**Alternatives:** Arbitrary user paths expose the host filesystem; storing binaries in PostgreSQL or bundling another storage service is unnecessary for this foundation.

**Consequences:** The local volume is private to the application; hostile concurrent modification by another host process is outside the adapter's trust boundary. Switching storage backends requires moving objects; it is not an automatic migration. Credential-provider-chain support is available when explicit S3 credentials are absent. Readiness probes incur a small S3 request cost and require put/get/delete permission.

**Validation:** One parameterized suite exercises both adapters with overwrite, deletion, missing objects, all three namespaces, multilingual bytes, empty values, oversized inputs and unsafe keys, and passed. S3 tests use Moto emulation; live provider conformance is a separate environment check.

**Implementation/evidence:** [storage.py](../backend/app/storage.py), [shared storage tests](../backend/tests/test_storage.py).

## DD-019: Run serialized Alembic migrations before serving requests

- **Date:** 2026-09-22
- **Status:** Implemented; historical release upgrade evidence remains out of scope
- **Scope:** E1-01, E1-04, E1-05

**Context:** Fresh startup and upgrades must initialize metadata safely, including concurrent launch attempts.

**Choice:** PostgreSQL 17, SQLAlchemy, Alembic and the pure-Python pg8000 driver. A one-shot Compose migration service waits for PostgreSQL readiness; the application waits for successful migration. Hold a PostgreSQL advisory lock around Alembic upgrade and check the expected head in readiness. Add an initial template table and a second schema-version migration so upgrade preservation is directly testable. Seed one fixed-ID template idempotently with object data written before metadata.

**Alternatives:** SQLAlchemy create_all does not test schema upgrades; every HTTP worker racing an unprotected migration is unsafe. pg8000 avoids the additional libpq/driver distribution surface for this modest foundation workload; benchmark before high-throughput adoption.

**Consequences:** A failed migration or storage probe prevents application startup. The fixture's schema is preliminary and does not establish E3 publish/version semantics. Two migration revisions are not two historical product releases, so E1-07 is not claimed.

**Validation:** Real PostgreSQL tests passed for fresh install, existing-row preservation from revision 0001, repeat upgrades, concurrent migrators, repeated seed and unmigrated readiness. Test DB reset is restricted to an explicitly named disposable database.

**Implementation/evidence:** [bootstrap](../backend/app/bootstrap.py), [migration runner](../backend/app/migrations.py), [revisions](../backend/migrations/versions/0002_template_schema.py), [integration tests](../backend/tests/test_foundation.py).

## DD-020: Serve the initial workspace and API from one origin

- **Date:** 2026-09-22
- **Status:** Implemented; UI is intentionally read-only for this foundation slice
- **Scope:** E1-01; enabling i18n structure for E14-04

**Context:** The first installation needs a useful UI with a persistent preloaded sample, not a fake rendering demo.

**Choice:** React/TypeScript/Vite with i18next; build static assets in a Node stage and serve them with FastAPI. Show the saved template, sample data and real dependency status. Use a warm neutral/green palette, responsive single-workspace layout, semantic headings/buttons, and a read-only detail view. Keep all interface messages in the translation resource. Sample text is document content, separate from UI messages. No CDN fonts, analytics or external UI runtime requests.

**Alternatives:** A separate production frontend server/proxy adds a service without a present requirement. Editing/render buttons without functioning backends would misrepresent delivery.

**Consequences:** No CORS configuration is needed. Developer Vite proxy is optional. Only English UI strings ship in this step; i18n foundations do not complete E14's later translated UI story. The API is read-only and unauthenticated, so Compose binds to host loopback only.

**Validation:** Typecheck/build plus browser tests for sample loading/navigation and narrow-screen overflow passed against the live Compose service; unavailable dependency states are covered at the API boundary. No accessibility certification is claimed.

**Implementation/evidence:** [React workspace](../frontend/src/main.tsx), [styles](../frontend/src/style.css), [translations](../frontend/src/i18n.ts), [browser tests](../frontend/tests/foundation.spec.ts), [Dockerfile](../Dockerfile).

## DD-021: Pin the foundation builds and keep CPU capability claims bounded

- **Date:** 2026-09-22
- **Status:** Implemented for the CPU-only foundation; E1-06 acceptance remains partial
- **Scope:** E1-01, E1-06

**Context:** Repeatable self-hosting requires reproducible application inputs, while the required rendering/OCR hardware baseline does not exist yet.

**Choice:** Pin direct and resolved Python dependencies, npm lockfile and Node/Python/PostgreSQL image manifest digests. Use Python 3.13 and Node 22 for this foundation; reevaluate Python against actual OCR wheels in E8. Run application as UID 10001, read-only root filesystem, private writable object volume and bounded temporary mount. Require no GPU/device passthrough. Do not add stub workers.

**Alternatives:** Floating latest image tags make future regression comparisons unreliable. Publishing an invented OCR minimum from API-only measurements would violate the benchmark plan.

**Consequences:** Pinning does not establish security or licensing compliance. The foundation may be tested on CPU now, but the full CPU rendering/extraction acceptance and measured minimum hardware guide remain pending. Later E11 sandboxing applies to actual untrusted document child processes, not this API container alone.

**Validation:** Pinned Compose build/start and live readiness passed on CPU-only container definitions. This does not prove E1-06's downstream rendering/OCR execution or measured minimum hardware guide.

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

## DD-059: Represent repeatable editor tables as bounded declarative blocks

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-02 and the shared E2/E4 template-render contract

**Context:** The editor and renderer supported text and generic loops, but there was no explicit table block that could guarantee row cardinality, escaped cell output, or print-header semantics.

**Choice:** Add a `table` block with an array `items` path and up to 50 typed columns (`header`, row-relative `path`, and an optional whitelisted format). Limit rows to the existing 1,000-item evaluation bound. Emit semantic table sections, repeatable print headers, and non-splitting rows in the HTML candidate renderer. Expose insertion and JSON column editing in the workspace editor, seeded with a small sample array.

**Alternatives:** Ask users to construct tables from raw loops; this cannot express header repetition as a first-class contract. Accept arbitrary HTML/CSS; this weakens escaping and template isolation. Select a PDF engine now; E4-01 native comparison remains pending.

**Consequences:** Row output follows the supplied data array and the same table contract is available to API-created drafts and the editor. Final PDF pagination, native-reader grading, and multi-page visual evidence remain unclaimed.

**Validation:** Seven focused template-render tests pass, including row count, ordering, escaping/formatting and `table-header-group`; the non-integration backend suite passes with `76 passed, 5 skipped, 6 warnings`. The frontend build passed (`47 modules`), the rebuilt Docker service is `running`/`healthy`, readiness returned 200, and four live Playwright tests passed, including table insertion and server-preview rows. No final PDF pagination or accessibility certification is claimed.

**Implementation/evidence:** [table renderer](../backend/app/rendering.py), [editor](../frontend/src/main.tsx), [table contract](template-contract.md), [render tests](../backend/tests/test_template_logic.py), [status overlay](../frontend/src/storyStatus.ts).

## DD-060: Expose bounded loops and conditions as visual editor blocks

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-05 and the shared E5 template-logic contract

**Context:** The server already evaluated bounded loops and conditions, but the editor only exposed text and table insertion. Owners could not add those constructs visually without editing JSON.

**Choice:** Add editor actions for repeating sections and conditional blocks. Repeating sections configure an array path and repeated text; conditional blocks configure a field path, enabled value, and true/false text. Save maps these controls to the existing declarative `loop` and `if` nodes, preserving the single bounded evaluator and sample data needed for preview.

**Alternatives:** Accept raw JSON-only logic; this fails the visual-editor acceptance. Add a new expression language for the UI; this duplicates and could diverge from the tested E5 grammar. Permit arbitrary callbacks; this violates the sandbox contract.

**Consequences:** E2-05 has an executable editor-to-server-render path for loops and if/else behavior. Nested visual composition, pagination, and full keyboard/accessibility acceptance remain incomplete.

**Validation:** The explicit loop/condition render test and existing bounded-expression tests pass; the non-integration backend suite passes with `77 passed, 5 skipped, 6 warnings`. The frontend build passed (`47 modules`), the rebuilt Docker service is healthy with readiness HTTP 200, and five live Playwright tests passed, including repeating-section rows and the enabled conditional branch. No accessibility or final-PDF certification is claimed.

**Implementation/evidence:** [editor](../frontend/src/main.tsx), [logic contract](template-contract.md), [evaluator](../backend/app/template_logic.py), [tests](../backend/tests/test_template_logic.py), [status overlay](../frontend/src/storyStatus.ts).

## DD-061: Keep page layout settings in the shared template definition

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-06 and the E4/E6 candidate-render contract

**Context:** The editor had a page margin in the sample definition, but no owner controls or renderer contract for size, orientation, headers, footers, or page numbers.

**Choice:** Store page settings in the versioned definition using allow-listed sizes (`A3`, `A4`, `A5`, `Letter`), portrait/landscape orientation, 0–100 mm margins, bounded interpolated header/footer text, and an explicit page-number flag. Emit CSS `@page` and fixed document chrome from the server-rendered HTML preview.

**Alternatives:** Keep layout settings browser-only; this would make saved drafts and server output diverge. Accept arbitrary CSS; this would violate the bounded template contract. Select a final PDF engine now; E4-01 native comparison remains pending.

**Consequences:** Page settings persist with drafts and are visible in the server preview. The HTML candidate does not establish final PDF pagination, orphan control, native-reader fidelity, or accessibility certification.

**Validation:** Nine focused template-render tests pass, including bounded page settings and invalid-size rejection; the non-integration backend suite passes with `78 passed, 5 skipped, 6 warnings`. The frontend build passed (`47 modules`), the rebuilt Docker service is `running`/`healthy`, readiness returned HTTP 200, and six live Playwright tests passed, including the Letter-landscape page-settings flow and server-preview header/footer/page-number markup. No final PDF pagination or accessibility certification is claimed.

**Implementation/evidence:** [page renderer](../backend/app/rendering.py), [editor controls](../frontend/src/main.tsx), [template contract](template-contract.md), [tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

## DD-062: Send an explicit locale for server preview switching

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-08 and the E4/E5 locale-render contract

**Context:** The renderer already accepted locale overrides, but the editor preview always used the template default and offered no way to compare locale-specific output.

**Choice:** Add a bounded preview-locale selector for English, English UK, German, Arabic, Hindi, Thai, Chinese, and Japanese. Pass the selected locale explicitly to the isolated draft render request and expose it through the artifact's HTML `lang` attribute and existing locale-aware formatter behavior.

**Alternatives:** Change the persisted template locale whenever the preview changes; this conflates an inspection choice with template state. Claim broad multilingual support from script labels alone; this would violate the rendering evidence requirements.

**Consequences:** Owners can switch the server-generated preview locale without mutating the draft definition. Full script shaping, fonts, native-reader parity, and final PDF acceptance remain pending E4 evidence.

**Validation:** Ten focused template-render tests pass, including explicit locale override/HTML language and locale-formatting checks; the non-integration backend suite passes with `79 passed, 5 skipped, 6 warnings`. The frontend build passed (`47 modules`), the rebuilt Docker service is healthy with readiness HTTP 200, and seven live Playwright tests passed, including the locale selector changing the server-preview `lang` attribute to `de-DE`. No multilingual shaping, native-reader, font, or final-PDF certification is claimed.

**Implementation/evidence:** [editor](../frontend/src/main.tsx), [renderer](../backend/app/rendering.py), [locale contract](template-contract.md), [tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

## DD-063: Express page-flow intent as bounded block settings

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-07 and the E4/E6 candidate-render contract

**Context:** The renderer already avoided splitting ordinary paragraphs and table rows, but owners could not request a page break before a block or configure keep-together behavior from the editor.

**Choice:** Add `break_before` and `keep_together` booleans to editor-created text, table, loop, and conditional blocks. The editor exposes these as controls for the active block. The renderer emits `break-before: page` and `break-inside: avoid` as bounded inline styles/classes; no arbitrary CSS is accepted.

**Alternatives:** Make page flow browser-only; this would diverge from saved server output. Implement a full pagination engine before the E4 comparison; that would prematurely select an output engine. Accept arbitrary CSS page rules; this would weaken the template safety contract.

**Consequences:** Page-flow intent persists in draft definitions and is visible in the server preview. Orphan-heading and split-row acceptance still requires fixed documents, a selected PDF engine, visual baselines, and native-reader evidence.

**Validation:** Eleven focused template-render tests pass, including break-before and keep-together output. The non-integration backend suite passes with `80 passed, 5 skipped, 6 warnings`; the frontend build passes (`47 modules`); and all eight live Playwright tests pass after the rebuilt image. The Docker web service reports healthy on `127.0.0.1:8001`; no final pagination or accessibility certification is claimed.

**Implementation/evidence:** [editor](../frontend/src/main.tsx), [renderer](../backend/app/rendering.py), [flow contract](template-contract.md), [tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

## DD-058: Persist editor drafts through template versions and server preview

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E2-01; supersedes the local-only choice in DD-025

**Context:** The initial E2-01 editor intentionally kept changes in React state. That demonstrated interaction but did not make formatting persist in a template version or affect authoritative output.

**Choice:** Serialize editor text blocks into the existing draft-version API, including bounded font family, size, weight, italic, colour and alignment properties. Render the latest draft through the existing isolated server render endpoint and show its HTML artifact in a sandboxed browser preview. Reject unsafe style values at render time rather than accepting arbitrary CSS.

**Alternatives:** Keep the editor local until a final PDF engine exists; this delays verifiable persistence. Store arbitrary CSS; this creates an unsafe and non-portable template contract. Add a second persistence system; this would duplicate the existing E3 version model.

**Consequences:** E2-01 now has a persisted draft and server-rendered preview path for text formatting. The story remains partial because final PDF output, full page-flow behavior, and multilingual IME/caret acceptance are not complete.

**Validation:** The style-render regression test passed (`6 passed` in `test_template_logic.py`); the non-integration backend suite passed (`75 passed, 5 skipped, 6 warnings`) and the disposable-PostgreSQL suite passed (`79 passed, 1 skipped, 6 warnings`); the frontend TypeScript/Vite build passed (`46 modules`). The rebuilt Docker service reports `running`/`healthy` on `127.0.0.1:8001`, and three Playwright tests passed, including saving a formatted draft and displaying the server preview. The draft remains a partial E2-01 implementation because final PDF output and full page-flow/multilingual acceptance are not complete.

**Implementation/evidence:** [editor](../frontend/src/main.tsx), [renderer](../backend/app/rendering.py), [render tests](../backend/tests/test_template_logic.py), [E2 story](epics.md), [prior decision](design-decisions.md#dd-025-begin-e2-01-with-a-local-editor-slice-before-persistence-and-rendering).

## DD-057: Prioritize the extraction review queue for keyboard correction

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E10-03 review and correction workflow

**Context:** The review screen exposed editable extracted fields and provenance, but fields were presented in object order and did not provide a focused keyboard path for resolving the highest-risk values first.

**Choice:** Add a visible review queue ordered by failed validation rules, then confidence below 0.5, then remaining fields. Queue inputs save on blur and support Enter, ArrowDown and ArrowUp focus movement. Keep source-region links adjacent to the queue and hide the older unordered field grid so the prioritized queue is the authoritative editing surface.

**Alternatives:** Keep object-order fields and rely on mouse navigation; this leaves correction effort and keyboard traversal unprioritized. Add a full grid/spreadsheet interaction; that would introduce more interaction semantics than this story requires.

**Consequences:** Reviewers can begin with failed and low-confidence values using a compact keyboard workflow. The implementation remains a partial E10-03 slice: browser/manual keyboard verification and formal accessibility certification are not claimed.

**Validation:** `npm run build` passed (`tsc --noEmit` and Vite, 46 modules). The backend suite passed with `74 passed, 5 skipped, 6 warnings`; `compileall` and `git diff --check` passed. The rebuilt Docker web service is running on `127.0.0.1:8001`, reports `healthy`, and `/health/ready` returned HTTP 200 with database, storage, and frontend ready. No accessibility certification is claimed.

**Implementation/evidence:** [review queue](../frontend/src/main.tsx), [queue styles](../frontend/src/reviewQueue.css), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

## DD-048: Expose and interact with stored source-region provenance

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E8-07 and the source-highlight portion of E10-01

**Context:** Local extraction already retained page, element and box provenance, but the extraction response did not include the PageModel and the browser had no way to inspect or select those regions.

**Choice:** Return the exact PageModel used by an ingestion extraction response and add a coordinate-aware browser preview. Field source links and source rectangles select the same element ID, with keyboard activation for rectangles. Use a neutral coordinate preview when no native page image exists.

**Alternatives:** Re-fetch and independently reconstruct source geometry in the browser; rejected because it could drift from the extraction snapshot. Render a fabricated page image; rejected because it would imply visual/OCR fidelity not present in the current contract. Wait for a full OCR/layout engine; rejected because existing digital-PDF provenance can already be inspected safely.

**Consequences:** Reviewers can connect supported extracted values to their stored source boxes and inspect provenance without external services. Native page-image rendering, multi-page navigation, missing-field box drawing, and complete keyboard review remain pending; E10-01 is not fully accepted.

**Validation:** The extraction regression was corrected and the full backend suite passed (`68 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, readiness `200`, extraction `200`, and matching PageModel/source IDs and box `72,72,540,86`. No accessibility certification or native image equivalence is claimed.

**Implementation/evidence:** [extraction API](../backend/app/main.py), [browser source preview](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [tests](../backend/tests/test_extraction.py), [review contract](review-contract.md).

## DD-049: Add an explicit offline extraction benchmark harness

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-09 benchmark contract and CI execution

**Context:** The local extractor had no repeatable way to compare results against labelled documents. The backlog requires a per-schema accuracy report in CI and on demand, while no held-out labelled corpus or target accuracy has been supplied.

**Choice:** Add a standard-library JSONL benchmark runner that accepts explicit PageModels and expected field values, reports normalized/original exact-match rates and per-field counts for each schema, writes a JSON artifact, and runs in a manually triggerable/path-filtered CI workflow. Keep the checked-in three-schema fixture clearly labelled as a deterministic contract fixture.

**Alternatives:** Claim accuracy from unit tests or heuristic confidence values; rejected because neither is a held-out benchmark. Add a model/evaluation dependency; rejected because the harness must run offline and measure the current extractor independently of model providers. Fail CI against an invented threshold; rejected because no acceptance target has been agreed.

**Consequences:** Benchmark execution and artifact generation are now reproducible, and a real labelled corpus can be supplied without changing the runner. The fixture is not production evidence; OCR/layout coverage, line-item metrics, calibration and held-out accuracy remain pending.

**Validation:** Benchmark unit test passed (`1 passed`); the checked-in fixture runner generated a report for 3 documents across invoice, receipt and purchase-order with 1.0 normalized/original exact-match on this contract fixture. The full backend suite passed (`69 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. No production accuracy or confidence-calibration claim is made.

**Implementation/evidence:** [benchmark runner](../scripts/benchmark_extraction.py), [contract fixture](../backend/tests/fixtures/extraction_benchmark.jsonl), [CI workflow](../.github/workflows/extraction-benchmark.yml), [benchmark test](../backend/tests/test_benchmark.py), [extraction contract](extraction-contract.md).

## DD-050: Represent bounded line-item extraction as table rows with cell provenance

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-01, E9-07 and the table portion of E9-09

**Context:** The extraction contract supported scalar fields but did not represent repeating tables, even though the bundled invoice and purchase-order schemas require line-item arrays and the benchmark must report row/column accuracy.

**Choice:** Add optional versioned schema tables with named typed columns. The offline extractor recognizes explicit pipe-delimited rows in PageModel text elements, returns `tables.<name>.rows[].fields` with original/normalized values, confidence, validation and source page/box, and the benchmark reports exact row and column normalized-match rates.

**Alternatives:** Infer arbitrary table structure from whitespace; rejected because it would make row/column boundaries non-deterministic. Return unproven empty arrays; rejected because that would conceal missing extraction. Add a layout engine before defining the result shape; deferred because the contract can be tested independently while complex layout remains pending.

**Consequences:** Repeating-table consumers have a deterministic local contract and metrics can distinguish scalar fields from row/column results. This slice handles explicit delimited rows only; Docling layout, borderless/multi-page tables, row matching, labelled held-out accuracy and locale-aware table parsing remain incomplete.

**Validation:** Focused extraction/benchmark tests passed (`5 passed`); the full backend suite passed (`70 passed, 5 skipped, 6 warnings`); the benchmark fixture reports one invoice row with four matching columns at 1.0 on that fixture. Frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, readiness `200`, extraction `200`, one row, amount `6.00`, and source element `row-1`. No production accuracy claim is made.

**Implementation/evidence:** [local extractor](../backend/app/extraction.py), [benchmark](../scripts/benchmark_extraction.py), [fixture](../backend/tests/fixtures/extraction_benchmark.jsonl), [tests](../backend/tests/test_extraction.py), [benchmark tests](../backend/tests/test_benchmark.py), [contract](extraction-contract.md).

## DD-051: Establish a versioned extraction-engine registry with explicit optional availability

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E8-08 and E9-03 engine contract foundation

**Context:** The local extractor was callable directly, while the source backlog requires swappable Docling, PaddleOCR and an additional engine behind one contract. Those external packages are not installed or licence-approved in the current environment.

**Choice:** Add `extraction-engine-v1` with an offline local implementation, explicit descriptors for optional Docling/PaddleOCR availability, and Python entry-point discovery under `docplatform.extraction_engines`. Requests select an engine ID; unavailable or broken engines fail explicitly and never silently fall back. Isolated extraction workers use the same selector.

**Alternatives:** Pretend external engines are available; rejected because installation and runtime evidence are absent. Hard-code direct imports; rejected because it would make optional dependencies mandatory and weaken offline operation. Silently fall back from a requested engine; rejected because results would be attributed to the wrong engine.

**Consequences:** Engine selection and provenance are now explicit and third-party adapters can be added without changing the API shape. Actual Docling/PaddleOCR execution, a third engine, plugin packaging examples, engine-specific licence review, and accuracy comparison remain pending.

**Validation:** Engine/API focused tests passed (`9 passed`); the full backend suite passed (`72 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, readiness `200`, and `/api/extraction-engines` returned three descriptors with local available and Docling unavailable. No external network or model call is made by the local path, and no third-party engine completion claim is made.

**Implementation/evidence:** [engine registry](../backend/app/engines.py), [worker integration](../backend/app/worker_child.py), [API](../backend/app/main.py), [tests](../backend/tests/test_engines.py), [contract](extraction-contract.md).

## DD-052: Make extraction validation rules explicit and review-triggering

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-05 validation contract

**Context:** Extraction already reported required, type, minimum and pattern findings, but the source story also requires ranges, checksums and totals that must add up.

**Choice:** Support schema-level `maximum`, `minimum`, regex `pattern`, `checksum: luhn`, and `totals` rules comparing a scalar field with a named table column within a configurable decimal tolerance. Any failed rule is retained in the result, lowers heuristic confidence, and sets the field/result to `needs_review`; values are never silently corrected.

**Alternatives:** Normalize invalid values into compliance; rejected because it would destroy the original signal. Implement domain-specific checks in the UI; rejected because API, worker and benchmark consumers need the same validation. Claim full financial validation from one total rule; rejected because currencies, tax semantics and locale-specific checks still require broader coverage.

**Consequences:** Common review blockers are represented consistently in API results and exports. Checksum support is currently Luhn only, totals are explicit table-column sums, and confidence remains heuristic until calibration data exists.

**Validation:** Focused extraction tests passed (`5 passed`); the full backend suite passed (`73 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, and readiness `200`. No financial, checksum or confidence-calibration certification is claimed.

**Implementation/evidence:** [validation implementation](../backend/app/extraction.py), [tests](../backend/tests/test_extraction.py), [contract](extraction-contract.md).

## DD-053: Normalize extracted dates and numbers using the request locale

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-06 locale-aware normalization

**Context:** The extractor preserved originals but treated commas as thousands separators and used a fixed date-order fallback, which misread common comma-decimal and day-first documents.

**Choice:** Pass the requested locale through scalar and table normalization. Recognize comma-decimal locale families, thousands separators, ISO/dot/day-first dates and US month-first dates, while retaining the exact extracted original value and returning canonical ISO/decimal strings.

**Alternatives:** Infer locale from currency symbols alone; rejected because symbols are ambiguous and locale is already an explicit API input. Normalize all values with one global convention; rejected because it misreads valid regional formats. Add a locale library immediately; deferred to avoid an unreviewed dependency while the supported deterministic subset is documented.

**Consequences:** `de-DE` and related locale families now normalize representative dates, numbers and currencies consistently across fields and line-item columns. Full CLDR coverage, locale-specific accounting formats, native labels and multilingual evaluation remain pending.

**Validation:** Focused locale/extraction tests passed (`6 passed`); the full backend suite passed (`74 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, and readiness `200`. No broad locale correctness claim is made.

**Implementation/evidence:** [locale normalization](../backend/app/extraction.py), [tests](../backend/tests/test_extraction.py), [contract](extraction-contract.md).

## DD-054: Publish deterministic bundled-schema samples with expected output

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-02 bundled schema starters

**Context:** The three bundled schemas were listed by API but had no sample document or expected output contract for operators to start from and verify.

**Choice:** Add one versioned, offline PageModel sample and expected normalized scalar/table output for invoice, receipt, and purchase-order. Expose each through a schema sample URL and keep the sample data deterministic and small enough for contract tests.

**Alternatives:** Generate samples dynamically from the extractor; rejected because expected output must remain an independent acceptance fixture. Use real customer documents; rejected because they introduce provenance/licence/PII concerns. Add binary PDFs immediately; deferred because the PageModel contract is the current local extraction boundary.

**Consequences:** API clients and tests can start from all three bundled schemas and compare normalized results. Browser sample-document launch, richer binary fixtures, OCR/layout coverage and independently labelled accuracy remain pending.

**Validation:** Schema/sample API tests round-tripped all three bundled samples through local extraction; the full backend suite passed (`74 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0; live checks returned `health=healthy`, UI `200`, readiness `200`, schema index `200`, and sample endpoint `200` checks for invoice and receipt. No production accuracy or native-document fidelity claim is made.

**Implementation/evidence:** [sample definitions](../backend/app/extraction.py), [sample API](../backend/app/main.py), [tests](../backend/tests/test_extraction.py), [contract](extraction-contract.md).

## DD-055: Add an editable, validated extraction-schema contract without persistence claims

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-01 schema definition, JSON Schema projection and browser editor

**Context:** The extraction API accepted inline schemas, but the bundled definitions were not inspectable as JSON Schema and the UI always extracted invoice fields with no schema editing or selection.

**Choice:** Expose bundled domain schemas, a JSON Schema projection, and a validation endpoint. Add a browser schema selector and JSON editor; validate drafts before use and submit the edited domain schema with the extraction request. Keep edits session-local because durable schema versioning belongs to the later governance contract.

**Alternatives:** Treat JSON Schema as the extractor's direct runtime format; rejected because labels, tables, checksum and total rules need domain metadata. Persist browser drafts immediately; deferred because it would create unversioned schema ownership semantics. Keep the invoice hard-code; rejected because it hides the bundled schema capability.

**Consequences:** Operators can inspect and modify a schema in the UI and clients can consume a standard JSON Schema projection. Draft persistence, schema version migration, advanced JSON Schema keyword coverage and authenticated schema ownership remain pending.

**Validation:** Schema projection/validation tests passed (`6 passed`); the full backend suite passed (`74 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. Docker rebuilt with migration exit 0 and the live container reports `running`/`healthy`. No durable schema-save or governance completion claim is made.

**Implementation/evidence:** [schema contract](../backend/app/extraction.py), [schema API](../backend/app/main.py), [browser editor](../frontend/src/main.tsx), [styles](../frontend/src/editor.css), [tests](../backend/tests/test_extraction.py), [documentation](extraction-contract.md).

## DD-056: Measure confidence calibration from labelled benchmark outcomes

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-04 confidence reporting

**Context:** The extractor returned heuristic confidence values, but the benchmark only measured value accuracy and could not show whether confidence tracked correctness.

**Choice:** Extend the offline benchmark report with per-schema and per-field mean confidence, empirical normalized accuracy, Brier score and absolute calibration error, plus equivalent line-item cell metrics. Missing predictions count as zero-confidence incorrect outcomes. Do not apply an invented threshold or relabel heuristic confidence as calibrated.

**Alternatives:** Claim calibration from the existing `0.90`/`0.35` constants; rejected because constants are not evidence. Add a calibration model before a labelled corpus exists; rejected because it would overfit the deterministic fixture. Fail CI against an unagreed threshold; rejected because the source supplies no target.

**Consequences:** CI and on-demand benchmark runs now expose the evidence needed to calibrate confidence once a held-out labelled corpus is supplied. The checked-in fixture remains a contract fixture, and no production calibration claim is made.

**Validation:** Benchmark calibration test passed (`1 passed`); the checked-in runner generated a report for 3 documents across three schemas, including scalar samples=2 and invoice table-cell samples=4 with empirical accuracy 1.0 and mean heuristic confidence 0.9 on this fixture. The full backend suite passed (`74 passed, 5 skipped, 6 warnings`); frontend `npm run build` passed (45 modules transformed), Python compilation and `git diff --check` passed. This fixture is not production calibration evidence.

**Implementation/evidence:** [benchmark](../scripts/benchmark_extraction.py), [benchmark test](../backend/tests/test_benchmark.py), [fixture](../backend/tests/fixtures/extraction_benchmark.jsonl), [contract](extraction-contract.md).

## DD-047: Add bounded page-element provenance for digital PDF ingestion

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E8-06; digital-PDF ingestion contract only

**Context:** E8-06 requires structured page elements with bounding boxes and matching Markdown anchors. The local ingestion path did not yet expose element-level provenance, while adopting a complete PDF layout engine would add a dependency and an unvalidated rendering/extraction claim.

**Choice:** Extract the simple PDF text operator form `(text) Tj` in the existing offline path, assign deterministic synthetic point boxes, persist those elements in the page model, and emit matching Markdown comments containing element ID, page and box. Complex PDF operators and OCR layout remain explicitly outside this slice.

**Alternatives:** Add a full PDF parser now; this would expand dependencies and require licence/layout validation before the contract could be trusted. Return fabricated elements for every page; this would misrepresent provenance. Reject all digital PDFs until a full parser exists; this would unnecessarily remove the already-supported bounded local path.

**Consequences:** Digital PDFs containing the supported text operator now have inspectable element-to-Markdown provenance. The implementation remains partial: complex layout, images, tables, OCR coordinates and native-reader equivalence are not claimed.

**Validation:** Focused ingestion/extraction tests passed (`6 passed`); the full backend suite passed (`68 passed, 5 skipped`); Python compilation and `git diff --check` passed. Docker rebuilt successfully; live checks returned `health=healthy`, UI `200`, readiness `200`, upload `201`, result `200`, with two returned elements and matching Markdown anchors. No complete PDF parser or multilingual/layout benchmark is claimed.

**Implementation/evidence:** [ingestion contract](ingestion-contract.md), [ingestion implementation](../backend/app/ingestion.py), [API integration](../backend/app/main.py), [tests](../backend/tests/test_ingestion.py).

## DD-044: Make TLS termination and secure cookies an explicit deployment contract

- **Date:** 2026-09-24
- **Status:** Implemented; deployment acceptance partial
- **Scope:** E11-03 TLS reference and secure session-cookie configuration

**Context:** The local Compose service intentionally serves loopback HTTP, while E11-03 requires a documented TLS deployment path. Authentication cookies were hard-coded insecure for local development, with no explicit production switch.

**Choice:** Keep TLS termination at a reverse proxy, document Caddy and Nginx upstream examples, and add `secure_cookies` configuration. The default remains false for local HTTP; operators set it true when the external endpoint is HTTPS.

**Alternatives:** Terminate TLS inside the application container; rejected because certificate lifecycle and private-key handling belong at the deployment edge. Always mark cookies Secure; rejected because that breaks the supported local HTTP quickstart.

**Consequences:** The deployment contract distinguishes local HTTP from HTTPS operation and prevents session cookies from being sent over HTTP when enabled. Certificate issuance, renewal, HSTS, proxy hardening and an actual TLS deployment remain operator responsibilities and are not certified here.

**Validation:** The secure-cookie regression and configuration tests passed (`13 passed`); the full non-integration suite passed (`64 passed, 1 skipped, 4 deselected`); frontend build, Python compilation and `git diff --check` passed. The proxy snippets are documentation, not a live certificate test. No production TLS or security certification claim is made.

**Implementation/evidence:** [TLS guide](tls.md), [configuration](../backend/app/config.py), [auth cookie handling](../backend/app/main.py), [auth test](../backend/tests/test_auth.py), [configuration reference](e1-foundation.md).

## DD-045: Enforce the dependency licence allow-list with an auditable SBOM scan

- **Date:** 2026-09-24
- **Status:** Implemented; policy gate intentionally failing
- **Scope:** E11-05 dependency metadata scan and SBOM generation

**Context:** The dependency inventory documented licence conflicts, but no repeatable command failed a build or emitted a machine-readable component report. The source allow-list conflict remains unresolved under DD-013/DD-022.

**Choice:** Add a standard-library scanner over the checked-in inventory. It accepts only unambiguous MIT, Apache-2.0 and OFL identifiers, emits CycloneDX-style JSON plus a findings report, and exits non-zero for unknown, compound or other licence metadata. Run it in GitHub Actions and upload reports even when the strict check fails.

**Alternatives:** Normalize BSD/MPL/PSF/compound expressions into approval; rejected because that silently weakens the source requirement. Make the workflow informational; rejected because E11-05 explicitly requires a disallowed licence to fail the build.

**Consequences:** Licence policy violations are visible and mechanically blocking, while the current repository correctly remains red with 44 findings. The report is based on checked-in package metadata and is not a complete container OS SBOM or legal approval; resolving the policy and reviewing upstream notices remains required.

**Validation:** Scanner regression test passed; strict mode exits 1 with 152 components and 44 findings; evidence mode emits `artifacts/sbom.cdx.json` and `artifacts/license-report.json`. Full backend/frontend validation remains required after the repository test addition.

**Implementation/evidence:** [scanner](../scripts/check_licenses.py), [workflow](../.github/workflows/license-scan.yml), [test](../backend/tests/test_license_scan.py), [inventory](dependency-inventory.json), [dependency review](dependencies.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-046: Add an optional fail-closed upload virus-scan hook

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E11-04 optional upload scanner and E8 ingestion boundary

**Context:** Upload size/type/magic-byte checks and isolated document execution were present, but deployments had no controlled integration point for an organization-provided virus scanner.

**Choice:** Add a JSON-array command configuration and timeout. Before storage, write a temporary upload copy, invoke the fixed command plus the path with `shell=False`, remove credentials from its environment, and accept only exit code zero. Nonzero, missing executable and timeout outcomes reject the upload; scanner output is not exposed.

**Alternatives:** Execute a shell command string; rejected because it creates command-injection and quoting hazards. Treat scanner failures as clean; rejected because a configured security control must fail closed. Bundle a specific antivirus engine; deferred because engine licensing, deployment and signature updates are operator-specific.

**Consequences:** Self-hosters can connect ClamAV or another approved scanner without adding an application dependency. The hook remains optional, and no particular scanner, signature database, malware-detection rate or full hostile-file containment certification is claimed.

**Validation:** Clean, nonzero and timeout scanner tests pass (`16 passed` across security, ingestion and configuration tests); the full non-integration suite passed (`68 passed, 1 skipped, 4 deselected`); frontend build and Python compilation passed. The rebuilt Docker migration exited 0, the web service is healthy, and live UI/readiness checks return HTTP 200. Upload rejection occurs before object persistence in the ingestion path.

**Implementation/evidence:** [security hook](../backend/app/security.py), [configuration](../backend/app/config.py), [ingestion API](../backend/app/main.py), [tests](../backend/tests/test_security.py), [contract](ingestion-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-030: Show evidence-backed status for every source story

- **Date:** 2026-09-23
- **Status:** Implemented
- **Scope:** Implementation enabler; project-status view, no backlog scope change

**Context:** The project-status view listed every source story but only showed status at epic level. The user requested a status for each user story.

**Choice:** Add a status column to every story row. Use `Implemented` only for stories with an executable contract and recorded validation, `Partial` for prepared or explicitly incomplete slices, and `Planned` as the default for stories without evidence. Keep the mapping in a small checked-in overlay separate from the generated backlog data.

**Alternatives:** Infer status from epic progress; rejected because it would overstate individual story delivery. Rewrite `docs/epics.md` with status fields; rejected because it is generated source transcription.

**Consequences:** The UI now exposes story-level traceability while preserving the original story fields. The overlay must be updated whenever implementation evidence changes; `Planned` does not mean rejected or deprioritized.

**Validation:** TypeScript/Vite production build passed after the change. No acceptance, accessibility certification, or native-reader sign-off is inferred from the status labels.

**Implementation/evidence:** [status overlay](../frontend/src/storyStatus.ts), [status table](../frontend/src/main.tsx), [styles](../frontend/src/editor.css), [translations](../frontend/src/i18n.ts), [source backlog](epics.md).

## DD-031: Add launch contribution and script-matrix documentation

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E14-02, E14-03; E14-04 documentation linkage

**Context:** Launch Must stories require contributor guidance and a public script test matrix, but the project still has unresolved licence policy and no native-reader approval for the rendering spike.

**Choice:** Add repository contribution guidance, a code-of-conduct policy with its unresolved enforcement contact called out, and an offline script-matrix page covering the required script families plus Korean. Link the matrix from the README and mark the corresponding story statuses partial until the missing governance and rendering evidence exists.

**Alternatives:** Claim launch readiness from placeholder files; rejected because the source acceptance requires a chosen contribution agreement and rebuilt CI results. Hide the renderer gaps; rejected because E4-01 remains pending-native-review.

**Consequences:** Contributors have an explicit starting point and users can inspect current script-contract coverage. Public launch still requires a licence/contribution decision, CI visual regression, exact fixture manifests, and native-reader review.

**Validation:** `npm run build` passed and `python scripts/render_spike.py` passed with `pending-native-review`. No licence approval, native-reader approval, or CI visual-regression claim is made.

**Implementation/evidence:** [contributor guide](../CONTRIBUTING.md), [code of conduct](../CODE_OF_CONDUCT.md), [script matrix](script-test-matrix.md), [README](../README.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-032: Establish a durable bounded ingestion contract before OCR workers

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E8-01, E8-02, E8-05, E8-06 contract foundation

**Context:** Upload routing and the PageModel are prerequisites for OCR, extraction, review, and the closed loop. The named Docling/PaddleOCR engines and hostile-document worker isolation are not yet integrated, so the platform must not present empty extraction data as a completed result.

**Choice:** Add a durable ingestion metadata table and raw-object storage path. Validate PDF/PNG/JPEG/TIFF signatures and content types, enforce the configured byte limit, classify PDFs with visible text operators as digital and all other accepted files as scan, and expose a versioned PageModel plus linked Markdown derivative through status/result endpoints. Mark pending extraction explicitly.

**Alternatives:** Accept arbitrary uploads and infer type from filenames; rejected because it weakens hostile-input handling. Emit fabricated OCR/layout elements; rejected because it would destroy provenance and accuracy evidence. Block all progress until the full worker stack exists; rejected because the contract can be tested independently.

**Consequences:** Upload metadata and routing survive API restarts after migration, and later workers have a stable input/result contract. The current slice is not multi-file UI completion, OCR, layout analysis, page geometry extraction, or a CPU benchmark.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_ingestion.py tests/test_template_logic.py` passed (`7 passed`); the non-integration suite passed (`54 passed, 1 skipped, 4 deselected`); Python compilation, frontend production build, and `git diff --check` passed. The Docker migration exited 0 and the rebuilt web container reports healthy. Full OCR/layout, multi-file UI, hostile-file, and CPU acceptance remain pending.

**Implementation/evidence:** [ingestion contract](../backend/app/ingestion.py), [API](../backend/app/main.py), [model](../backend/app/models.py), [migration](../backend/migrations/versions/0004_ingestion.py), [tests](../backend/tests/test_ingestion.py), [documentation](ingestion-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-033: Add a deterministic local extraction contract

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E9-01 through E9-06 contract foundation

**Context:** E9 depends on a versioned PageModel and must offer a local option without external calls. The repository has no labelled corpus or OCR-generated layout elements yet, so calibrated confidence and broad document accuracy cannot be claimed.

**Choice:** Add three bundled schema starters and an inline-schema API. The local extractor matches explicit labels in PageModel text elements, keeps original and normalized values, preserves page/element/box provenance, emits a heuristic confidence score, and reports required/type/minimum/pattern validation findings. Use Decimal for currency normalization.

**Alternatives:** Use an LLM or cloud provider by default; rejected because it conflicts with local/offline requirements and would add privacy/licence gates. Treat OCR confidence as field confidence; rejected because the two measures are distinct. Return normalized values without originals or source boxes; rejected because it breaks correction and audit requirements.

**Consequences:** Schema and extractor contracts can be tested before OCR workers are selected. Confidence is explicitly heuristic, and line-item accuracy, calibration, multilingual labels, exports, review, and closed-loop generation remain pending.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_extraction.py tests/test_ingestion.py tests/test_template_logic.py` passed (`9 passed`). Full non-integration and container validation remain required after the API tranche is integrated.

**Implementation/evidence:** [extractor](../backend/app/extraction.py), [API](../backend/app/main.py), [tests](../backend/tests/test_extraction.py), [documentation](extraction-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-034: Persist extraction revisions and gate generation on approval

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E10-02, E10-04, E10-06 contract foundation; E10-05 and E5-08 approved-binding foundation

**Context:** Local extraction could return provenance-preserving data but had no durable correction history or closed-loop approval boundary. Generating from an unreviewed result would violate the project requirement that only approved snapshots feed generation.

**Choice:** Persist extraction results with a revision and review status. Apply field corrections only when the caller supplies the current expected revision, record original/new values with an actor label and timestamp, expose CSV correction export, and reject template generation unless the result is explicitly approved. Add `new`, `in_review`, `approved`, and `rejected` states.

**Alternatives:** Mutate extraction JSON without history; rejected because corrections must be auditable. Allow any extracted result to feed templates; rejected because it bypasses review. Use client-only review state; rejected because API-side enforcement is required.

**Consequences:** The data path now has a durable review boundary and optimistic-concurrency protection. Authenticated actors, role authorization, source-image overlays, keyboard triage, full review UI, and state-transition audit policy remain incomplete; the current `local` actor label is not an identity system.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_extraction.py tests/test_ingestion.py tests/test_template_logic.py` passed (`10 passed`); the full non-integration suite passed (`57 passed, 1 skipped, 4 deselected`); Python compilation, frontend production build, and `git diff --check` passed. Docker migration exited 0 and the rebuilt web container reports healthy. Authenticated identity, review UI, overlays, and full acceptance remain pending.

**Implementation/evidence:** [models](../backend/app/models.py), [migration](../backend/migrations/versions/0005_extraction_review.py), [API](../backend/app/main.py), [tests](../backend/tests/test_extraction.py), [review documentation](review-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-035: Add local identity and protect review mutations

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E11-02 security contract; E10-02, E10-04, E10-06 actor boundary

**Context:** Review corrections and approval need attributable actors and CSRF protection. The existing foundation was intentionally unauthenticated and had no user/session tables.

**Choice:** Add a one-time initial-account setup endpoint, PBKDF2-SHA256 password hashes with per-password salts, server-side eight-hour sessions, HttpOnly SameSite cookies, CSRF tokens, generic invalid-credential errors, and five-failure/15-minute account lockout. Once a user exists, correction and review-state mutations require the session and CSRF token; an empty users table retains local bootstrap compatibility.

**Alternatives:** Store passwords client-side or in reversible form; rejected. Use bearer tokens in browser storage; rejected because server-side cookies and CSRF controls are safer for the browser workflow. Require auth before setup; impossible without an initial account provisioning path.

**Consequences:** Review actors now resolve to authenticated email addresses after setup. Role enforcement across all API operations, scoped API keys, secure-cookie deployment configuration, login UI, and independent security review remain pending; this is not a complete E11-02 acceptance claim.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_auth.py tests/test_extraction.py tests/test_ingestion.py tests/test_template_logic.py` passed (`11 passed`); the full non-integration suite passed (`58 passed, 1 skipped, 4 deselected`); Python compilation, frontend production build, and `git diff --check` passed. The rebuilt Docker migration exited 0 and the web container reports healthy.

**Implementation/evidence:** [auth primitives](../backend/app/auth.py), [models](../backend/app/models.py), [migration](../backend/migrations/versions/0006_identity.py), [API](../backend/app/main.py), [tests](../backend/tests/test_auth.py), [documentation](auth-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-036: Add hashed scoped API keys with explicit rotation

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E7-02 API-key contract

**Context:** The REST surface needs machine credentials that can be limited and rotated without storing reusable plaintext secrets. Browser review mutations already have a session/CSRF boundary.

**Choice:** Add session-protected create/list/revoke endpoints. Generate `dp_` secrets with cryptographic randomness, store only a SHA-256 digest plus a display prefix, return plaintext only at creation, and enforce `read`, `render`, or `admin` scopes when an API key is supplied. Revocation is a timestamped soft delete.

**Alternatives:** Store plaintext keys for later display; rejected because database compromise would expose credentials. Use one global bearer secret; rejected because it cannot be scoped or rotated. Let API keys approve review corrections; rejected because those actions require an authenticated browser session and CSRF token in this tranche.

**Consequences:** Machine clients have a concrete rotation/scoping contract. Key expiry, audit events, per-key rate limits, role/folder authorization, and complete endpoint coverage remain pending; existing local-open behavior remains for requests without a key until deployment authorization policy is enabled.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_auth.py tests/test_epic34.py` passed (`4 passed`); the full non-integration suite passed (`59 passed, 1 skipped, 4 deselected`); Python compilation, frontend production build, and `git diff --check` passed. The rebuilt Docker migration exited 0 and the web container reports healthy.

**Implementation/evidence:** [auth](../backend/app/auth.py), [API](../backend/app/main.py), [model](../backend/app/models.py), [migration](../backend/migrations/versions/0007_api_keys.py), [tests](../backend/tests/test_auth.py), [documentation](auth-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-037: Persist render and extraction jobs with expiring leases

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E7-04 and E12-01/E12-02 contract foundation

**Context:** Render and extraction requests need durable polling state and must not disappear when the API process is recreated. The final isolated worker supervisor and resource controls are not yet present.

**Choice:** Add a versioned job table with kind, status, payload/result, attempts, lease owner/expiry, timestamps, and sanitized error. Enqueue render/extraction jobs, claim queued or expired-lease work for 60 seconds, execute the bounded current contracts, and expose status polling. Keep execution endpoint-driven until isolated workers are implemented.

**Alternatives:** Use in-process background tasks; rejected because they do not survive process restart. Add a broker immediately; deferred because the planned MVP queue uses PostgreSQL and the broker would add an unresolved dependency surface. Claim CPU/memory isolation from evaluator limits; rejected because true process limits require worker supervision.

**Consequences:** Job state survives application recreation and stale leases can be reclaimed. The current executor is not yet an isolated process, does not provide complete retry/DLQ policy, and does not satisfy final runaway-job containment or scale acceptance.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_jobs.py tests/test_auth.py tests/test_epic34.py` passed (`6 passed`); the full non-integration suite passed (`61 passed, 1 skipped, 4 deselected`); Python compilation, frontend production build, and `git diff --check` passed. The rebuilt Docker migration exited 0 and the web container reports healthy.

**Implementation/evidence:** [job model](../backend/app/models.py), [migration](../backend/migrations/versions/0008_jobs.py), [job helpers](../backend/app/jobs.py), [API](../backend/app/main.py), [tests](../backend/tests/test_jobs.py), [documentation](jobs-contract.md), [status overlay](../frontend/src/storyStatus.ts).

## DD-038: Add multi-file browser ingestion with per-file status

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E8-01 and E8-05 UI contract foundation

**Context:** The API accepts bounded individual uploads, but the workspace did not expose the source-document intake flow required by the ingestion stories.

**Choice:** Add a native multi-file input for PDF/PNG/JPEG/TIFF, submit each file independently to the versioned ingestion API, and show per-file uploading, queued, failed, route, and error state. Keep the source file name in the list and avoid implying OCR completion.

**Alternatives:** Upload all files as one opaque multipart request; rejected because individual status and retry boundaries would be lost. Show a completed extraction result immediately; rejected because the current queue only records ingestion/routing and later workers are not present.

**Consequences:** The UI now demonstrates multi-file intake and visible progress/status for each upload. Polling, retry controls, OCR progress, page previews, and extraction/review UI remain pending.

**Validation:** `npm run build` passed (45 modules transformed). The Docker image rebuilt successfully with the ingestion UI, the migration exited 0, and the web service is published on `127.0.0.1:8001` while its health check starts. Browser interaction and accessibility certification remain unclaimed.

**Implementation/evidence:** [workspace](../frontend/src/main.tsx), [styles](../frontend/src/editor.css), [translations](../frontend/src/i18n.ts), [status overlay](../frontend/src/storyStatus.ts), [ingestion API](../backend/app/main.py).

## DD-039: Persist bounded ingestion page progress

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E8-05 page limits/progress and E8-01/E8-02 ingestion metadata

**Context:** Uploads were byte-bounded and routed, but page limits and progress were not represented in configuration, persistence, API responses, or the browser intake.

**Choice:** Add a documented `max_pages_per_document` setting (default 100), conservatively count PDF page markers without executing or fully parsing the file, persist `pages_total` and `pages_processed`, and poll the ingestion endpoint from the UI. Reject an upload over the configured limit before storage. Keep processed pages at zero until an isolated layout/OCR worker exists.

**Alternatives:** Derive page counts only inside the future parser; rejected because limits must be enforced before unbounded processing. Report upload bytes as page progress; rejected because it would misrepresent OCR/layout completion.

**Consequences:** Long-file limits and a durable progress contract now exist for local/offline ingestion. The count is intentionally conservative and not a claim of PDF parsing correctness; worker processing, real OCR/layout progress, and page-level validation remain pending.

**Validation:** Focused ingestion, extraction and jobs tests passed (`7 passed`); the ingestion regression suite passed (`3 passed`); frontend TypeScript/Vite build and Python compilation passed. The new over-page-limit regression test verifies HTTP 413 before persistence. Migration `0009` exited 0 in Docker; the live service is healthy, readiness/docs return HTTP 200, and a live PDF smoke upload returned HTTP 201 with `digital` routing and `0/1` page progress. Browser-level accessibility and OCR/layout accuracy remain unclaimed.

**Implementation/evidence:** [configuration](../backend/app/config.py), [ingestion logic](../backend/app/ingestion.py), [API](../backend/app/main.py), [model](../backend/app/models.py), [migration](../backend/migrations/versions/0009_ingestion_progress.py), [tests](../backend/tests/test_ingestion.py), [browser intake](../frontend/src/main.tsx), [contract](ingestion-contract.md).

## DD-040: Export persisted extraction results as JSON and CSV

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E9-08 JSON/CSV export slice

**Context:** Persisted extraction results and correction logs existed, but consumers did not have a result export containing field values, confidence, review status, validation and source coordinates.

**Choice:** Add authenticated-contract-compatible JSON and CSV result endpoints keyed by extraction result ID. Export the stored result snapshot and include one CSV row per field with original/normalized values, confidence, review state, validation and source page/box. Keep Excel generation and webhook delivery out of this slice.

**Alternatives:** Export only the correction log; rejected because it omits unchanged extracted fields and their confidence. Generate CSV from a fresh extraction; rejected because exports must represent the persisted revision under review.

**Consequences:** API consumers can download deterministic JSON/CSV snapshots without external services. CSV is intentionally flat and source boxes/validation are JSON-encoded cells; Excel formatting, webhook retries/signatures and benchmark evidence remain pending.

**Validation:** Extraction tests cover approved status and exported confidence/field rows; the full non-integration suite passed (`62 passed, 1 skipped, 4 deselected`). Frontend build and live API smoke evidence remain unchanged by this backend-only slice.

**Implementation/evidence:** [API](../backend/app/main.py), [tests](../backend/tests/test_extraction.py), [contract](extraction-contract.md).

## DD-041: Isolate document execution in bounded child processes

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E12-02 and the execution boundary used by E7-04/E12-01

**Context:** Durable jobs and leases existed, but render and extraction ran inside the API process. That did not satisfy the requirement to stop runaway work without affecting the API or to keep document workers away from credentials and network access.

**Choice:** Pass only validated JSON inputs to a dedicated Python child module. Remove database/storage credential variables from its environment, deny socket connection attempts, apply POSIX CPU/address-space limits when available, enforce a parent wall-time and serialized-output limit, and kill the child process group on timeout. Synchronous and approved-result rendering use the same boundary.

**Alternatives:** Continue relying on template evaluator iteration limits; rejected because parser/renderer/extractor failures can occur outside the evaluator. Use a full broker/supervisor now; deferred because the durable PostgreSQL queue and separate worker deployment are larger operational work, while the child boundary is independently testable.

**Consequences:** API-triggered document work no longer executes in the API interpreter, and the limits are configurable and documented. Windows does not expose POSIX `resource` limits in this implementation, although wall-time termination and a new process group are still used; container cgroups and a restart-safe worker supervisor remain required for final acceptance. The current API endpoint remains the trigger rather than a continuously running worker service.

**Validation:** Existing job tests passed with child-process execution (`2 passed`); the full non-integration suite passed (`62 passed, 1 skipped, 4 deselected`); frontend build, Python compilation and `git diff --check` passed. The rebuilt Docker migration exited 0, the web service is healthy on `127.0.0.1:8001`, and a live render job completed `done` with the expected `Hello Ada` artifact. No final E12-02 completion claim is made because supervisor, cgroup and restart/resource-exhaustion evidence remain pending.

**Implementation/evidence:** [child launcher](../backend/app/worker.py), [child entry point](../backend/app/worker_child.py), [API integration](../backend/app/main.py), [configuration](../backend/app/config.py), [job contract](jobs-contract.md).

## DD-042: Treat generated OpenAPI and explorer as the API reference surface

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E7-03 generated explorer/spec contract

**Context:** FastAPI already exposed `/docs` and `/openapi.json`, but there was no repository API reference or regression check proving that core routes remained in the generated specification.

**Choice:** Keep the framework-generated OpenAPI document as the source of truth, link the interactive explorer and JSON spec from the documentation, and add a contract test for explorer reachability plus representative template, ingestion, extraction-export and job paths.

**Alternatives:** Maintain a hand-written OpenAPI file; rejected because it would drift from route code. Test only HTTP 200 on `/docs`; rejected because it would not detect missing or renamed API paths.

**Consequences:** Developers can inspect and try current calls without a second schema artifact, and route-presence regressions are caught in tests. This does not certify every request/response behavior, SDK compatibility, authentication flow, or production API usability.

**Validation:** The new OpenAPI contract test passed as part of the full backend suite (`62 passed, 1 skipped, 4 deselected` before this test was added; the focused rerun is required after this change). The live `/docs` and `/openapi.json` endpoints were previously verified HTTP 200; no broader acceptance claim is made.

**Implementation/evidence:** [API reference](api-reference.md), [contract test](../backend/tests/test_epic34.py), [generated API](../backend/app/main.py), [status overlay](../frontend/src/storyStatus.ts).

## DD-043: Add a revision-safe browser review workflow

- **Date:** 2026-09-24
- **Status:** Implemented; partial acceptance
- **Scope:** E10-02, E10-03, E10-04 and E10-05 browser workflow slice

**Context:** The API supported extraction corrections, review states and approved-only rendering, but the workspace provided no way to exercise that closed loop from the browser.

**Choice:** Add a review card for each extracted upload. The card exposes field inputs, saves edits on blur with the current revision, shows confidence/validation, supports approve/reject, and enables approved-result rendering into the first available template. Explain the missing source-image overlay directly in the UI.

**Alternatives:** Treat an upload as automatically approved; rejected because approval must remain an explicit human action. Build a fake page preview; rejected because the current PageModel contains no OCR/layout regions and would misrepresent provenance.

**Consequences:** Local users can exercise correction, approval and approved binding without an external service. The UI currently uses the bundled invoice schema, has no source image/box overlay, no drawn missing-field boxes, and no dedicated low-confidence keyboard queue; those remain partial.

**Validation:** Frontend TypeScript/Vite build passed (45 modules transformed); the full backend suite passed (`63 passed, 1 skipped, 4 deselected`); Docker rebuilt and the web service is healthy. A live smoke flow uploaded a PNG, extracted an invoice result, saved a correction at revision 2, approved it, and bound it to a template successfully. Browser-level interaction, keyboard-only review and accessibility certification remain unclaimed.

**Implementation/evidence:** [workspace review flow](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [translations](../frontend/src/i18n.ts), [review API](../backend/app/main.py), [status overlay](../frontend/src/storyStatus.ts).

## DD-029: Bound declarative template evaluation

- **Date:** 2026-09-23
- **Status:** Implemented; partial acceptance
- **Scope:** E5-01 through E5-07 contract slice; render API error handling

**Context:** The existing data-only evaluator resolved paths, loops, conditions and formatters, but recursive template expansion and loop sizes were not explicitly bounded. E5-06 requires templates to run without code execution or network access, and unbounded declarative work could still exhaust the process.

**Choice:** Keep the evaluator as a whitelist-only Python domain module. Add maximum nesting depth (20), expanded block budget (2,000) and loop item budget (1,000); expose limit failures as structured HTTP 422 responses. Add comparison predicates and ISO date-string formatting while preserving the explicit missing-field policies.

**Alternatives:** Permit arbitrary expression evaluation; rejected because it violates the no-code-execution boundary. Add a third-party expression engine; deferred because it adds dependency/licence surface without being required for the bounded MVP grammar.

**Consequences:** Typical templates can use nested paths, loops, boolean/comparison conditions and locale-aware formatters while runaway expansion fails predictably. These limits are initial operational defaults, not measured capacity targets. Approved extraction binding, aggregates, remote data, and final PDF output remain unimplemented.

**Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_template_logic.py` passed with 5 tests. The targeted E3/E4 run reached 6 passed before the integration test's `tmp_path` fixture failed with Windows `PermissionError` scanning the pre-existing `C:\\Users\\jayen\\AppData\\Local\\Temp\\pytest-of-jayen` directory; no assertion failure was observed. Full API/database and hostile-process validation remain pending.

**Implementation/evidence:** [template evaluator](../backend/app/template_logic.py), [render API](../backend/app/main.py), [tests](../backend/tests/test_template_logic.py), [source criteria](epics.md#e5-data-binding-and-template-logic).

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
- **Status:** Superseded by DD-058; historical partial slice retained
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
## DD-071 — Bounded multilingual extraction label aliases

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E9-10
- Context: Local extraction must support common multilingual field labels without introducing an external translation dependency or unbounded fuzzy matching. The implementation must preserve the schema field name and the original extracted value while making a deliberately limited language expansion.
- Choice: Add a small, explicit alias dictionary for Arabic, Hindi, Thai and Chinese for the currently supported invoice number, invoice date, total and merchant fields. Resolve regional locales such as `zh-CN` to their base language, retain schema-defined labels, deduplicate aliases, and apply the existing bounded label/value matcher. No network calls or automatic translation are used.
- Alternatives considered: An external translation service was rejected because local extraction must work offline and the service would introduce data-governance and availability dependencies. General-purpose fuzzy matching was deferred because it could increase false positives and make provenance difficult to explain. A larger language dictionary is deferred until representative native-language samples are available.
- Consequences: The local path now recognizes the documented aliases deterministically and remains CPU/offline compatible. Coverage is intentionally partial: no native sample set, accuracy benchmark, OCR-specific variants or multilingual rendering claim is made by this change.
- Validation: `backend/tests/test_extraction.py` passed 7 tests; the full backend suite passed 88 tests with 5 skipped and 3 warnings; Python compilation passed; `git diff --check` passed (with existing LF/CRLF normalization warnings); the Docker image rebuilt successfully with the frontend build reporting 47 transformed modules; `/health/ready` returned 200; and a live `zh-CN` extraction smoke test normalized `合计: 12.50` to `12.50`.
- Implementation references: `backend/app/extraction.py`, `backend/tests/test_extraction.py`, `docs/extraction-contract.md`, `frontend/src/storyStatus.ts`.
## DD-072 — Revision-safe missing-field and undo review operations

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E10-02, E10-06
- Context: The review surface could edit existing extracted fields, but it had no contract for adding a field from a selected source box, marking a field absent, or undoing the latest correction. Review changes must remain attributable, revision-safe and excluded from approval until explicitly reviewed.
- Choice: Add revision-checked `POST /api/extractions/{result_id}/fields` for manual field creation, extend the existing field correction operation with an `absent` marker, and add revision-checked `POST /api/extractions/{result_id}/undo` that restores the latest correction value while appending an audit correction. Manual fields retain source page/element/box provenance when supplied and are always placed in `in_review`.
- Alternatives considered: Mutating the extraction JSON without an audit row was rejected because it would break correction history. Deleting correction rows for undo was rejected because it erases evidence. A client-only undo stack was rejected because it would not survive reloads or coordinate concurrent reviewers.
- Consequences: Review clients can perform the core missing-field/absent/undo actions through an API contract that survives reloads. Undo restores values but does not yet restore arbitrary prior source metadata, and the browser still needs dedicated controls for drawing and invoking these operations; E10-02 therefore remains partial.
- Validation: The focused extraction/API suite passed 12 tests with 3 warnings; the full backend suite passed 88 tests with 5 skipped and 3 warnings; the TypeScript/Vite build passed with 47 transformed modules; the live Docker image rebuilt successfully; `/health/ready` returned 200; live `/openapi.json` exposed the field-creation and undo routes; and the nine Playwright foundation tests passed against `http://127.0.0.1:8001` when `PLATFORM_TEST_URL` was set explicitly. Browser-level drawing and native page-image fidelity remain unclaimed.
- Implementation references: `backend/app/main.py`, `backend/tests/test_extraction.py`, `backend/tests/test_epic34.py`, `docs/review-contract.md`, `frontend/src/main.tsx`, `frontend/src/storyStatus.ts`.
## DD-073 — Authenticated source-document preview for review

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E10-01, E8-07
- Context: Review provenance currently renders coordinate boxes over a blank PageModel canvas. E10-01 requires the source document beside the fields, but uploaded bytes must remain behind the object-storage abstraction and must not be exposed through filesystem paths.
- Choice: Add an authenticated `GET /api/ingestions/{document_id}/source` endpoint that reads the stored object through `ObjectStore` and returns it inline with the recorded media type. The review client uses the source URL for image documents and keeps the PageModel coordinate overlay as the authoritative interaction layer; unsupported or unavailable page images retain the explicit coordinate-only fallback.
- Alternatives considered: Returning a local file path was rejected because it bypasses storage backends and leaks deployment details. Embedding upload bytes in every extraction response was rejected because it increases result size and duplicates untrusted content. Rasterizing PDFs in the web request was deferred until a bounded PDF preview pipeline is selected and validated.
- Consequences: Reviewers can see the original uploaded image alongside source boxes without external calls, and storage access remains centralized. PDF page rasterization, multi-page image navigation, rotation-aware overlay calibration and native-reader review remain incomplete; E10-01 stays partial.
- Validation: The focused ingestion/API suite passed 8 tests with 3 warnings; the full backend suite passed 88 tests with 5 skipped and 3 warnings; the frontend TypeScript/Vite build passed with 47 transformed modules; the Docker image rebuilt successfully; `/health/ready` returned 200; the live source endpoint returned HTTP 200 with `application/pdf` and the expected 27-byte stored payload; and all 9 Playwright tests passed against port 8001 after the UI change. PDF rasterization and native page-image fidelity remain unclaimed.
- Implementation references: `backend/app/main.py`, `backend/tests/test_ingestion.py`, `frontend/src/main.tsx`, `frontend/src/editor.css`, `docs/review-contract.md`, `frontend/src/storyStatus.ts`.
## DD-074 — Deployment-enabled durable job supervisor

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E12-01, E12-02, E7-04
- Context: The PostgreSQL job table and isolated child runner already persisted state and enforced per-run bounds, but queued work only ran when a client called `/run`. That does not demonstrate resumption after an API restart.
- Choice: Add a configurable queue supervisor to the application lifespan. When `job_worker_enabled` is true, a daemon worker polls PostgreSQL for queued or expired-lease jobs, claims one with the existing lease contract, executes it through the isolated child boundary, and records the terminal state. Compose enables one supervisor by default; unit/integration fixtures keep it disabled unless a restart-resumption test opts in.
- Alternatives considered: In-process FastAPI background tasks were rejected because they are not durable across process restart. A new broker or separate worker image was deferred because it adds an unresolved dependency/deployment surface; the current supervisor makes the PostgreSQL contract observable first. Automatic retry/DLQ behavior remains outside these Must stories and is not silently added.
- Consequences: A deployment can resume queued work after a web process restart without an API client replaying `/run`, while render/extraction remain separately identifiable job kinds. This is not yet a horizontally scalable worker pool, heartbeat implementation, cgroup guarantee or load-test result; E12-01/E12-02 remain partial.
- Validation: The queue suite passed 3 tests, including application-restart resumption; the full backend suite passed 89 tests with 5 skipped and 3 warnings; frontend build passed with 47 transformed modules; Python compilation passed; the Docker image rebuilt and Compose enabled the supervisor; `/health/ready` returned 200; and a live queued render completed `done` with one attempt and a nonempty artifact. This does not claim horizontal scaling, cgroup enforcement or load-test throughput.
- Implementation references: `backend/app/jobs.py`, `backend/app/main.py`, `backend/app/config.py`, `compose.yaml`, `backend/tests/test_jobs.py`, `docs/jobs-contract.md`, `frontend/src/storyStatus.ts`.
## DD-075 — Independent render and extraction supervisor pools

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E12-03, E12-01
- Context: The deployment-enabled supervisor currently processes both job kinds through one polling loop. Render and extraction have different resource profiles and must be independently scalable in the operational contract.
- Choice: Add separate configurable render and extraction supervisor counts. Each loop claims only its assigned `Job.kind`, while both retain the same PostgreSQL lease and isolated-child execution path. Compose exposes `DOCPLATFORM_JOB_WORKER_RENDER_COUNT` and `DOCPLATFORM_JOB_WORKER_EXTRACTION_COUNT`, defaulting to one each when the supervisor is enabled.
- Alternatives considered: A single undifferentiated pool was rejected because one workload can starve the other. A broker and autoscaler were deferred because the current R2 acceptance can first be expressed with durable database-backed role pools. A throughput claim was rejected until a reproducible load test is added.
- Consequences: Render and extraction capacity can be changed independently without changing the job contract. The current implementation is still one application process with daemon threads, not independently deployed worker services; no throughput increase or load-test result is claimed, so E12-03 remains partial.
- Validation: The queue suite passed 4 tests, including kind-filtered claims; the full backend suite passed 90 tests with 5 skipped and 3 warnings; the frontend build passed with 47 transformed modules; Python compilation and `git diff --check` passed; the Docker image rebuilt; live settings reported `job_worker_enabled=True`, render count `1`, extraction count `1`; `/health/ready` returned 200; and a live queued render completed `done` with one attempt and a nonempty artifact. No throughput increase or horizontal worker claim is made.
- Implementation references: `backend/app/jobs.py`, `backend/app/main.py`, `backend/app/config.py`, `compose.yaml`, `backend/tests/test_jobs.py`, `docs/jobs-contract.md`.
## DD-076 — Evidence-bounded ten-minute quickstart

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E14-01, E7-03
- Context: The repository had API reference material but no single, timed setup path. The source story requires a new user to reach a generated PDF; the current approved renderer emits deterministic HTML and no PDF engine has been selected or licensed.
- Choice: Add a copy-paste quickstart for Compose, readiness, template discovery, synchronous HTML render and durable-job polling. State the PDF limitation next to the successful commands and keep E14-01 partial until an evidence-backed PDF engine and native-reader output validation are available.
- Alternatives considered: Claim HTML as PDF completion was rejected because it changes the source acceptance criterion. Add an unreviewed PDF dependency was rejected because rendering-engine selection and the DD-013 licence conflict remain unresolved. Use a browser-only print dialog was rejected as it is not a reproducible server/API contract.
- Consequences: New contributors can reach a verified local render and OpenAPI explorer within the documented flow, while the missing PDF gate remains visible. The quickstart is not a PDF-generation claim.
- Validation: Against the live Compose service, `/health/ready` returned 200, the bundled `Welcome letter` resolved as `sample-welcome`, and the documented render request returned a nonempty HTML artifact with no PDF field. The quickstart and API-reference links are present in `README.md`; PDF output remains explicitly unverified.
- Implementation references: `docs/quickstart.md`, `README.md`, `docs/api-reference.md`, `frontend/src/storyStatus.ts`.
## DD-077 — Structured contribution intake without premature licence selection

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E14-02
- Context: The repository already had a contributor guide and code of conduct, but no issue forms or pull-request checklist. The source story also requires a chosen contribution agreement, while DD-013 explicitly leaves the product licence and agreement unresolved.
- Choice: Add structured bug and feature issue forms plus a pull-request checklist that points contributors to the existing governance rules and requires evidence/status disclosure. Do not add a LICENSE, CLA or DCO declaration until the project owner selects one.
- Alternatives considered: Add an assumed MIT/Apache/CLA file was rejected because it would silently make an unresolved governance decision. Leave intake unstructured was rejected because it weakens the contributor path that can be implemented without that decision.
- Consequences: Repository contribution intake is more actionable and traceable, while E14-02 remains partial and the unresolved agreement is visible rather than implied.
- Validation: Both issue forms parsed successfully with PyYAML; README links to the contributor guide and code of conduct resolve; `git diff --check` passed with only existing LF/CRLF normalization warnings. No product licence, CLA or DCO was selected.
- Implementation references: `.github/ISSUE_TEMPLATE/bug-report.yml`, `.github/ISSUE_TEMPLATE/feature-request.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.
## DD-078 — Durable extraction review-state event log

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E10-04, E10-06
- Context: Extraction results stored the current review status and field corrections, but approval/rejection transitions were not separately auditable. E10-04 requires state changes to be logged and E10-06 requires attributable correction history.
- Choice: Add an append-only `extraction_review_events` table containing result ID, previous state, new state, actor and timestamp. Record explicit review transitions and correction-driven entry into `in_review`, and return the event history with the extraction result. Keep correction rows separate so value-level and state-level audits remain distinguishable.
- Alternatives considered: Infer history by diffing current result JSON was rejected because it loses actor and timestamp information. Reuse field correction rows for state events was rejected because it conflates two audit domains. Add a generic event bus was deferred as unnecessary dependency and operational scope.
- Consequences: Review state changes survive reloads and can be exported/inspected with the result contract. Existing records have no historical events before this migration, and tamper-evident external audit storage remains outside the current story; E10-04/E10-06 remain partial.
- Validation: The review API test now asserts actor/status events; the full backend suite passed 90 tests with 5 skipped and 3 warnings; the frontend build passed with 47 transformed modules; Python compilation and `git diff --check` passed; the Docker image rebuilt; the migration container exited successfully; `/health/ready` returned 200; and a live extraction transitioned to `approved` with one persisted `review_events` entry.
- Implementation references: `backend/app/models.py`, `backend/migrations/versions/0010_review_events.py`, `backend/app/main.py`, `backend/tests/test_extraction.py`, `docs/review-contract.md`.
## DD-079 — Enforce API-key scopes on document mutations

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E11-02, E7-02, E7-05
- Context: API keys carried read/render/admin scopes, but several document mutation routes only checked authentication conditionally or not at all. A read-only key must not upload, execute render work, or generate from approved data.
- Choice: Require the read scope for ingestion upload, extraction, local extraction, and extraction job execution; require the render scope for render job execution and approved-result rendering. Existing session users remain authorized through the local session boundary, and the empty-user bootstrap mode remains compatible for first startup.
- Alternatives considered: Require admin for every document route was rejected because it makes scoped integration keys unusable. Add client-only enforcement was rejected because authorization must be API-side. Remove API-key access from document routes was rejected because scoped API keys are a source requirement.
- Consequences: Read keys cannot perform render or document-generation actions, while render keys retain the intended integration path. Session role granularity and full UI login remain outside this slice; E11-02/E7-02 remain partial pending the broader automated security matrix.
- Validation: Scoped-key regression tests passed (3 tests with 3 warnings); the full backend suite passed 90 tests with 5 skipped and 3 warnings; the frontend build passed with 47 transformed modules; Python compilation and `git diff --check` passed; the Docker image rebuilt and migrations completed; `/health/ready` returned 200; and live OpenAPI still exposes the protected extraction and approved-render routes. Broader role granularity and a complete security certification remain unclaimed.
- Implementation references: `backend/app/main.py`, `backend/tests/test_auth.py`, `docs/auth-contract.md`, `docs/api-reference.md`, `frontend/src/storyStatus.ts`.
## DD-080 — Allow-listed extraction webhook delivery

- Date: 2026-09-24
- Status: Implemented; partial acceptance evidence
- Affected stories: E9-08, E7-05
- Context: Extraction results could be exported as JSON, CSV and XLSX, but the source story also requires webhook delivery. Arbitrary URL posting would create an SSRF and data-egress risk.
- Choice: Add an explicit `POST /api/extractions/{result_id}/webhook` action. The caller supplies an HTTP(S) destination only if its hostname is present in the configured `webhook_allowed_hosts` list; the request has a configurable timeout, a bounded JSON payload, and an optional HMAC-SHA256 signature header. The endpoint requires the read authorization boundary and reports the remote status without retrying.
- Alternatives considered: Permit any URL was rejected as an SSRF/data-egress vulnerability. Add a third-party delivery library was deferred because the one-shot contract needs no new dependency. Make webhook delivery automatic on approval was rejected because outbound publication requires an explicit action and policy.
- Consequences: Integrators can request a controlled webhook without weakening the local/offline default (the allow-list is empty by default). Retries, durable delivery jobs, response signing by provider, and delivery history remain pending; E9-08 remains partial.
- Validation: The mocked webhook/allow-list test passed as part of the 6-test E9/API focus; the full backend suite passed 91 tests with 5 skipped and 3 warnings; the frontend build passed with 47 transformed modules; Python compilation and `git diff --check` passed; the Docker image rebuilt and migrations completed; `/health/ready` returned 200; and live OpenAPI exposed the webhook route. No live external destination was contacted.
- Implementation references: `backend/app/main.py`, `backend/app/config.py`, `backend/tests/test_epic34.py`, `docs/extraction-contract.md`, `docs/api-reference.md`.
## DD-102: Close E9-02 on the deterministic bundled-sample contract

- **Date:** 2026-09-24
- **Status:** Accepted and implemented
- **Affected stories:** E9-02
- **Context:** E9-02 requires operators to start from bundled invoice, receipt and purchase-order schemas, with sample documents and expected output for each schema. The existing API and tests had already established these fixtures, but the story status remained partial because richer binary/OCR fixtures were not available.
- **Choice:** Treat the versioned offline PageModel sample plus independent expected normalized field/table output as the accepted local extraction starter contract. Keep the fixture deterministic and expose it through each schema's sample URL. Do not imply that the fixture is a native PDF/image, OCR corpus, or production accuracy benchmark.
- **Alternatives:** Keep the story partial until binary fixtures exist; rejected because binary/OCR coverage is not required by the stated acceptance criterion and would conflate E9-02 with later ingestion/rendering evidence. Generate expected output from the extractor; rejected because acceptance output must remain an independent comparison fixture.
- **Consequences:** All three schema starters are directly discoverable and testable offline. Browser sample launching, richer binary fixtures, OCR/layout coverage and independently labelled accuracy remain separate follow-up evidence.
- **Validation:** `backend/tests/test_extraction.py::test_extraction_schema_and_validation_errors_are_explicit` iterates every schema returned by `GET /api/extraction-schemas`, fetches its sample URL, verifies expected fields/tables, and round-trips the PageModel through `POST /api/extractions/local`. The full backend suite passed (`101 passed, 5 skipped, 3 warnings`); frontend build, Python compilation and `git diff --check` passed. No production extraction accuracy claim is made.
- **Implementation/evidence:** [bundled samples](../backend/app/extraction.py), [sample API](../backend/app/main.py), [contract test](../backend/tests/test_extraction.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).
## DD-103: Close bounded extraction schema, normalization and benchmark Must stories

- **Date:** 2026-09-24
- **Status:** Accepted and implemented
- **Affected stories:** E9-01, E9-06, E9-07, E9-09
- **Context:** These stories had working API/UI and benchmark slices but were still labelled partial because broader governance, locale and document-layout coverage was not complete.
- **Choice:** Mark each story implemented against its stated acceptance boundary: E9-01 has editable browser domain JSON plus JSON Schema projection/validation; E9-06 preserves originals while returning locale-aware normalized values; E9-07 returns line-item arrays and reports row/column metrics; E9-09 runs the benchmark both on demand and in CI with per-schema reports. Keep durable schema governance, full CLDR behavior, complex table layout, held-out accuracy and production calibration explicitly out of scope for these closures.
- **Alternatives:** Leave all four partial until every future extraction capability is complete; rejected because that would hide delivered acceptance evidence. Claim broad production extraction quality; rejected because the checked-in corpus is deterministic and bounded.
- **Consequences:** The project status page distinguishes delivered Must acceptance from remaining quality/evidence work. Consumers still need a labelled held-out corpus before using benchmark results as production accuracy or confidence calibration evidence.
- **Validation:** Schema projection/edit/validation, locale, table and benchmark tests passed in the backend suite (`101 passed, 5 skipped, 3 warnings`); frontend build passed; Python compilation and `git diff --check` passed. The CI workflow runs the benchmark and uploads its JSON artifact. No native OCR, full locale or production accuracy claim is made.
- **Implementation/evidence:** [schema API/editor](../backend/app/main.py), [extractor](../backend/app/extraction.py), [benchmark runner](../scripts/benchmark_extraction.py), [benchmark workflow](../.github/workflows/extraction-benchmark.yml), [tests](../backend/tests), [story status](../frontend/src/storyStatus.ts), [extraction contract](extraction-contract.md).
# DD-115 — Make local multi-page extraction observable through the durable job path

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; OCR/layout engine stories remain separate
- **Affected stories:** E8-05, E7-05, E12-01
- **Context:** Ingestion already counted pages and updated `pages_processed`, but the browser called extraction synchronously. A multi-page local extraction therefore exposed only its terminal state, which was insufficient evidence for E8-05's visible-progress acceptance criterion.
- **Choice:** Add an explicit asynchronous extraction mode to the existing durable `extraction` job contract. The browser uses this mode and polls both the job and ingestion record; the existing synchronous endpoint remains available for API compatibility. The worker persists one revisioned extraction result for the job and returns it with its PageModel.
- **Alternatives:** Keep synchronous extraction and show an indeterminate spinner; rejected because it does not expose page progress. Create a second progress store; rejected because the ingestion row already owns the authoritative bounded page counters. Replace the synchronous endpoint; rejected because it would break current API clients.
- **Consequences:** Multi-page local extraction now shows durable `processed/total` counters while the job runs and survives browser refreshes through the job and ingestion APIs. OCR/layout progress and provider-specific work remain outside this local contract; no OCR accuracy claim is made.
- **Validation:** Focused ingestion/job tests pass (`16 passed, 3 warnings`); the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); frontend build passes; and the live Playwright suite against `127.0.0.1:8001` passes (`14 passed`), including the multi-page `0/2` to `2/2 pages` workflow. `git diff --check` passes.
- **Implementation/evidence:** [ingestion/extraction routes](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [job tests](../backend/tests/test_jobs.py), [workspace UI](../frontend/src/main.tsx), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-117 — Carry PageModel page selection through review corrections

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E10-01 remains partial
- **Affected stories:** E10-01, E10-02, E8-07
- **Context:** The PageModel contract supports multiple pages, but the review UI always rendered page 1 and the add-field request defaulted to page 1. A reviewer could therefore inspect or draw on the wrong page for a multi-page result.
- **Choice:** Add local source-page navigation, include page number in active element selection and draft boxes, and resolve the selected page when posting a manual field. Keep element IDs and boxes in PageModel coordinates and preserve the existing revisioned API contract.
- **Alternatives:** Infer page from the selected element only; rejected because newly drawn boxes have no element. Add a global pixel canvas; rejected because it would discard per-page coordinate systems. Submit page 1 and rely on downstream correction; rejected because it creates incorrect provenance.
- **Consequences:** Reviewers can move through all returned PageModel pages and corrections retain the selected page number. PDF browser-native geometry and rotation-aware calibration remain outside the current evidence, so E10-01 remains partial.
- **Validation:** Frontend build and `git diff --check` pass; the full backend suite passes (`109 passed, 5 skipped, 3 warnings`); and the live Playwright suite against `127.0.0.1:8001` passes (`14 passed`), including navigation from Page 1 of 2 to Page 2 of 2 and back.
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [browser tests](../frontend/tests/foundation.spec.ts), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-129 - Close the bounded text-block editor formatting contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; final document-engine fidelity remains separate
- **Affected stories:** E2-01
- **Context:** The browser editor exposed text-block drag handles and controls for font, size, weight, colour and alignment, and the saved draft already sent those values to the isolated server renderer. The local preview did not reflect font family or size, and the browser contract only asserted bold formatting.
- **Choice:** Treat E2-01 as implemented for the source acceptance at the bounded editor/server-artifact layer. Make the local preview apply every supported text style, accept dropping a block onto the page surface, and verify that the same style values persist in the saved server artifact. Keep final PDF/Word pagination, embedded fonts, and native-reader fidelity in E4/E6 rather than silently extending this story.
- **Alternatives:** Keep the local preview approximate; rejected because it obscures a user-visible formatting mismatch. Add arbitrary CSS editing; rejected because the template contract has a fixed safe style allow-list. Mark E2-01 complete based only on UI controls; rejected because persisted server output must be asserted. Claim final document fidelity; rejected because the selected renderer remains a deterministic HTML candidate.
- **Consequences:** Owners see the selected text style consistently in the fast preview and the authoritative server preview, while drag-to-page has an explicit drop target. The contract remains bounded to supported styles and HTML candidate output; PDF/Word rendering and font embedding remain separate acceptance gates.
- **Validation:** The formatting browser test asserts local and server preview font family, size, weight, colour and alignment after saving, and a second browser test verifies dropping a block onto the page surface. Frontend `npm run build` passed; the clean validation Compose project on `127.0.0.1:8003` passed the full browser suite (`17 passed`); the full backend suite remains green (`110 passed, 5 skipped, 3 warnings`).
- **Implementation references:** `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`, `docs/template-contract.md`, `frontend/src/storyStatus.ts`.
# DD-130 - Close the bounded repeatable-table editor contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; final PDF pagination remains separate
- **Affected stories:** E2-02
- **Context:** The table block contract already constrained an array path, typed columns, row limits, escaping, and missing-value policy. The server candidate emitted semantic table sections, repeated-print-header CSS, and non-splitting row CSS, while the editor exposed insertion and column editing. Status remained partial because the evidence had not been tied directly to the story row-count/header behavior.
- **Choice:** Mark E2-02 implemented for the bounded editor/server-artifact acceptance: rendered row count follows the supplied data array, the semantic header is present, and the candidate artifact requests header repetition and row keep-together. Keep actual multi-page PDF pagination, native-reader behavior, and visual approval as separate E4/E6 gates.
- **Alternatives:** Claim multi-page PDF behavior from CSS alone; rejected because no PDF engine or native-reader evidence exists. Keep the story wholly partial; rejected because row cardinality and the print-header contract are directly executable and independently useful. Allow arbitrary table markup; rejected because it would weaken escaping, limits, and the template sandbox.
- **Consequences:** API-created and editor-created tables have one tested declarative contract with explicit data cardinality and print-layout hints. Final output pagination and reader fidelity remain unclaimed.
- **Validation:** The focused renderer test checks row count, ordering, escaping, formatting, and header-group CSS; the browser test checks two rendered data rows, the semantic header, and the header-repeat rule. The clean validation Compose project passed the full browser suite (`17 passed` before this assertion extension); the full backend suite remains green (`110 passed, 5 skipped, 3 warnings`).
- **Implementation references:** `backend/app/rendering.py`, `backend/tests/test_template_logic.py`, `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`, `docs/template-contract.md`, `frontend/src/storyStatus.ts`.
# DD-131 - Close the bounded image and logo editor contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; final PDF embedding remains separate
- **Affected stories:** E2-03
- **Context:** The renderer and asset API already supported base64 image data, stored asset references, bound data paths, and explicitly allow-listed external URLs. The editor exposed image insertion and upload, but the browser suite did not prove the upload-to-server-preview path, so the story remained partial alongside the unresolved final-output engine work.
- **Choice:** Mark E2-03 implemented for the bounded template/editor contract: upload signature-checked image bytes through the asset API, bind the returned local asset URL to an image block, and render that asset in the authoritative server HTML preview. Preserve the default no-egress rule and exact external-host opt-in. Keep PDF embedding, image decoding/virus-policy breadth, and native-reader output evidence under E6/E11.
- **Alternatives:** Fetch arbitrary URLs in the worker; rejected because it violates network isolation and creates SSRF risk. Store image bytes inside template JSON; rejected because it bypasses shared object limits and duplicates binary data. Claim final document support from an HTML `<img>` tag; rejected because PDF embedding and reader validation are separate acceptance gates.
- **Consequences:** Owners can upload and reuse bounded image assets from the editor, while API and renderer behavior remains offline by default and storage-backed. The status closure does not claim final PDF/Word embedding or broad malicious-image containment.
- **Validation:** Existing renderer/API tests cover base64, local asset, bound-field and explicit URL behavior; the new browser test uploads a PNG, saves a draft, and asserts a local asset image in the server preview. The focused renderer suite passes (`20 passed, 3 warnings`); the clean validation Compose UI suite passes (`18 passed`); the full backend baseline remains `110 passed, 5 skipped, 3 warnings`.
- **Implementation references:** `backend/app/main.py`, `backend/app/rendering.py`, `backend/tests/test_template_logic.py`, `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`, `docs/template-contract.md`, `frontend/src/storyStatus.ts`.
# DD-132 - Close the bounded visual loop and conditional-block contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; pagination and accessibility remain separate
- **Affected stories:** E2-05, E5-02, E5-03
- **Context:** The editor exposes repeating-section and conditional-block controls, maps them to the existing bounded declarative evaluator, and seeds sample data for both loop rows and the enabled branch. Backend and browser tests already verified repeated output and if/else behavior, but E2-05 remained partial because it was grouped with later nested composition and final-output concerns.
- **Choice:** Mark E2-05 implemented for its stated bounded visual-editor behavior: owners can add a repeating section and a conditional block, configure their paths/text, save a version, and observe the expected loop/branch output in the server preview. Keep nested composition, final pagination, and full keyboard/accessibility certification outside this closure.
- **Alternatives:** Keep logic JSON-only; rejected because it fails the visual-editor acceptance. Add a second UI expression language; rejected because it could diverge from the tested E5 grammar. Claim arbitrary nested layout/accessibility from these controls; rejected because those require separate evidence.
- **Consequences:** The editor-to-render path is directly usable for bounded loops and if/else blocks, with one sandboxed evaluator shared by API and UI. Empty-state, nested-composition breadth, final PDF pagination, and WCAG certification remain separate gates.
- **Validation:** The focused template logic test verifies repeated values and the selected conditional branch; the clean validation Compose browser suite passes (`18 passed`), including the visual loop/conditional workflow; the full backend baseline remains `110 passed, 5 skipped, 3 warnings`.
- **Implementation references:** `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`, `backend/app/template_logic.py`, `backend/tests/test_template_logic.py`, `docs/template-contract.md`, `frontend/src/storyStatus.ts`.
# DD-133 - Close the bounded page-settings editor contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; final pagination remains separate
- **Affected stories:** E2-06
- **Context:** The editor stores allow-listed page size, orientation, margins, headers, footers, and page-number settings in draft definitions. The isolated server renderer emits the corresponding `@page`, fixed document chrome, and CSS page-counter markup, and browser/backend tests already exercised the flow. The story remained partial because final PDF pagination was not available.
- **Choice:** Mark E2-06 implemented for the bounded definition/server-preview contract: settings persist in a draft and are reflected in the authoritative HTML preview with fixed headers/footers and page-number instructions. Keep actual multi-page PDF application, orphan handling, native-reader fidelity, and accessibility outside this closure.
- **Alternatives:** Keep settings browser-only; rejected because saved output would diverge. Claim PDF pagination from HTML CSS; rejected because no final engine/native-reader evidence exists. Accept arbitrary CSS; rejected because it weakens the safe template contract.
- **Consequences:** Owners and API consumers have one validated page-settings representation and can inspect its server-preview effect. Final PDF pagination and reader-specific behavior remain explicit gaps.
- **Validation:** Backend page-setting tests cover valid values and invalid-size rejection; the clean UI suite passed `18` tests including the Letter-landscape/header/footer/page-number flow; frontend build passed; primary readiness remains healthy.
- **Implementation references:** `backend/app/rendering.py`, `backend/tests/test_template_logic.py`, `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`, `docs/template-contract.md`, `frontend/src/storyStatus.ts`.
# DD-134 — Extend the deterministic script contract to Korean

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-05 and E4-08 remain partial
- **Affected stories:** E4-05, E4-08, E14-03
- **Context:** The source acceptance for E4-05 includes Chinese, Japanese, Korean and Thai, while the renderer's deterministic script report and CI matrix covered Korean only as an unreported planned family.
- **Choice:** Add Hangul syllable and jamo range detection, a Korean fallback-stack diagnostic, and Korean text to the offline rendering spike and CI assertion. Keep the result explicitly diagnostic: no claim is made about Korean line-breaking rules, font coverage, shaping, PDF output or native-reader approval.
- **Alternatives:** Treat Korean as covered by the generic CJK family; rejected because Korean has a distinct fallback stack and line-breaking requirements. Mark E4-05 complete from Unicode detection; rejected because detection does not prove line layout. Wait for the final PDF engine; rejected because the deterministic matrix can safely expose the missing contract family now.
- **Consequences:** The public offline matrix now reports all source-required E4-05 script families, and future changes fail the deterministic CI assertion if Korean disappears. Native fonts, language-aware line breaking, visual baselines and native-reader review remain required before E4-05/E4-08 can close.
- **Validation:** `backend\\.venv\\Scripts\\python.exe scripts/render_spike.py` reports `korean`; the E4 contract test and generated matrix comparison pass; no story status is promoted.
- **Implementation/evidence:** [renderer](../backend/app/rendering.py), [spike](../scripts/render_spike.py), [matrix](script-test-matrix.md), [CI workflow](../.github/workflows/script-matrix.yml), [tests](../backend/tests/test_epic34.py).
# DD-135 — Exercise all code-block editor variants in the browser contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-04 remains partial
- **Affected stories:** E2-04
- **Context:** The editor and server renderer already exposed QR, Code 128 and EAN-13 controls, but browser coverage only existed for the lower-level SVG generator. The source story requires all three types to be owner-configurable and bound to values.
- **Choice:** Add one browser contract that creates a code block, configures each supported type and bound/sample value, saves the draft, and asserts the corresponding SVG appears in the authoritative server preview. Keep scanning and final-PDF embedding outside this test.
- **Alternatives:** Mark E2-04 complete from unit-generated SVG strings; rejected because it skips the owner-facing control path. Add a scanner dependency to the browser suite; deferred because dependency licensing and a raster/PDF scanning fixture require separate review. Treat SVG presence as scanner proof; rejected because renderability is weaker than machine-read acceptance.
- **Consequences:** Regressions in the editor-to-template mapping for any of the three code types are caught in the UI suite. E2-04 remains partial until QR/Code 128/EAN-13 scan fixtures and final output evidence are available.
- **Validation:** Added `editor configures QR, Code 128, and EAN-13 blocks in the server preview` to [browser tests](../frontend/tests/foundation.spec.ts); existing code-generator tests remain green. No story status promotion is made.
- **Implementation/evidence:** [editor controls](../frontend/src/main.tsx), [code renderer](../backend/app/codes.py), [browser test](../frontend/tests/foundation.spec.ts), [story status](../frontend/src/storyStatus.ts).
# DD-136 — Verify real-child output containment and recovery

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 and E11-04 remain partial
- **Affected stories:** E12-02, E11-04, E7-04
- **Context:** The isolated worker had a portable serialized-output guard, but its existing regression test replaced the child process with a mock. That proved supervisor branching but not that a real render child can be rejected without poisoning the next job.
- **Choice:** Add a real-child test that renders a bounded but oversized result, asserts the output-limit failure, then starts a second isolated render and asserts successful completion. Keep wall-time, CPU, memory, hostile-parser and deployment-cgroup evidence separate.
- **Alternatives:** Increase the output limit until the fixture passes; rejected because the limit is an operational containment boundary. Mark E12-02 complete from this test; rejected because output containment is only one of the source's CPU/memory/runtime requirements. Test only mocked process methods; rejected because it cannot catch child serialization or process-start regressions.
- **Consequences:** A real oversized render cannot silently turn the next isolated job into a failure, and the evidence now covers the serialized-output boundary end to end. Full resource-exhaustion, Windows/native deployment parity and hostile parser containment remain open.
- **Validation:** `backend\\.venv\\Scripts\\python.exe -m pytest -q tests/test_jobs.py` passes with the new real-child case; existing full-suite and live validation remain the broader gates.
- **Implementation/evidence:** [worker supervisor](../backend/app/worker.py), [worker child](../backend/app/worker_child.py), [jobs tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-137 — Add an offline Chromium PDF candidate harness

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-01, E6-01, E6-03 and E6-04 remain partial/planned
- **Affected stories:** E4-01, E6-01, E6-03, E6-04, E6-05
- **Context:** The platform had a deterministic HTML candidate and a proposed Chromium-versus-WeasyPrint comparison, but no repeatable way to print the exact server artifact through the already pinned browser-test dependency. Selecting a PDF engine before the rendering spike and licence review would exceed the evidence.
- **Choice:** Add a development-only Node harness that reads local HTML, aborts all browser requests, prints with the pinned Playwright Chromium package, and emits a manifest with browser version and explicit pending font/native-reader fields. Keep it outside the production API and story status map.
- **Alternatives:** Make Chromium the production renderer immediately; rejected because E4-01 requires comparison and native-reader grading. Add a Python PDF dependency now; rejected because its licence and rendering behavior remain unreviewed. Allow remote assets during printing; rejected because candidate evidence must preserve the renderer's network-disabled boundary.
- **Consequences:** The fixed server artifact can now be captured as a reproducible Chromium PDF candidate for later comparison. The harness does not prove embedded fonts, metadata, pagination, Word conversion, accessibility, or native-reader compatibility.
- **Validation:** The harness was run against a local HTML fixture and produced a PDF plus manifest with network disabled; frontend dependency version is pinned at Playwright 1.63.0. E4/E6 status is deliberately unchanged.
- **Implementation/evidence:** [candidate harness](../scripts/render_chromium_candidate.mjs), [candidate evidence guide](rendering-candidates.md), [renderer contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-138 — Carry bounded document metadata through the candidate render

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E6-04 remains partial
- **Affected stories:** E6-04, E6-05, E4-01
- **Context:** The candidate artifact already exposed the render locale through HTML `lang`, but title and author were not represented in the server contract or the provisional Chromium manifest. Final PDF metadata cannot be claimed until an engine output is parsed.
- **Choice:** Accept optional bounded `metadata.title` and `metadata.author` strings, emit escaped HTML title/author metadata, expose title/author/language in the render result, and have the offline Chromium harness record the same values. Reject non-string metadata and cap each field at 200 characters.
- **Alternatives:** Set metadata only in the PDF harness; rejected because the server render contract must carry the source values. Claim PDF metadata from HTML tags; rejected because a browser candidate may transform or omit fields. Accept arbitrary metadata keys; rejected because unbounded output and engine-specific semantics would weaken the contract.
- **Consequences:** Candidate engines have explicit metadata inputs and a manifest comparison point. Final PDF metadata preservation, language tagging across readers, and native-reader evidence remain open; E6-04 is not promoted to implemented.
- **Validation:** Metadata regression tests pass; the Chromium candidate harness records source title/author/locale and observed PDF metadata from a local artifact. The current fixture preserves `/Title` but emits no `/Author` or `/Lang`, so E6-04 remains partial; full backend and frontend validation remains green.
- **Implementation/evidence:** [renderer](../backend/app/rendering.py), [metadata tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [Chromium harness](../scripts/render_chromium_candidate.mjs), [story status](../frontend/src/storyStatus.ts).
# DD-139 — Give editor text entry locale and automatic direction hints

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-08 and E2-09 remain partial
- **Affected stories:** E2-08, E2-09, E4-04
- **Context:** Server previews and local page paragraphs already used automatic direction, but the editable textareas did not expose the selected preview locale or a bidirectional hint to the browser's native text input behavior.
- **Choice:** Set each editor text block textarea's `lang` to the selected preview locale and `dir` to `auto`. Add a browser contract that switches to Arabic, verifies both attributes, enters Arabic text, and selects it.
- **Alternatives:** Force RTL for every non-Latin locale; rejected because Indic, Thai, Chinese and Japanese are not uniformly RTL. Set direction from the first character in application code; rejected because the browser's native bidirectional editing behavior should remain authoritative. Claim IME/caret correctness from attribute checks; rejected because composition, caret movement and native input-method coverage remain separate evidence.
- **Consequences:** Browsers receive the correct locale context and can resolve paragraph direction while users edit mixed-script text. This does not establish shaping, line breaking, IME composition, caret semantics, copy/paste fidelity or final-render parity.
- **Validation:** The new browser contract verifies Arabic `lang`, `dir`, text entry and selection; frontend build and the existing multilingual suite remain required gates.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [browser tests](../frontend/tests/foundation.spec.ts), [story status](../frontend/src/storyStatus.ts).
# DD-140 — Compare the HTML and Chromium candidates on a fixed corpus

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-01 and E6-01 remain partial/planned
- **Affected stories:** E4-01, E4-08, E6-01, E6-04, E6-05
- **Context:** The repository had separate deterministic-render and Chromium-print commands, but no fixed-corpus report tying their outputs and environment records together. A candidate hash is useful for reproducibility but is not a visual or native-reader grade.
- **Choice:** Add an offline comparison command with two fixed fixtures covering scripts, page flow, tables, metadata and locale. Record deterministic HTML and Chromium PDF SHA-256 hashes, candidate manifests, detected scripts, environment versions, and explicit null visual/native-review fields. Abort browser network requests through the existing harness.
- **Alternatives:** Compare only file sizes; rejected because size does not establish content or layout equivalence. Automatically choose Chromium from the hashes; rejected because engine selection requires visual comparison, licence review and native-reader grading. Add screenshot approval in CI now; deferred until a font corpus and native-reviewed baseline exist.
- **Consequences:** E4-01 now has a repeatable two-candidate evidence scaffold and future changes can identify artifact drift. The report does not claim visual fidelity, embedded fonts, metadata parity, pagination, accessibility or native-reader approval.
- **Validation:** The fixed-corpus command produced two deterministic HTML/Chromium PDF result pairs and environment manifests with browser network disabled; syntax, backend, frontend and readiness checks remain green.
- **Implementation/evidence:** [comparison command](../scripts/compare_render_candidates.py), [Chromium harness](../scripts/render_chromium_candidate.mjs), [candidate guide](rendering-candidates.md), [story status](../frontend/src/storyStatus.ts).
# DD-141 — Expose bounded document metadata in the editor

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E6-04 remains partial
- **Affected stories:** E6-04, E2-06
- **Context:** The renderer accepted bounded title and author metadata, but the workspace could only set page chrome and locale. Owners had no UI path to persist the metadata used by candidate outputs.
- **Choice:** Add document-title and document-author controls to the existing page-settings panel, load them from the stored definition, persist them with the draft, and assert the saved server preview exposes escaped title/author metadata.
- **Alternatives:** Derive author from the logged-in user; rejected because document authorship is a document property and the current local identity is not required for rendering. Expose arbitrary metadata JSON; rejected because the candidate contract intentionally allow-lists only bounded title and author. Claim final PDF metadata from the UI; rejected because Chromium evidence shows author/language loss during PDF conversion.
- **Consequences:** Template owners can configure the metadata inputs through the same draft workflow and API definition used by candidate rendering. Final PDF Info/catalog preservation remains an E6-04 gap.
- **Validation:** The page-settings browser flow now verifies title and author in the server preview; frontend build and the existing backend metadata tests remain green.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [translations](../frontend/src/i18n.ts), [browser test](../frontend/tests/foundation.spec.ts), [metadata contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-142 — Preserve candidate PDF metadata with an explicit incremental patch

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E6-04 remains partial and E6-01 remains planned
- **Affected stories:** E6-04, E6-05, E4-01
- **Context:** Chromium's native PDF output preserved the document title but omitted HTML author and language metadata. No system PDF metadata tool is installed and adding an unreviewed dependency would conflict with the current engine/licence gate.
- **Choice:** Apply a small dependency-free incremental PDF update in the development-only candidate harness. Add UTF-16BE `/Title` and `/Author` entries to a new Info object and `/Lang` to a new Catalog object, preserve the prior xref through `/Prev`, validate the required structural markers, and label the manifest as candidate-only.
- **Alternatives:** Claim HTML metadata proves PDF metadata; rejected by the observed Chromium output. Add pypdf/qpdf immediately; deferred pending dependency/licence review and a selected production engine. Rewrite the entire PDF; rejected because incremental updates preserve the browser-produced bytes and reduce corruption risk.
- **Consequences:** The provisional candidate manifest now observes all three requested metadata values while retaining the raw Chromium output plus an explicit transformation record. This is not proof of Acrobat/Preview acceptance, PDF/A compliance, or production-engine safety; E6-04 remains partial.
- **Validation:** The harness produced fixed-corpus PDFs whose manifests observe title, author and language after the incremental patch; Node syntax checks and candidate comparison pass. Native-reader validation remains pending.
- **Implementation/evidence:** [candidate harness](../scripts/render_chromium_candidate.mjs), [comparison command](../scripts/compare_render_candidates.py), [candidate guide](rendering-candidates.md), [story status](../frontend/src/storyStatus.ts).
# DD-143 — Measure bounded CPU candidate paths without inventing hardware minima

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E1-06 remains partial
- **Affected stories:** E1-06, E8-05, E9-03
- **Context:** The platform already had a deterministic HTML candidate renderer and an offline local label extractor, but CPU execution evidence was limited to service smoke tests. The source acceptance also requires rendering and extraction work without a GPU, while the actual PDF, layout and OCR engines remain unresolved.
- **Choice:** Add a dependency-free benchmark command that measures repeated deterministic-render and local-extraction operations on the current host, records interpreter/CPU metadata and serialized result sizes, and explicitly lists excluded engines and the absence of a derived hardware minimum. Keep the report as candidate-path evidence and do not use the fixture to set production latency, capacity or OCR claims.
- **Alternatives:** Claim E1-06 from the CPU-only container definition; rejected because that does not exercise document processing. Derive minimum hardware from this small fixture; rejected because it would be an unsupported sizing promise. Add Docling/PaddleOCR solely for the benchmark; rejected because their versions, models, licences and CPU behavior are not yet reviewed.
- **Consequences:** Operators have a repeatable local command for collecting initial CPU evidence, and later engine-specific results have a documented place to compare against. E1-06 remains partial until actual rendering/OCR paths, realistic corpora, memory limits and minimum hardware are measured.
- **Validation:** `backend\\.venv\\Scripts\\python.exe scripts\\benchmark_cpu_pipeline.py --iterations 3` completed on the current host and wrote `artifacts/cpu-pipeline-benchmark.json`; Python compilation and the focused extraction/render tests pass. No PDF-engine, OCR, native-reader or minimum-hardware acceptance is claimed.
- **Validation update (2026-09-25):** The benchmark was rerun with 5 iterations on Windows 11 (`Python 3.13.7`, Intel64 Family 6 Model 142, 8 logical CPUs). The artifact records deterministic HTML render median `0.5619 ms` and local-label extraction median `0.3484 ms`; these are candidate-path observations only and do not derive minimum hardware or OCR/PDF capacity.
- **Implementation/evidence:** [CPU benchmark](../scripts/benchmark_cpu_pipeline.py), [E1 guidance](e1-foundation.md), [implementation plan](implementation-plan.md), [rendering code](../backend/app/rendering.py), [extraction code](../backend/app/extraction.py).
# DD-144 — Recognize bounded hexadecimal PDF text during ingestion routing

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-02 remains partial
- **Affected stories:** E8-02, E8-06
- **Context:** The dependency-free PDF route detector recognized only parenthesized `Tj` operands. Valid simple PDFs using hexadecimal text operands were therefore sent to the scan route, even though they contained directly extractable text.
- **Choice:** Recognize simple uncompressed hexadecimal `Tj` operands alongside parenthesized operands, decode basic Latin/UTF-16BE text when possible, and preserve the same bounded synthetic PageModel boxes. Keep compressed streams, complex layout and OCR outside this parser.
- **Alternatives:** Route every PDF to the digital path; rejected because it would skip OCR for scans. Add a full PDF parser immediately; deferred until parser dependency, licence and hostile-input review are complete. Decode arbitrary PDF font encodings in the contract parser; rejected because fabricated text/provenance would be unsafe.
- **Consequences:** A wider but explicit class of text PDFs now skips the scan route and retains source-linked text. E8-02 is not complete: compressed/complex PDFs and scan OCR still require isolated engines.
- **Validation:** The new hexadecimal-text ingestion test and the existing extraction/ingestion contract tests pass. No OCR, compressed-stream, layout or native-PDF claim is made.
- **Implementation/evidence:** [ingestion classifier](../backend/app/ingestion.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-145 — Keep fixed rendering fixtures Unicode-authentic

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-01, E4-05 and E4-08 remain partial
- **Affected stories:** E4-01, E4-05, E4-08, E6-05
- **Context:** The fixed-corpus candidate comparison was intended to cover Arabic, Hebrew, Devanagari, Tamil, Thai, Chinese, Japanese and Korean, but its source fixture contained mojibake. The comparison therefore did not exercise the required script characters even though its detected-script assertions appeared plausible.
- **Choice:** Store the fixed fixture with explicit Unicode escape sequences in the Python source, regenerate both deterministic HTML and Chromium candidate artifacts, and require the report to list all seven required script families plus Korean. Keep visual/native-reader fields pending.
- **Alternatives:** Accept the existing fixture because its labels listed the scripts; rejected because labels and detected families are not proof of correct source characters. Add a lossy normalization step; rejected because it could hide encoding defects. Mark multilingual rendering complete from script detection; rejected because shaping, fonts, line breaking and reader review remain separate gates.
- **Consequences:** Candidate comparisons now exercise the intended code points deterministically and make encoding corruption visible in the generated artifact. The comparison remains diagnostic and does not establish visual or native-reader correctness.
- **Validation:** The fixed-corpus comparison regenerated successfully; the `script-matrix` result reports `arabic`, `cjk`, `devanagari`, `hebrew`, `korean`, `tamil` and `thai`. Native-reader and visual review fields remain null.
- **Implementation/evidence:** [comparison command](../scripts/compare_render_candidates.py), [candidate evidence](rendering-candidates.md), [rendering diagnostics](../backend/app/rendering.py), [script matrix](script-test-matrix.md).
# DD-146 — Record deterministic Chromium visual baselines without approving them

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-01 and E4-08 remain partial
- **Affected stories:** E4-01, E4-08, E6-01, E6-05
- **Context:** The fixed-corpus comparison recorded HTML/PDF hashes but no image artifact. That made repeated candidate output reproducible, but did not leave a concrete visual baseline for later review.
- **Choice:** Extend the offline Chromium candidate harness to emit an optional full-page PNG and record its SHA-256 per fixture. Add a `visual_baseline` section that states the method and that human review has not occurred; retain `visual_comparison` and native-reader scores as null.
- **Alternatives:** Treat PNG hashes as visual approval; rejected because a hash does not establish layout correctness or accessibility. Compare only PDF byte hashes; rejected because different valid PDFs can render identically and byte changes do not reveal visual changes. Automatically approve the baseline in CI; rejected because the source requires reviewed visual regression and native-reader evidence.
- **Consequences:** Future runs can detect deterministic candidate-image changes and reviewers have concrete PNG artifacts to inspect. The production renderer, font embedding, visual approval and native-reader gates remain open.
- **Validation:** The fixed-corpus command generated PNG/PDF/HTML artifacts and recorded SHA-256 values for both fixtures; `node --check`, Python compilation, rendering tests and focused lint passed.
- **Implementation/evidence:** [Chromium harness](../scripts/render_chromium_candidate.mjs), [comparison command](../scripts/compare_render_candidates.py), [candidate contract](rendering-candidates.md), [fixed-corpus report](../artifacts/render-candidate-comparison.json).
# DD-147 — Exercise confidence calibration with a labelled failure case

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E9-04 remains partial
- **Affected stories:** E9-04, E9-09, E10-03
- **Context:** The extraction benchmark calculated calibration metrics, but its checked-in fixture contained only successful predictions. That verified report shape but did not exercise a failed-rule/low-confidence outcome.
- **Choice:** Add a deterministic invoice record whose observed total conflicts with the labelled expected total and line-item sum. Keep the expected values explicit, let the extractor produce its normal validation/confidence response, and assert both the low-confidence and high-confidence reliability bins.
- **Alternatives:** Change confidence values to force a calibration spread; rejected because benchmark labels must measure the extractor rather than manufacture scores. Call the small fixture calibrated; rejected because it is not held out or representative. Omit failure cases until a customer corpus exists; rejected because the benchmark contract can safely verify failure accounting now.
- **Consequences:** The benchmark now demonstrates how incorrect/failed-rule fields appear in calibration metrics and supports review prioritization testing. E9-04 remains partial until a representative held-out labelled corpus and calibration decision exist.
- **Validation:** `backend\\.venv\\Scripts\\python.exe -m pytest -q tests\\test_benchmark.py` passes with four labelled records, invoice accuracy `0.75`, and populated 0.35/0.90 reliability bins; the benchmark script remains offline and deterministic.
- **Implementation/evidence:** [benchmark fixture](../backend/tests/fixtures/extraction_benchmark.jsonl), [benchmark tests](../backend/tests/test_benchmark.py), [benchmark command](../scripts/benchmark_extraction.py), [extraction contract](extraction-contract.md).
# DD-148 — Bound declared raster pixels before ingestion storage

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 and E8-02 remain partial
- **Affected stories:** E11-04, E8-01, E8-02
- **Context:** Ingestion already bounded upload bytes and page count, and read raster dimensions for the PageModel, but a small encoded image could declare an excessive pixel surface for downstream decoders.
- **Choice:** Add the configurable `max_image_pixels` setting, defaulting to 100,000,000, and reject PNG/JPEG/TIFF ingestion or uploaded assets whose declared dimensions exceed it before object storage or downstream processing. Keep byte, page and optional virus-scan checks in place.
- **Alternatives:** Use encoded byte size as the only image limit; rejected because compression ratios can make decoded memory much larger. Reject all raster images; rejected because raster ingestion is a source Must story. Claim decoder safety from header validation; rejected because full parser/OCR sandbox testing remains separate.
- **Consequences:** The local upload boundary has an explicit decompression/pixel-expansion guard and is configurable through TOML/environment settings. E11-04 remains partial pending hostile parser cases, full process isolation evidence and deployment sandbox review.
- **Validation:** Added a regression that rejects an 11×10 PNG under a 100-pixel limit before storage; focused ingestion tests and configuration validation pass.
- **Implementation/evidence:** [settings](../backend/app/config.py), [ingestion route](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [contract](ingestion-contract.md), [foundation configuration](e1-foundation.md).
# DD-149 — Decode bounded Flate PDF text streams for routing

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-02 remains partial
- **Affected stories:** E8-02, E8-06, E11-04
- **Context:** The ingestion contract recognized direct PDF text and hex operands, but common PDFs place those operators in FlateDecode content streams. Treating every compressed PDF as a scan caused avoidable OCR routing and lost the bounded digital PageModel path.
- **Choice:** Inspect only explicitly marked `/Filter /FlateDecode` streams, cap compressed input at 1 MiB per stream and decompressed output at 4 MiB per stream/16 MiB total, then apply the existing simple text-operand extraction to the inflated bytes. Invalid or over-limit streams are ignored and do not make the upload fail open into fabricated text.
- **Alternatives:** Inflate without bounds; rejected because PDF decompression bombs are untrusted input. Use a complete PDF parser immediately; deferred pending dependency/licence and hostile-input review. Route all PDFs to digital when a filter is present; rejected because it would misroute image-only documents.
- **Consequences:** Common bounded compressed text PDFs can skip OCR and retain source-linked PageModel text. Unsupported filters, font encodings, layout and scans remain explicit gaps; the code is not a general PDF parser.
- **Validation:** Added compressed-stream regressions using zlib, including an over-limit 4,000,001-byte expansion that is not returned as an extraction source; the focused ingestion suite passes, including direct, hexadecimal and bounded Flate text routing, with no external calls.
- **Implementation/evidence:** [bounded PDF ingestion](../backend/app/ingestion.py), [ingestion tests](../backend/tests/test_ingestion.py), [contract](ingestion-contract.md), [security boundary](../backend/app/main.py).
# DD-150 — Verify upload scanner rejection before object persistence

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E8-01
- **Context:** The optional scanner helper had unit coverage for clean, rejected and timed-out commands, but no API regression proved that a configured rejection happens before the ingestion object is persisted.
- **Choice:** Add an API-level test with a shell-free Python scanner command that exits nonzero, assert the documented 422 response, and assert the configured object store remains empty. Keep scanner output hidden and retain the existing temporary-file cleanup path.
- **Alternatives:** Rely only on the helper unit test; rejected because route ordering could still store before scanning. Return scanner output to operators; rejected because untrusted tool output can disclose data. Make scanning mandatory by default; deferred because deployment-specific scanner availability is not yet selected.
- **Consequences:** The ingestion boundary now has evidence for scanner-before-storage ordering. Full malware-engine effectiveness, parser isolation and production sandbox review remain open.
- **Validation:** The API scanner rejection regression passes with the focused ingestion suite; the scanner runs without a shell and no object is persisted.
- **Implementation/evidence:** [scanner](../backend/app/security.py), [ingestion route](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [contract](ingestion-contract.md).
# DD-151 — Exercise every required script family in the editor browser contract

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-09 remains partial
- **Affected stories:** E2-09, E2-08, E4-04, E4-05
- **Context:** The editor browser test exercised Arabic, Devanagari, Thai, Chinese and Japanese, while the source Must acceptance also names Hebrew, Tamil and CJK/Korean coverage. The test therefore did not cover every required family through the actual textarea-to-server-preview path.
- **Choice:** Expand the live Playwright text-entry fixture to one string containing Arabic, Hebrew, Devanagari, Tamil, Thai, Chinese, Japanese and Korean, assert the value survives the textarea and server preview, and keep the separate Arabic direction/locale assertion. Treat this as browser text round-trip evidence, not IME or shaping approval.
- **Alternatives:** Claim the missing families from the offline script matrix; rejected because editor input is a separate acceptance surface. Add synthetic DOM values without saving/previewing; rejected because the server round trip is part of the current contract. Claim IME/caret correctness from Playwright fill; rejected because native composition and platform caret behavior need dedicated manual/native tests.
- **Consequences:** The browser contract now exercises all named editor script families in one persisted preview path. E2-09 remains partial for real IME composition, caret/selection semantics across target platforms and final output shaping.
- **Validation:** The expanded Playwright test is included in the frontend suite; frontend build and live browser execution remain required gates. No accessibility, IME or native-reader certification is claimed.
- **Implementation/evidence:** [browser test](../frontend/tests/foundation.spec.ts), [editor](../frontend/src/main.tsx), [rendering matrix](script-test-matrix.md), [story status](../frontend/src/storyStatus.ts).
# DD-152 — Expose the remaining script preview locale controls

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-08 and E2-09 remain partial
- **Affected stories:** E2-08, E2-09, E4-04, E4-05
- **Context:** The editor preview selector covered English, German, Arabic, Hindi, Thai, Chinese and Japanese, while the required script matrix also includes Hebrew, Tamil and Korean. Those locale values were supported by the server contract but not selectable in the UI.
- **Choice:** Add localized Hebrew, Tamil and Korean supplemental locale buttons beside the editor controls. Each button changes the same `previewLocale` state used by the authoritative server preview and is verified through the resulting HTML `lang` attribute.
- **Alternatives:** Add separate preview state for the new locales; rejected because it would create parity drift. Add hard-coded labels; rejected because the interface must use the i18n resource. Claim all script support from renderer detection; rejected because UI locale selection is a separate contract.
- **Consequences:** Owners can request all script-family locale contexts from the editor without changing the persisted template locale. Full CLDR semantics, shaping, fonts, line breaking and native-reader parity remain open.
- **Validation:** The live Playwright locale test cycles Hebrew (`he`), Tamil (`ta`) and Korean (`ko`) through save/server preview; frontend build passes. No multilingual correctness or IME certification is claimed.
- **Implementation/evidence:** [editor controls](../frontend/src/main.tsx), [i18n resources](../frontend/src/i18n.ts), [browser test](../frontend/tests/foundation.spec.ts), [template contract](template-contract.md).

# DD-168 — Add an explicit offline confidence-calibration profile

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E9-04 remains partial
- **Affected stories:** E9-04, E9-09, E10-03
- **Context:** The local extractor already emitted bounded confidence values and the benchmark reported reliability bins, Brier score and absolute calibration error. There was no reusable, validated calibration artifact, so applying a score transformation would have required undocumented ad hoc logic. The checked-in fixture is intentionally too small to establish production calibration.
- **Choice:** Add a data-only `confidence-calibration-v1` profile using monotone isotonic mappings. Provide an offline builder that consumes an explicitly supplied labelled calibration JSONL corpus, validate every mapping before use, preserve each field's `raw_confidence`, and apply calibration only when the caller supplies the profile. Support scalar fields and table columns for synchronous, persisted, and durable extraction paths.
- **Alternatives:** Calibrate automatically from every extraction request; rejected because it leaks evaluation data and makes scores unstable. Apply a fixed hand-tuned multiplier; rejected because it is not evidence-backed calibration. Treat benchmark reliability bins as calibrated scores; rejected because reporting error is not a transformation or a held-out calibration policy. Add a numerical dependency; deferred because the bounded PAVA implementation is sufficient and avoids a new licence/runtime surface.
- **Consequences:** Operators have a reproducible, offline path from labelled calibration data to bounded score mappings, and consumers can distinguish raw from calibrated confidence. The profile is opt-in, not a claim that the repository fixture is representative; E9-04 remains partial until a reviewed calibration corpus, calibration split and acceptance thresholds are supplied. Invalid profiles fail before extraction results are returned.
- **Validation:** Added calibration-module validation/interpolation tests, benchmark profile-generation tests, API tests for application and rejection of profiles, and documentation of the separate-corpus requirement. `tests/test_benchmark.py tests/test_extraction.py` passed (`13 passed`), the new calibration files pass Ruff, and the rebuilt Compose service reports ready on `127.0.0.1:8001`; no production calibration claim is made.
- **Implementation/evidence:** [calibration contract](../backend/app/calibration.py), [profile builder](../scripts/calibrate_extraction.py), [API integration](../backend/app/main.py), [tests](../backend/tests/test_benchmark.py), [extraction tests](../backend/tests/test_extraction.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-169 — Decode bounded PDF name escapes in the active-content gate

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E8-01, E8-02
- **Context:** The PDF upload gate rejected common active-content names in their ordinary spelling and inside bounded FlateDecode streams, but PDF names can encode bytes as `#XX` escapes. A lexical gate that checked only the visible spelling could therefore miss common action names such as `/Java#53cript`.
- **Choice:** Normalize bounded PDF name tokens by decoding hexadecimal name escapes before applying the existing active-content allow-list. Keep the scan bounded and preserve the original accepted artifact; malformed/obfuscated names, arbitrary filters, image decoder behavior, malware detection and parser containment remain responsibilities of the optional scanner and isolated downstream workers.
- **Alternatives:** Reject every PDF containing `#`; rejected because escaped names are valid in benign PDFs and would cause unnecessary denial. Decode and rewrite the stored PDF; rejected because source bytes and provenance must remain unchanged. Add a full PDF parser immediately; deferred under the existing dependency/licence and hostile-input decision.
- **Consequences:** Common escaped spellings of the blocked active-content names fail before scanning/storage, with no new runtime dependency. This strengthens the lexical boundary without implying complete PDF security or antivirus coverage.
- **Validation:** Added raw escaped-name regressions alongside the raw and bounded-Flate active-content tests; `tests/test_security.py tests/test_ingestion.py` passed (`27 passed`), changed security files pass Ruff, and the rebuilt Compose service reports ready on `127.0.0.1:8001`. E11-04 is not promoted.
- **Implementation/evidence:** [security gate](../backend/app/security.py), [security tests](../backend/tests/test_security.py), [ingestion route](../backend/app/main.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-170 — Allow an explicitly configured confidence-calibration profile

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E1-02 and E9-04 remain bounded/partial respectively
- **Affected stories:** E1-02, E9-04, E9-09, E10-03
- **Context:** E9 confidence calibration was opt-in only through each extraction request. Operators need a deliberate deployment setting for a reviewed profile, while the default must remain heuristic and local. E1-02 requires settings to be typed, documented, path-safe and free of secret leakage.
- **Choice:** Add optional `confidence_calibration_path` to TOML/environment configuration. Resolve relative paths beside the selected configuration file, load and validate the data-only profile during application creation, fail closed with a sanitized configuration error, and let an explicit request profile override the configured profile. Do not ship a default profile or infer one from the repository fixture.
- **Alternatives:** Enable calibration from the checked-in fixture by default; rejected because it is not representative or held-out. Accept arbitrary profile JSON per deployment without validation; rejected because malformed mappings could distort review decisions. Store the profile in the database; deferred because a local immutable deployment artifact is easier to inspect and keeps extraction deterministic.
- **Consequences:** Operators can deliberately enable reviewed calibration for synchronous, asynchronous and persisted extraction while retaining raw scores. Missing configuration preserves the current heuristic behavior, and invalid profile files prevent startup rather than silently falling back. E9-04 remains partial until an independently reviewed calibration corpus, split and thresholds are available.
- **Validation:** Added relative-path configuration and startup/profile-application tests; extraction and benchmark tests remain green. The setting is documented in the E1 configuration table and extraction contract. No production calibration claim is made.
- **Implementation/evidence:** [configuration](../backend/app/config.py), [application integration](../backend/app/main.py), [configuration tests](../backend/tests/test_config.py), [extraction tests](../backend/tests/test_extraction.py), [calibration contract](../backend/app/calibration.py), [extraction contract](extraction-contract.md), [E1 settings](e1-foundation.md).

# DD-171 — Add a Windows working-set watchdog for isolated jobs

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** The isolated worker already applied POSIX resource limits and Windows Job Object CPU/memory limits, with a Windows CPU-clock watchdog. A native Windows probe did not provide stable evidence that Job Object CPU termination was observable on the development host, and there was no parent-side memory diagnostic when a platform limit failed to terminate promptly.
- **Choice:** Extend the parent-side Windows watchdog to read `GetProcessTimes` and `GetProcessMemoryInfo` without a new dependency, kill the child when configured CPU or working-set thresholds are reached, and report CPU versus memory exhaustion distinctly. Keep the Job Object as the primary Windows boundary, POSIX `RLIMIT_*` controls, wall-time guard, serialized-output guard and process-tree cleanup.
- **Alternatives:** Depend on `psutil`; deferred because it adds a runtime/licence surface for two native readings. Treat the Job Object attachment call as sufficient evidence; rejected because the observed native probe was inconclusive. Use only wall time; rejected because a memory-hungry job can affect neighboring work before its wall limit expires.
- **Consequences:** Windows deployments have an additional parent-owned memory termination path and actionable errors, while the implementation remains CPU/offline and dependency-free. A stable native exhaustion fixture, deployment cgroup/Job Object evidence and hostile-parser containment are still required before E12-02 or E11-04 can be promoted.
- **Validation:** Added a real supervisor regression for memory-limit error propagation; `tests/test_jobs.py` passed (`12 passed`), the changed worker files pass Ruff, and the rebuilt Compose service reports ready on `127.0.0.1:8001`. The native development-host CPU probe remains documented as inconclusive, so no full resource-enforcement claim is made.
- **Implementation/evidence:** [worker supervisor](../backend/app/worker.py), [job tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-172 — Expose the offline Chromium PDF candidate in the quickstart

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E14-01, E6-01, E6-04 and E6-05 remain partial
- **Affected stories:** E14-01, E6-01, E6-04, E6-05
- **Context:** The quickstart reached a deterministic server HTML artifact, while the repository already contained a network-disabled Chromium candidate harness used by the rendering comparison. New users had no documented command to produce that candidate, and treating HTML as PDF would change the source acceptance criterion.
- **Choice:** Add a small wrapper and quickstart step that converts the local HTML artifact through the existing offline Chromium harness, producing a PDF, manifest and screenshot. Keep candidate status, network-disabled behavior, font assessment and native-reader fields visible in the manifest; do not wire it into the production API or select Chromium as the default engine.
- **Alternatives:** Call the HTML artifact a generated PDF; rejected because it is a different format. Make Chromium the production renderer; rejected because E4-01 engine comparison, licensing, font embedding and native-reader evidence remain open. Require a browser print dialog; rejected because it is not reproducible or API-operable.
- **Consequences:** A new contributor can produce a concrete PDF candidate from the documented flow, and later engine/native-review work has a stable artifact entry point. Production PDF generation, embedded-font proof, reader compatibility, metadata fidelity and final output acceptance remain explicitly open.
- **Validation:** `scripts/quickstart_pdf_candidate.py` produced a non-empty 46,728-byte candidate with manifest status `candidate`, engine `chromium-playwright` and `network=disabled` from the existing script-matrix HTML; the wrapper passes Ruff. No E14-01 status promotion is made.
- **Implementation/evidence:** [quickstart wrapper](../scripts/quickstart_pdf_candidate.py), [quickstart](quickstart.md), [Chromium harness](../scripts/render_chromium_candidate.mjs), [candidate comparison](../scripts/compare_render_candidates.py), [rendering candidates](rendering-candidates.md), [story status](../frontend/src/storyStatus.ts).

# DD-197 — Fail closed and time the quickstart PDF candidate

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E14-01 remains partial
- **Affected stories:** E14-01, E6-01, E6-04, E6-05
- **Context:** The quickstart wrapper launched the offline Chromium candidate and printed paths, but did not independently verify the PDF signature, non-empty manifest, or elapsed render time after the child command returned.
- **Choice:** Measure the candidate command with a monotonic clock, require a non-empty `%PDF-` artifact and non-empty manifest after the child exits, and print elapsed seconds. Keep candidate status and the production-rendering boundary unchanged.
- **Alternatives:** Treat a zero exit code as sufficient; rejected because a renderer can exit successfully without writing the expected artifacts. Promote the candidate to production PDF output; rejected because renderer selection, licensing, fonts and native-reader evidence remain open.
- **Consequences:** The documented local path gives actionable artifact-integrity and timing evidence while failing closed on incomplete output. It still does not establish production PDF acceptance or a general ten-minute performance guarantee.
- **Validation:** The wrapper compiles and the existing Chromium candidate harness remains the producer of the PDF/manifest; the postconditions are intentionally checked after every successful child invocation. E14-01 remains partial.
- **Implementation/evidence:** [quickstart wrapper](../scripts/quickstart_pdf_candidate.py), [quickstart](quickstart.md), [Chromium harness](../scripts/render_chromium_candidate.mjs), [story status](../frontend/src/storyStatus.ts).

# DD-173 — Add bounded font-object evidence to candidate PDF manifests

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E6-05 and E4-02/E4-06 remain partial
- **Affected stories:** E6-05, E4-01, E4-02, E4-06, E4-07
- **Context:** The Chromium candidate manifest recorded metadata and visual hashes but represented fonts as entirely unassessed, even though the produced PDF contained inspectable font objects. A useful report must distinguish object-level evidence from glyph coverage and reader approval.
- **Choice:** Parse only bounded PDF byte markers in the candidate harness and report unique `/BaseFont`/`/FontName` values, embedded font-file marker count and `/ToUnicode` map count. Set glyph coverage to null and label the result object-inventory-only. Do not parse arbitrary streams, infer missing glyphs from names, or feed this evidence into production status.
- **Alternatives:** Treat font names as proof of embedded glyph coverage; rejected because names do not establish cmap coverage or reader behavior. Add a full PDF/font parser dependency; deferred pending engine/licence review. Leave the report empty; rejected because observable candidate evidence is useful for later comparison.
- **Consequences:** Candidate reviewers can see concrete font-object indicators and compare changes across fixtures without a false completion claim. Actual cmap/glyph coverage, fallback correctness, font licensing, PDF reader behavior and production output remain open.
- **Validation:** `node --check scripts/render_chromium_candidate.mjs` passed; a regenerated candidate manifest reported five unique font names, five embedded-font markers and five ToUnicode maps with `glyph_coverage: null`. E6-05 is not promoted.
- **Implementation/evidence:** [candidate harness](../scripts/render_chromium_candidate.mjs), [candidate contract](rendering-candidates.md), [comparison command](../scripts/compare_render_candidates.py), [story status](../frontend/src/storyStatus.ts).

# DD-174 — Extend bounded locale formatting evidence

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-09 remains partial
- **Affected stories:** E4-09, E2-08, E2-09
- **Context:** The formatter already had regression coverage for the shipped preview locale families, but the active profile needed explicit coverage for Thai, Korean and Arabic output details, including Arabic-Indic digits and the Arabic percent sign.
- **Choice:** Keep the dependency-free formatter and make the supported currency/separator symbols explicit for the shipped profiles. Apply Arabic-Indic digits only to Arabic-family locales and preserve raw numeric values before formatting. Keep regional fallback deterministic and bounded.
- **Alternatives:** Add a full CLDR/runtime internationalization dependency; deferred because it would add a dependency and licensing/runtime review surface. Infer locale behavior from browser APIs; rejected because offline server rendering must remain deterministic. Claim full locale correctness from these fixtures; rejected because calendars, shaping, accounting, timezone and native-reader behavior remain unverified.
- **Consequences:** Preview and extraction-export formatting now has visible regression evidence for the active bounded profiles, while the formatter remains CPU-only and offline. E4-09 remains partial and no complete CLDR or multilingual output claim is made.
- **Validation:** Locale-focused template tests pass (`7 passed, 22 deselected`); broader template tests and service readiness are validated below. The Arabic assertions cover grouped decimal output and percent output with Arabic-Indic digits.
- **Implementation/evidence:** [formatter](../backend/app/template_logic.py), [formatter tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-175 — Highlight exact extraction source boxes in review

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 and E10-01 remain partial
- **Affected stories:** E8-07, E10-01, E10-02
- **Context:** Extraction results already retained page, element and box provenance, and the review surface highlighted the containing PageModel element. A field-specific box could still be smaller than that element, so clicking a scalar or table value did not visibly identify the exact stored coordinates.
- **Choice:** Carry the selected field's bounded four-coordinate `source.box` through review state and render a non-interactive overlay on the matching source page, while retaining the containing element highlight and manual drawn-box workflow. Clear the exact-box overlay when a reviewer starts a new manual source selection.
- **Alternatives:** Replace element highlighting with the field box; rejected because element identity and role remain useful context. Recompute coordinates in the browser; rejected because the stored PageModel/source coordinates are authoritative. Rasterize every PDF page server-side; deferred because native page rendering and output-engine selection remain separate gates.
- **Consequences:** Reviewers can distinguish the exact field/cell region from its containing source element in both image/PDF overlay contexts and deterministic PageModel previews. E8-07/E10-01 remain partial for native raster fidelity, broad layout engines and full end-to-end document coverage.
- **Validation:** Frontend `npm run build` passed (`47 modules`); the focused live Playwright run against `http://localhost:8001` passed all three review tests, including the new exact-box assertion (`3 passed in 23.2s`). The service readiness endpoint reported database, storage and frontend ready.
- **Implementation/evidence:** [review UI](../frontend/src/main.tsx), [review styles](../frontend/src/editor.css), [browser test](../frontend/tests/foundation.spec.ts), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-176 — Add a validated layout-engine mapping boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-03 remains partial and E8-08 remains partial
- **Affected stories:** E8-03, E8-06, E8-08, E11-04
- **Context:** The PageModel already exposed heuristic roles for the simple digital-text path, but an engine adapter had no explicit validation boundary for pages, reading order, roles, tables, or source boxes. Directly trusting a future Docling/plugin payload would weaken provenance and hostile-input controls.
- **Choice:** Add a dependency-free `layout-engine-v1` mapper that bounds page/element counts, validates unique IDs, finite positive boxes, page numbers and allow-listed roles, derives deterministic reading-order metadata when absent, and returns a PageModel fragment. Use the same element mapper for the current local ingestion path. Keep engine-specific parsing and execution outside this mapper.
- **Alternatives:** Install Docling immediately; rejected because dependency/model/native licence and CPU evidence remain unresolved under DD-013. Accept arbitrary engine JSON; rejected because malformed geometry and duplicate identifiers would reach review/extraction. Infer missing geometry from text; rejected because fabricated source boxes violate provenance.
- **Consequences:** Future Docling, PaddleOCR or third-party adapters have a concrete normalized boundary, and current digital ingestion receives the same geometry validation. This does not claim Docling availability, OCR quality, arbitrary PDF reading order, rotation correctness, or native layout fidelity.
- **Validation:** Added mapper unit tests for roles/order/boxes, normalized pages, duplicate IDs, invalid rectangles and incompatible versions. `tests/test_layout.py tests/test_ingestion.py` passed (`19 passed, 3 warnings`); changed Python files pass Ruff. E8-03 and E8-08 remain partial.
- **Implementation/evidence:** [layout mapper](../backend/app/layout.py), [ingestion integration](../backend/app/ingestion.py), [layout tests](../backend/tests/test_layout.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-177 — Restrict optional scanner subprocess environment

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E8-01
- **Context:** The optional upload scanner already ran shell-free, before storage, with a timeout, but it inherited the application environment and removed only several known credential variable names. Deployments can define arbitrary secret names, so denylisting a fixed list was not a complete credential boundary.
- **Choice:** Pass the scanner only an explicit allow-list of `PATH`, platform process/temp variables, locale variables and timezone. Keep the executable and fixed arguments configured by the operator, use `shell=False`, retain the timeout and temporary-file cleanup, and do not expose scanner output.
- **Alternatives:** Continue removing known AWS/database names; rejected because unknown deployment secrets would remain exposed. Pass an empty environment; rejected because platform executable discovery and temporary-file behavior can require minimal process variables. Run the scanner inside the document worker; rejected because scanner integration is a separate upload boundary and must still fail closed before persistence.
- **Consequences:** Organization-provided scanners no longer receive arbitrary application secrets by inheritance. Operators must supply scanner configuration through fixed command arguments or the scanner's own controlled configuration. This does not establish antivirus effectiveness, parser isolation, or malware-detection coverage.
- **Validation:** Added a regression that sets an arbitrary application secret and uses a scanner command that succeeds only if it sees that variable; the upload is rejected, proving non-inheritance. Focused security/ingestion tests and Ruff validation are recorded below.
- **Implementation/evidence:** [scanner boundary](../backend/app/security.py), [security tests](../backend/tests/test_security.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-196 — Add bounded reusable components and editor interaction history

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-10 and E2-11 remain partial
- **Affected stories:** E2-10, E2-11
- **Context:** The editor had direct block editing and immutable template versions, but no user-facing history/clipboard controls or reusable component references. Component propagation must not duplicate mutable definitions into each template or allow executable content.
- **Choice:** Add bounded client-side undo/redo snapshots, copy/paste, shortcut handling, alignment actions, and an explicit snap/guides control. Store reusable components in a database registry, reference them from template blocks by ID, resolve the current definition only inside the isolated render boundary, and reject missing references or cycles. Component updates increment a registry version.
- **Alternatives:** Store component bodies inline; rejected because edits would not propagate. Resolve components in the browser; rejected because API and worker renders could diverge. Adopt a general canvas/layout dependency; deferred because the existing DOM/block editor remains the project’s bounded editor foundation and dependency/licence review is unresolved.
- **Consequences:** Referencing templates receive the current component definition on render, while definitions remain inert JSON blocks. The interaction controls are available without adding runtime dependencies. Actual geometric snapping/guideline placement and a complete component-management UI remain incomplete, so neither story is promoted to implemented.
- **Validation:** Frontend `npm run typecheck` passes. Python bytecode compilation passes. Existing focused backend tests reported 28 passed and 4 skipped, with 2 unrelated Windows temporary-directory permission errors. Full browser coverage for the new controls and component propagation is still required.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [component model](../backend/app/models.py), [component migration](../backend/migrations/versions/0012_reusable_components.py), [API and render expansion](../backend/app/main.py), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-197 — Prioritize the hybrid template editor and renderer adapter boundary

- **Date:** 2026-09-24
- **Status:** Accepted; implementation in progress
- **Affected stories:** E2-01 through E2-09, E2-10, E2-11, E4-01 through E4-10, E6-01, E6-04, E6-05, E7-01, E7-04, E11-04, E12-01, E12-02, E14-01
- **Context:** The agreed near-term product outcome is an owner-created template rendered to PDF. The current bounded JSON/template and isolated renderer contracts are more mature than a DOCX-first architecture, while final engine selection remains pending empirical and native-reader evidence. Prince can be evaluated without making it the default, but commercial deployment requires an appropriate license.
- **Choice:** Keep the bounded browser editor and versioned template JSON as the near-term authoring model, improve it toward a Word-like experience, retain Chromium as the default renderer, and introduce a renderer adapter contract with Prince as an optional explicitly configured implementation. Other backlog areas remain deferred unless they are prerequisites for this flow.
- **Alternatives:** Switch immediately to a DOCX-first office editor; deferred because it would replace the canonical model and require new contracts for bindings, loops, components, versioning, callbacks, and DOCX-to-PDF conversion. Make Prince the default now; rejected because E4-01 still lacks complete candidate comparison, font evidence, and native-reader grades. Keep renderer selection scattered through the API; rejected because it would make future engine selection and evidence tracking unsafe.
- **Consequences:** The critical editor-to-PDF path can progress without a commercial purchase or an immediate document-model rewrite. Chromium remains the reproducible default; Prince can be benchmarked and enabled only when deliberately configured and licensed. The hybrid editor is not a claim of full Word/DOCX compatibility, and final multilingual/PDF acceptance remains evidence-gated.
- **Validation:** Conversation scope and constraints are recorded in [editor-rendering-direction.md](editor-rendering-direction.md). The renderer adapter and editor changes will record focused tests, fixture manifests, engine versions, font hashes, and explicit native-reader/licensing gaps before any story promotion.
- **Implementation/evidence:** [editor-rendering-direction.md](editor-rendering-direction.md), [implementation plan](implementation-plan.md), [renderer candidate guide](rendering-candidates.md).

# DD-211 — Dispatch configured OCR only to mixed-document scan pages

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-02 and E8-04 remain partial
- **Affected stories:** E8-02, E8-04, E8-06, E10-01
- **Context:** Upload classification identified mixed PDFs conservatively, but a configured OCR adapter was reported unavailable for every mixed document. A valid local adapter could not process scan pages while preserving digital-page bypass semantics.
- **Choice:** Invoke the configured OCR protocol whenever at least one page is classified as `scan`, validate all returned page numbers, retain only elements for requested scan pages, preserve bounded digital text on digital pages, and record the requested scan-page list in processing metadata.
- **Alternatives:** OCR the whole mixed document and retain every returned page; rejected because digital pages must skip OCR. Invoke the adapter once per page; rejected because the existing protocol accepts one bounded upload and language, not a page stream. Continue reporting unavailable; rejected because it prevents deliberate local adapters from handling mixed inputs.
- **Consequences:** A configured page-aware adapter can process mixed scans without contaminating digital pages, and review consumers can inspect dispatch scope. The core image still contains no PaddleOCR/Tesseract engine, classification remains conservative, and OCR/layout accuracy is unverified; E8-02/E8-04 remain partial.
- **Validation:** Added a mixed-PDF integration regression with a configured local OCR command; ingestion tests pass (`18 passed`). The test verifies digital text remains on page 1, OCR text is retained only on scan page 2, and metadata records `requested_pages: [2]`.
- **Implementation/evidence:** [ingestion dispatch](../backend/app/main.py), [OCR protocol](../backend/app/ocr.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-206 — Kill configured converter process groups on timeout

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04, E2-04, E4-01
- **Context:** OCR already streamed bounded output and terminated its isolated process group on timeout or output overflow, while PDF and Word converter calls used `subprocess.run` and could terminate only the direct child on timeout. A configured converter could therefore leave descendants running after the API reported failure.
- **Choice:** Centralize quiet document-engine execution in a `Popen` helper that starts an isolated process group, waits with the configured wall-time limit, kills the group on timeout, and reaps the process before returning the exit code. Use the helper for both configured PDF and Word converters.
- **Alternatives:** Keep `subprocess.run` and rely on engine self-cleanup; rejected because operator-provided engines are not trusted to clean up descendants. Add platform-specific logic to each converter; rejected because duplicated timeout semantics invite drift. Use a shell wrapper; rejected because shell execution weakens the existing shell-free boundary.
- **Consequences:** Converter timeouts now clean up descendants on supported process-group platforms and preserve the existing quiet, shell-free contract. CPU/resource enforcement, Windows Job Objects and native engine effectiveness remain unverified, so E11-04 stays partial.
- **Validation:** Added real sleeping-engine timeout regressions for PDF and Word conversion; focused converter/process tests pass, including the existing 8 MB stderr tests. The helper uses POSIX sessions and Windows process groups where exposed by the host.
- **Implementation/evidence:** [process boundary](../backend/app/process_sandbox.py), [PDF renderer](../backend/app/pdf_render.py), [Word converter](../backend/app/word_convert.py), [converter tests](../backend/tests/test_pdf_render.py), [Word tests](../backend/tests/test_word_convert.py), [story status](../frontend/src/storyStatus.ts).

# DD-207 — Apply process-group cleanup to the optional upload scanner

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04
- **Context:** The optional upload scanner suppressed unbounded diagnostics and enforced a timeout, but it still used direct-child subprocess timeout handling while configured PDF/Word engines had moved to a shared killable-group helper.
- **Choice:** Run the scanner through the same shell-free, quiet `Popen` helper used by document engines. Preserve the scanner's restricted environment, temporary-file lifecycle, exit-code contract and fail-closed errors.
- **Alternatives:** Leave scanner cleanup to the configured executable; rejected because scanner wrappers can spawn descendants. Duplicate group-kill logic in `security.py`; rejected because timeout behavior would drift. Capture scanner diagnostics for troubleshooting; rejected because output is not part of the contract and can create memory pressure.
- **Consequences:** Scanner timeouts now terminate and reap the configured process group on supported platforms, reducing leftover-process and temporary-file-lock risk. This remains a hook and lexical upload boundary, not proof of antivirus effectiveness or complete parser isolation.
- **Validation:** Existing clean, rejection, secret-filtering, 8 MB diagnostic, timeout and PDF/SVG active-content tests pass through the shared boundary; changed security/process files pass Ruff.
- **Implementation/evidence:** [scanner boundary](../backend/app/security.py), [process boundary](../backend/app/process_sandbox.py), [security tests](../backend/tests/test_security.py), [story status](../frontend/src/storyStatus.ts).

# DD-208 — Add configurable resource ceilings to standalone worker services

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E12-03
- **Context:** Per-job child limits and watchdogs protect individual executions, but the Compose render and extraction services had no explicit container-level CPU, memory or process-count ceilings. A service-level runaway or fork storm could therefore consume host capacity beyond the child contract.
- **Choice:** Add independent Compose limits to both worker services: 2 CPUs, 768 MiB memory and 256 PIDs by default. Expose each through deployment environment variables so operators can size the two pools deliberately; retain the existing per-job wall, CPU, address-space and output limits.
- **Alternatives:** Apply one fixed limit to the whole stack; rejected because render and extraction pools are independently scalable. Remove child limits and rely on containers; rejected because a container cap does not isolate one job from its neighbors. Claim universal cgroup/Job Object enforcement; rejected because runtime-specific enforcement still needs deployment evidence.
- **Consequences:** The local Compose topology now has an explicit outer resource boundary for each worker pool while preserving the inner job supervisor contract. Defaults are operational safeguards, not capacity or SLO claims; web-process synchronous work and non-Compose deployments require their own limits, so E12-02 remains partial.
- **Validation:** `docker compose config` renders both worker ceilings; the live Compose stack rebuilt with the limits and remained ready on port 8001. Existing job/resource tests remain green.
- **Implementation/evidence:** [Compose topology](../compose.yaml), [jobs contract](../docs/jobs-contract.md), [worker supervisor](../backend/app/worker.py), [job tests](../backend/tests/test_jobs.py), [story status](../frontend/src/storyStatus.ts).

# DD-209 — Make confidence profiles traceable to corpus bytes

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E9-04 remains partial
- **Affected stories:** E9-04, E9-09
- **Context:** The offline isotonic calibration tool produced a profile ID from the source-name string only. Renaming or replacing a calibration corpus could therefore leave an operator without cryptographic evidence of which labelled records generated a configured profile.
- **Choice:** Record the corpus source, SHA-256 digest and record count in every generated calibration profile, and derive the profile ID from the corpus digest when available. Keep profile validation data-only and preserve raw confidence values when applying a profile.
- **Alternatives:** Trust a filename or operator-supplied profile ID; rejected because neither identifies corpus bytes. Embed all labelled records in the profile; rejected because it duplicates potentially sensitive data. Treat the repository fixture as production calibration evidence; rejected because it is deterministic but not representative or independently reviewed.
- **Consequences:** Operators can verify that a configured profile corresponds to a specific corpus artifact without storing the corpus in the profile. This improves provenance but does not establish calibration quality, split discipline, thresholds or independent review; E9-04 remains partial.
- **Validation:** Calibration tests verify the metadata contract and monotone profile behavior; the extraction contract documents the fields; changed script/tests pass Ruff and the benchmark suite.
- **Implementation/evidence:** [calibration builder](../scripts/calibrate_extraction.py), [calibration application](../backend/app/calibration.py), [benchmark tests](../backend/tests/test_benchmark.py), [extraction contract](../docs/extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-210 — Keep CPU guidance aligned with live worker ceilings

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E1-06 remains partial
- **Affected stories:** E1-06, E12-02
- **Context:** The foundation guide described an unbenchmarked 2-core/4-GiB development allocation, while the live Compose worker services now enforce separate 2-core/768-MiB/256-PID ceilings. Operators needed one documented statement of the current limits without mistaking them for engine sizing evidence.
- **Choice:** Add the active worker ceilings and their environment overrides to the CPU guidance, explicitly label them as service-boundary safeguards, and retain the existing warning that actual OCR/layout/PDF minimum hardware is not derived.
- **Alternatives:** Replace the guide's planning allocation with a claimed minimum; rejected because downstream engines are not selected or benchmarked. Omit the service limits from the guide; rejected because documentation would diverge from the running Compose topology. Reuse the small candidate benchmark as capacity evidence; rejected because its scope excludes the required engines.
- **Consequences:** CPU-only deployment guidance now matches the live Compose contract and points to the per-job limits. E1-06 and E12-02 remain partial pending engine-specific, cross-runtime sizing and containment evidence.
- **Validation:** The worker ceilings were inspected on both live containers; readiness returned HTTP 200; the CPU benchmark artifact remains explicitly scoped to deterministic HTML/local extraction; the jobs/resource suite passed.
- **Implementation/evidence:** [foundation guide](../docs/e1-foundation.md), [Compose topology](../compose.yaml), [CPU benchmark](../artifacts/cpu-pipeline-benchmark.json), [jobs contract](../docs/jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-198 — Use authentic native-script fixtures for direct editor entry

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-09 remains partial
- **Affected stories:** E2-09, E2-08, E4-02, E4-03, E4-04, E4-05
- **Context:** The browser test intended to cover direct multilingual editing used mojibake strings, so its successful round trip did not prove that authentic Arabic, Hebrew, Indic, Thai, or CJK text survived browser input and server preview.
- **Choice:** Add a browser contract using authentic Arabic, Hebrew, Hindi, Tamil, Thai, Chinese, Japanese, and Korean text. Exercise fill, selection, exact value retention, and final server-preview output; retain `dir="auto"` and locale assertions separately.
- **Alternatives:** Keep the existing strings because they are non-ASCII; rejected because mojibake is not evidence of native-script input. Promote E2-09 from this browser test; rejected because caret/IME behavior across supported operating systems and final rendering fidelity still require broader evidence.
- **Consequences:** The browser contract now detects UTF-8 corruption and verifies real script values through the editor and preview boundary. It does not claim IME certification, shaping, font coverage, or final PDF correctness.
- **Validation:** The focused Playwright multilingual tests and frontend build are the required validation; E2-09 stays partial until the broader input-method and rendering gates are evidenced.
- **Implementation/evidence:** [browser tests](../frontend/tests/foundation.spec.ts), [editor](../frontend/src/main.tsx), [script matrix](script-test-matrix.md), [story status](../frontend/src/storyStatus.ts).

# DD-199 — Refresh implementation-plan status boundaries

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented as documentation maintenance
- **Affected stories:** All Must stories represented by the status overlay; no source scope or priority changes
- **Context:** The implementation plan still stated that non-E1 epic implementation was unstarted, although the repository now contains validated contract slices across E1-E14 and an evidence-backed per-story status overlay.
- **Choice:** Update the plan and E3/E4 status page to identify the overlay as authoritative, summarize the delivered bounded slices, and list the remaining native-rendering, OCR, licensing, calibration, security-containment and review-fidelity gates. Preserve the source backlog and all partial statuses.
- **Alternatives:** Leave the stale statement in place; rejected because it misrepresents current implementation evidence. Mark every touched story complete; rejected because the listed acceptance gates remain unmet.
- **Consequences:** Planning documentation now matches the repository’s actual implementation position while preserving explicit uncertainty and open gates.
- **Validation:** Compared the updated summaries with `frontend/src/storyStatus.ts`, `docs/epics.md`, the current decision register, and the full backend regression result of 178 passed and 6 skipped. No story status was changed by this documentation update.
- **Implementation/evidence:** [implementation plan](implementation-plan.md), [E3/E4 status](epic-3-4-status.md), [story status](../frontend/src/storyStatus.ts), [source backlog](epics.md).

# DD-200 — Discard optional OCR diagnostics at the subprocess boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-04 and E11-04 remain partial
- **Affected stories:** E8-04, E11-04
- **Context:** The optional OCR adapter parsed bounded JSON stdout, but `capture_output=True` also buffered arbitrary stderr even though diagnostics were not exposed or used by the contract.
- **Choice:** Pipe only stdout for bounded JSON parsing and route OCR stderr to `DEVNULL`. Retain the existing UTF-8 parsing, 4 MiB stdout limit, timeout, reduced environment, and isolated worker boundary.
- **Alternatives:** Capture and truncate stderr after completion; rejected because the child can still emit unbounded diagnostics before truncation. Return stderr to callers; rejected because engine diagnostics are not part of the API contract and may contain sensitive input details.
- **Consequences:** Noisy OCR diagnostics cannot accumulate in the worker process memory or leak through the API. OCR engine correctness, native containment and model/licensing evidence remain open.
- **Validation:** Added an 8 MiB stderr regression; the OCR focus suite and Ruff checks pass. E8-04/E11-04 remain partial.
- **Implementation/evidence:** [OCR boundary](../backend/app/ocr.py), [OCR tests](../backend/tests/test_ocr.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-201 — Discard configured document-engine diagnostics

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E6-01, E6-03 and E11-04 remain partial
- **Affected stories:** E6-01, E6-03, E11-04
- **Context:** The optional HTML-to-PDF and Word-to-PDF boundaries validated output files but captured child stdout and stderr even though neither stream was returned or used. A noisy configured engine could consume worker memory through diagnostics.
- **Choice:** Route both streams to `DEVNULL`; retain shell-free invocation, reduced environment, timeout, output-file validation, PDF active-content checks and configured candidate status.
- **Alternatives:** Capture and truncate after completion; rejected because buffering occurs before truncation. Return engine diagnostics to API callers; rejected because they are not part of the contract and may expose document or environment details.
- **Consequences:** Configured document engines cannot accumulate unused diagnostics in the worker process. This does not select an engine or establish PDF/Word fidelity, fonts, native-reader approval, or complete OS-level containment.
- **Validation:** PDF and Word converter success regressions now emit 8 MiB stderr while still passing; focused converter tests and Ruff checks pass. E6-01/E6-03/E11-04 remain partial.
- **Implementation/evidence:** [PDF boundary](../backend/app/pdf_render.py), [Word boundary](../backend/app/word_convert.py), [converter tests](../backend/tests/test_pdf_render.py), [Word tests](../backend/tests/test_word_convert.py), [story status](../frontend/src/storyStatus.ts).

# DD-202 — Enforce the OCR stdout limit while the child runs

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-04 and E11-04 remain partial
- **Affected stories:** E8-04, E11-04, E12-02
- **Context:** The OCR adapter discarded stderr and checked its JSON stdout limit, but `subprocess.run` could buffer an oversized stdout stream before the post-process check.
- **Choice:** Run the OCR child with a reader thread, consume stdout in bounded chunks, terminate it as soon as the 4 MiB limit is crossed, and retain the existing timeout and fail-closed parsing behavior.
- **Alternatives:** Keep post-completion validation; rejected because a runaway engine could consume worker memory first. Redirect stdout to an unbounded temporary file; rejected because it moves the risk from memory to disk exhaustion. Increase the limit; rejected because the contract already defines the maximum output.
- **Consequences:** Oversized OCR output is stopped at the boundary and cannot be accumulated in the worker process. Process-tree enforcement, OCR engine availability, model licensing and scan accuracy remain open.
- **Validation:** Added a real child regression that emits 4,000,001 bytes and is terminated with the configured output-limit error; six OCR tests and Ruff checks pass. E8-04/E11-04 remain partial.
- **Implementation/evidence:** [OCR boundary](../backend/app/ocr.py), [OCR tests](../backend/tests/test_ocr.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-203 — Put configured document engines in killable process groups

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 and E12-02 remain partial
- **Affected stories:** E11-04, E12-02, E8-04, E6-01, E6-03
- **Context:** The worker supervisor already created its outer child in a new process group, but nested OCR, PDF, and Word engine commands did not explicitly create their own groups. A nested adapter could therefore outlive a direct-child termination on POSIX hosts.
- **Choice:** Start configured document-engine subprocesses in a new session/process group and terminate the group on OCR timeout or output-limit failure. Keep the outer worker Job Object, POSIX limits, watchdogs and wall-time controls unchanged.
- **Alternatives:** Kill only the direct engine PID; rejected because descendants could remain. Invoke platform-specific shell task-kill commands; rejected because shell invocation widens the boundary and is not portable. Claim Windows descendant enforcement from this helper alone; rejected because Windows deployment/job-object evidence remains required.
- **Consequences:** POSIX nested engine descendants are terminated with the engine when this boundary trips; Windows receives a process-group creation hint while the outer Job Object remains the primary descendant control. Full deployment-level resource and hostile-parser evidence remains open.
- **Validation:** Added process-group option coverage, real OCR output-limit coverage, and focused OCR/PDF/Word tests; Ruff passes. E11-04/E12-02 remain partial.
- **Implementation/evidence:** [process sandbox](../backend/app/process_sandbox.py), [OCR boundary](../backend/app/ocr.py), [PDF boundary](../backend/app/pdf_render.py), [Word boundary](../backend/app/word_convert.py), [sandbox test](../backend/tests/test_process_sandbox.py), [story status](../frontend/src/storyStatus.ts).

# DD-204 — Make mixed-document OCR limitations explicit

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-02 and E8-04 remain partial
- **Affected stories:** E8-02, E8-04, E8-06
- **Context:** Conservative page routing correctly identified mixed PDFs, but ingestion used the document-level digital route to report OCR as `skipped`, which could imply that scanned pages had been handled.
- **Choice:** When page routes contain both digital and scan pages, preserve the routes and digital text while reporting OCR as `unavailable` with the explicit reason `mixed documents require page-aware OCR dispatch`. Do not run a whole-document OCR command against a mixed PDF or invent scan-page text.
- **Alternatives:** Mark all mixed documents as scan and OCR the entire file; rejected because it loses digital text and lacks page extraction semantics. Keep reporting `skipped`; rejected because it hides an unprocessed scan page. Infer page byte ranges for arbitrary PDFs; deferred until a reviewed parser/layout engine exists.
- **Consequences:** API consumers can distinguish a fully digital skip from a mixed-document OCR gap, and no false extraction is created. Independent scan-page OCR dispatch and complex PDF parsing remain open.
- **Validation:** Mixed-PDF ingestion tests now assert the explicit unavailable reason; the focused ingestion suite passes. E8-02/E8-04 remain partial.
- **Implementation/evidence:** [ingestion route](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-205 — Add a source-to-status Must-story audit

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; no story status changes
- **Affected stories:** All source-backlog Must stories and E14-03 documentation
- **Context:** The status page had an explicit overlay, but there was no repository command proving that every Must row in the generated source catalogue was represented. A missing mapping would silently appear as an implicit planned state.
- **Choice:** Add a dependency-free audit script that parses Must IDs from `docs/epics.md`, validates their explicit `implemented`/`partial`/`planned` entries in `frontend/src/storyStatus.ts`, reports counts and IDs, and exits nonzero for omissions.
- **Alternatives:** Trust the UI fallback for unknown IDs; rejected because it hides status drift. Copy the status list into another manifest; rejected because duplicated source data would drift. Auto-promote unmapped stories; rejected because status requires evidence.
- **Consequences:** Backlog/status coverage is mechanically checkable and the existing conservative statuses remain unchanged. The audit validates presence, not acceptance evidence; decision records and tests remain authoritative for promotion.
- **Validation:** The command reports all 91 source Must IDs explicitly, with 55 implemented, 28 partial, and 8 planned entries; Python compilation, Ruff, frontend build, and the new CI workflow definition pass local checks. No story is promoted by the audit.
- **Implementation/evidence:** [audit command](../scripts/audit_must_status.py), [source backlog](epics.md), [status overlay](../frontend/src/storyStatus.ts), [implementation plan](implementation-plan.md).

# DD-196 — Accept the bounded source-provenance review contract for E8-07

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E10-01, E8-03, E8-04 and E8-08 remain partial
- **Affected stories:** E8-07, E10-01, E10-02
- **Context:** Earlier decisions correctly left E8-07 partial while provenance validation, exact field-box overlays and multi-page selection were incomplete. Those boundaries now require provenance for every non-null extracted value, and the review UI carries page, element and exact box selections through the persisted result.
- **Choice:** Mark E8-07 implemented for the source contract: local scalar/table extraction stores page-and-box provenance, invalid plug-in results fail closed, clicking extracted scalar/table values highlights the exact box, and reviewers can navigate to the provenance page. Keep native PDF rasterization, arbitrary layout-engine accuracy and image/OCR quality scoped to E10-01/E8-03/E8-04 rather than extending E8-07.
- **Alternatives:** Keep E8-07 partial until native PDF rasterization; rejected because the source acceptance requires a highlighted source region and the current PDF/PageModel overlay satisfies that bounded contract, while raster fidelity is explicitly a separate implementation gap. Promote all review stories together; rejected because E10-01 has a page-image/native-render criterion not covered here. Infer missing boxes; rejected because it violates provenance integrity.
- **Consequences:** Consumers can rely on non-null extracted values being reviewable through the versioned provenance contract. Results from unavailable or incomplete OCR/layout engines remain partial elsewhere, and native reader/page-image fidelity is not implied.
- **Validation:** `tests/test_engines.py tests/test_extraction.py` pass with the missing-provenance regression; focused live Playwright tests pass for exact-box highlighting, line-item selection and multi-page provenance navigation; the extraction contract and status page are updated. E8-07 is promoted only within this bounded acceptance.
- **Implementation/evidence:** [engine registry](../backend/app/engines.py), [local extractor](../backend/app/extraction.py), [review UI](../frontend/src/main.tsx), [engine/extraction tests](../backend/tests/test_engines.py), [review browser tests](../frontend/tests/foundation.spec.ts), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-191 — Record conservative per-page ingestion route evidence

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-02 and E8-05 remain partial
- **Affected stories:** E8-02, E8-05, E8-06
- **Context:** Ingestion exposed only one document-level route even when a simple multi-page PDF contained text on one page and no detectable text on another. The source requires digital/scanned page detection, but the current bounded parser cannot safely associate arbitrary PDF content streams with page objects.
- **Choice:** Add `route` to each PageModel page and `processing.page_routes`. For PDFs with exactly identifiable `/Type /Page` spans, classify each span from bounded text-operator evidence; otherwise repeat the document route for all pages. Do not change the document-level route or claim page-specific OCR execution until content-stream mapping is available.
- **Alternatives:** Treat every page as digital when any text exists; rejected because scans could skip OCR. Treat every page as scan; rejected because known digital pages would lose the local path. Split or parse arbitrary PDF streams immediately; deferred pending a reviewed parser and hostile-input evidence.
- **Consequences:** Mixed simple PDFs now expose useful, auditable page-route evidence without fabricating certainty. The current OCR adapter still receives the uploaded document as a whole, so page-specific routing and processing progress remain open.
- **Validation:** Added a mixed-page route regression; the focused ingestion suite and changed-file Ruff checks pass. E8-02 is not promoted.
- **Implementation/evidence:** [ingestion classifier](../backend/app/ingestion.py), [ingestion route](../backend/app/main.py), [ingestion tests](../backend/tests/test_ingestion.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-192 — Persist complete field snapshots for correction undo

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E10-02 and E10-06 implemented
- **Affected stories:** E10-02, E10-06
- **Context:** Correction audit rows retained original and new scalar values, but undo reconstructed only `normalized_value`, `absent`, `review_status` and `validation`. A correction that changed source provenance could therefore not be undone faithfully.
- **Choice:** Add nullable before/after field JSON snapshots to correction records. New corrections persist the complete field state, and undo restores the latest before snapshot while recording its own snapshot. Legacy rows use the existing value-only fallback. Allow a correction request to replace a field's source with the same bounded validation used for manually added fields.
- **Alternatives:** Encode metadata into the scalar `original_value`/`new_value` columns; rejected because it would break existing CSV/audit semantics. Reconstruct only known metadata keys; rejected because future field metadata would still be lost. Rewrite historical rows; rejected because audit history must remain immutable and old rows can be handled explicitly.
- **Consequences:** Source boxes, absent state, validation, confidence and review metadata survive correction undo without deleting audit rows. The browser exposes the revision-safe undo action; broader native review evidence remains a separate quality gate.
- **Validation:** Added migration `0011`, API source-correction coverage, an end-to-end undo regression, and a live Playwright flow proving edit-save-undo restoration; extraction tests and the frontend build pass. The review contract documents legacy fallback behavior.
- **Implementation/evidence:** [review model](../backend/app/models.py), [review endpoints](../backend/app/main.py), [migration](../backend/migrations/versions/0011_correction_snapshots.py), [extraction tests](../backend/tests/test_extraction.py), [review contract](review-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-178 — Validate provenance at the extraction-engine boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 and E8-08 remain partial
- **Affected stories:** E8-07, E8-08, E9-03, E10-01
- **Context:** The `extraction-engine-v1` registry checked result shape and confidence but accepted arbitrary non-null provenance dictionaries. An optional engine could therefore return a page without a valid box, malformed coordinates, or a non-string element ID, breaking source highlighting and review traceability.
- **Choice:** Require every non-null scalar or table-cell source to contain a positive integer page number and a finite positive four-coordinate box; validate optional element IDs and reject incompatible plugin output before it reaches persistence or review. Keep missing predictions explicitly `source: null` rather than fabricating geometry.
- **Alternatives:** Infer a box from the nearest PageModel element; rejected because fabricated provenance violates the extraction contract. Accept page-only sources; rejected because E8-07 requires a source region. Reject the entire engine at discovery time; rejected because runtime result validation gives a precise, engine-scoped failure without preventing the local engine from starting.
- **Consequences:** Third-party, Docling and future OCR adapters must provide reviewable geometry, and malformed results fail closed. The local engine remains offline and unchanged; actual external engine availability, OCR/layout quality and end-to-end native source rendering remain open.
- **Validation:** Added an invalid-plugin regression for a degenerate source box; `tests/test_engines.py tests/test_extraction.py` passed (`15 passed, 3 warnings`) and changed engine files pass Ruff.
- **Implementation/evidence:** [engine registry](../backend/app/engines.py), [engine tests](../backend/tests/test_engines.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-186 — Expose page-flow controls on every editor block

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-07 remains partial
- **Affected stories:** E2-07, E2-01, E4-08
- **Context:** The editor already persisted `break_before` and `keep_together` for the active block and the renderer emitted bounded CSS, but owners could not configure flow rules on a non-selected block without first selecting it.
- **Choice:** Add compact page-flow checkboxes to every block row, bound directly to that block's state, while retaining the toolbar controls for the selected block. Give row controls distinct accessible names and preserve the existing server-render contract.
- **Alternatives:** Require selecting a block before editing its flow; rejected because it obscures which block is configured. Add arbitrary CSS; rejected because it weakens the bounded template grammar. Infer breaks from content length; rejected because explicit owner intent must remain authoritative.
- **Consequences:** Owners can configure automatic page breaks and keep-together behavior directly where each block appears, and saved definitions continue to produce the existing deterministic CSS. Full engine pagination and native PDF reader evidence remain open, so E2-07 stays partial.
- **Validation:** Frontend typecheck/build and the focused live page-flow browser suite pass, including per-block checkbox interaction; the server preview continues to assert `break-before:page` and `break-inside:avoid`.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [editor styles](../frontend/src/editor.css), [browser test](../frontend/tests/foundation.spec.ts), [template contract](template-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-198 — Package the default Chromium renderer for the production container

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E4-01 and E4-02 remain partial pending comparison and acceptance evidence
- **Affected stories:** E2-01, E2-10, E2-11, E4-01, E4-02, E4-08, E12-01, E12-02
- **Context:** The adapter boundary selected Chromium as the default, but the production container still depended on an operator-provided browser command. That made the default configuration non-runnable for a clean deployment and left the browser version outside the application image.
- **Choice:** Pin Playwright as a direct frontend dependency, package its Chromium browser and system dependencies in the production image, run the renderer as the non-root application user, and use the packaged script when no explicit Chromium command is configured. Preserve explicit command overrides and keep Prince opt-in with its own command and license-file settings.
- **Alternatives:** Require every operator to install Chromium; rejected because the default flow would fail on a clean image. Download a browser at application startup; rejected because it violates deterministic/offline startup. Make Prince the default; rejected because engine comparison and licensing evidence are not complete.
- **Consequences:** A clean production image can render without an external browser installation, while operators retain an explicit override path and a future Prince adapter path. The image now includes browser binaries, OS dependencies and fonts that require the existing dependency/licence inventory review. Renderer correctness, multilingual coverage, native-reader review, accessibility and Prince licensing remain open; no story is promoted solely by packaging.
- **Validation:** Frontend production build passed; focused adapter/config/PDF tests passed (`19 passed`); the pinned production image built successfully; a non-root in-container smoke render produced a non-empty PDF beginning with `%PDF-1.4` and a manifest with network access disabled. The smoke test is only execution evidence, not full rendering acceptance.
- **Implementation/evidence:** [Dockerfile](../Dockerfile), [renderer adapter](../backend/app/renderer_adapter.py), [Chromium script](../scripts/render_chromium_candidate.mjs), [PDF service](../backend/app/pdf_render.py), [configuration](../backend/app/config.py), [adapter tests](../backend/tests/test_renderer_adapter.py), [direction record](editor-rendering-direction.md), [rendering candidates](rendering-candidates.md).
# DD-187 — Validate generated code SVGs before document embedding

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E2-04 remains partial
- **Affected stories:** E2-04, E11-04
- **Context:** QR, Code 128 and EAN-13 libraries generated SVG markup that was embedded directly in the bounded HTML renderer. Existing upload SVG validation did not automatically protect generated output if a dependency changed its serialization.
- **Choice:** Run every generated code SVG through the existing root/size/active-content/external-reference validator and require drawable SVG geometry before embedding. Keep the encoder libraries pinned and the output offline.
- **Alternatives:** Trust dependency output indefinitely; rejected because generated markup is still an input boundary. Parse and rewrite all SVG XML; rejected because it adds complexity without improving the current bounded contract. Rasterize codes; rejected because it would weaken scalable output and introduce another rendering dependency.
- **Consequences:** A changed or compromised encoder output fails closed before it reaches the document artifact, while valid code vectors remain deterministic. This does not establish QR/barcode scanner compatibility, PDF embedding fidelity, or licence compliance, so E2-04 remains partial.
- **Validation:** Code-render tests pass with geometry and active-content assertions; the focused template suite and frontend/browser code-block flow remain green.
- **Implementation/evidence:** [code generators](../backend/app/codes.py), [renderer tests](../backend/tests/test_template_logic.py), [SVG security validator](../backend/app/security.py), [story status](../frontend/src/storyStatus.ts).
# DD-188 — Run render and extraction pools as separate Compose services

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-03 remains partial
- **Affected stories:** E12-03, E12-01, E12-02, E7-04
- **Context:** Durable jobs already carried a kind and the web process supported separate render/extraction thread counts, but both pools were embedded in one API process and could not be scaled independently as deployment units.
- **Choice:** Expose the existing bounded job executor through application state and add standalone `render-worker` and `extraction-worker` services that claim only their own job kind. Compose disables embedded web workers by default; operators scale the two services independently with Compose replica counts. Lease recovery and child-process limits remain shared contracts.
- **Alternatives:** Duplicate execution logic in each worker; rejected because drift would weaken result and failure semantics. Keep all workers in the API; rejected because process scaling remains coupled. Add a broker; deferred because the existing PostgreSQL lease queue is sufficient for this deployment boundary.
- **Consequences:** Render and extraction capacity now have separate service/process boundaries and can be scaled independently without changing API job payloads. Throughput, autoscaling, resource-exhaustion and production multi-host guarantees remain unverified, so E12-03 and E12-02 remain partial.
- **Validation:** Compose configuration validates and the rebuilt topology reports healthy `web`, `render-worker`, and `extraction-worker` services on port 8001. A live queued render completed with status `done`, kind `render`, and one attempt; a live asynchronous extraction completed with status `done`, kind `extraction`, and one attempt. The benchmark command recorded variable results: the initial eight-job/80-block rerun measured 8.622 seconds with one worker versus 9.241 seconds with two; a larger 12-job/300-block run measured 12.199 versus 9.609 seconds, but its immediate repeat measured 10.907 versus 19.031 seconds. The latest report is [compose-worker-throughput.json](../artifacts/compose-worker-throughput.json). Because the throughput improvement is not reproducible on this host, E12-03 remains partial. Standalone worker kind validation passes. No general capacity, autoscaling or native resource-enforcement claim is made.
- **Implementation/evidence:** [worker service](../backend/app/worker_service.py), [executor hook](../backend/app/main.py), [Compose topology](../compose.yaml), [worker test](../backend/tests/test_worker_service.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-193 — Make the Compose worker benchmark repeated and order-aware

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-03 remains partial pending observed results
- **Affected stories:** E12-03, E12-09
- **Context:** The first Compose worker benchmark used one sample per worker count and sequential status polling. Host scheduling and API polling overhead produced contradictory results across immediate repeats, so the report was too weak for a throughput comparison.
- **Choice:** Warm each one- and two-worker topology, collect configurable repeated samples (default three), poll job states concurrently, and compare medians while retaining all raw samples and warm-up times. Keep the workload bounded and local, and treat the result as an observation rather than a capacity target.
- **Alternatives:** Declare the fastest prior run authoritative; rejected because it is selection bias. Average all historical artifacts; rejected because host state and code versions differ. Add a benchmark service or external load generator; deferred because the current acceptance needs a repository-runnable local Compose test first.
- **Consequences:** The benchmark now exposes variability and reduces sequential polling distortion, making a future throughput claim more reproducible. It still does not establish multi-host scaling, autoscaling, a production SLO, or resource enforcement.
- **Validation:** The benchmark script passes compilation and Ruff; the next repeated live run will be recorded in the generated artifact. E12-03 is not promoted by this methodology change alone.
- **Implementation/evidence:** [benchmark](../scripts/benchmark_compose_workers.py), [jobs contract](jobs-contract.md), [throughput artifact](../artifacts/compose-worker-throughput.json), [story status](../frontend/src/storyStatus.ts).

# DD-194 — Accept the repeated Compose throughput evidence for E12-03

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-03
- **Context:** DD-188 recorded standalone worker services but retained E12-03 as partial because single-run measurements contradicted one another. DD-193 changed the benchmark to warm each topology, poll concurrently, and compare repeated samples.
- **Choice:** Mark E12-03 implemented for its source acceptance criterion based on the recorded local repeated load test: three one-worker samples had a median of 9.748 seconds, three two-worker samples had a median of 5.546 seconds, and every two-worker sample was faster than every one-worker sample in that run. Keep the result scoped to the documented eight-job/80-block deterministic HTML workload.
- **Alternatives:** Require a production-scale or multi-host benchmark; rejected for this story’s current repository acceptance because those are separate operational objectives. Promote from service topology alone; rejected because it lacks throughput evidence. Keep partial despite the new evidence; rejected because the repeated run now directly exercises the acceptance criterion.
- **Consequences:** The project has a reproducible repository command and one evidence-backed local demonstration that adding a render worker improves throughput. This does not claim universal capacity, autoscaling, multi-host behavior, PDF/OCR throughput, or resource enforcement; E12-02 remains partial.
- **Validation:** `scripts/benchmark_compose_workers.py --jobs 8 --blocks 80 --repeats 3` produced [compose-worker-throughput.json](../artifacts/compose-worker-throughput.json): one-worker samples `[8.774, 9.748, 19.179]`, two-worker samples `[5.546, 4.970, 5.678]`, medians `9.748` and `5.546`. The benchmark passes Ruff/compilation, and the live Compose API/workers remained ready during the run.
- **Implementation/evidence:** [worker service](../backend/app/worker_service.py), [Compose topology](../compose.yaml), [benchmark](../scripts/benchmark_compose_workers.py), [throughput artifact](../artifacts/compose-worker-throughput.json), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-195 — Add a real POSIX runaway-engine regression

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E12-02 remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** Isolated jobs had real output-limit and wall-time regressions plus mocked Windows watchdog coverage, but no real CPU-bound nested document-engine regression. The current development host is Windows, so its POSIX resource path cannot execute natively.
- **Choice:** Add a POSIX-only regression that runs a CPU-bound operator OCR command inside the isolated worker, asserts termination before the five-second wall limit, and runs a subsequent render successfully. Skip it on Windows rather than treating the platform mismatch as evidence.
- **Alternatives:** Claim CPU containment from `RLIMIT_CPU` configuration alone; rejected because configuration is not execution evidence. Run a busy loop in the Windows test suite and call wall-time termination CPU enforcement; rejected because it conflates limits. Make the test non-skipping; rejected because it would be false or flaky on Windows.
- **Consequences:** Linux/container CI can now prove a real runaway nested engine is stopped without poisoning the next job. Windows Job Object exhaustion and deployment-level enforcement remain open, so E12-02 and E11-04 stay partial.
- **Validation:** `tests/test_jobs.py` passes on the current Windows host with 12 passed and 1 explicitly skipped; the new test is marked for POSIX RLIMIT environments and changed test/worker files pass Ruff. The same worker path executed inside the Linux-based Compose web container and reported `runaway_stopped=True elapsed=1.470` followed by a successful `next_job=...after CPU` render.
- **Implementation/evidence:** [worker supervisor](../backend/app/worker.py), [worker child](../backend/app/worker_child.py), [job tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-190 — Require provenance for every non-null extracted value

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E8-07 and E8-08 remain partial
- **Affected stories:** E8-07, E8-08, E9-03, E10-01
- **Context:** The extraction-engine contract validated the shape of a non-null source, but allowed an engine to return a non-null original or normalized value with `source: null`. That value could not satisfy source-region highlighting or provenance retention.
- **Choice:** Reject scalar and table fields that contain a non-null original or normalized value without page-and-box provenance. Continue allowing `source: null` for genuinely missing fields, and retain strict validation of page numbers, boxes and element IDs.
- **Alternatives:** Infer a source from nearby PageModel elements; rejected because fabricated provenance is worse than an explicit missing value. Reject every result containing a missing field source; rejected because required-field misses are valid review outcomes. Allow the result and show an unhighlightable value; rejected because it violates the extraction contract.
- **Consequences:** Plug-in engines fail closed before malformed provenance reaches persistence or review, while missing-field review remains representable. This does not establish OCR/layout accuracy, complete source rendering fidelity, or three available production engines.
- **Validation:** Added a plug-in regression for a non-null value without provenance; extraction-engine tests and Ruff pass. The extraction contract documents the invariant, and the status overlay correctly leaves E8-07/E8-08 partial.
- **Implementation/evidence:** [engine registry](../backend/app/engines.py), [engine tests](../backend/tests/test_engines.py), [extraction contract](extraction-contract.md), [story status](../frontend/src/storyStatus.ts).

# DD-189 — Discard optional scanner output at the subprocess boundary

- **Date:** 2026-09-24
- **Status:** Accepted and Implemented; E11-04 remains partial
- **Affected stories:** E11-04
- **Context:** The optional upload scanner already ran shell-free, with a timeout, a restricted environment and no returned diagnostic output, but `capture_output=True` still buffered arbitrary scanner stdout and stderr in the web process. A noisy configured scanner could therefore create avoidable memory pressure during upload validation.
- **Choice:** Route scanner stdout and stderr directly to `DEVNULL`. Continue using the scanner exit code as the only result signal, and retain timeout, environment allow-list, temporary-file cleanup and fail-closed error handling.
- **Alternatives:** Keep captured output and truncate it after completion; rejected because the subprocess pipe can still buffer unbounded output before the parent receives it. Capture a small diagnostic prefix; deferred because scanner output is intentionally not part of the API contract and suppressing it is safer. Ignore scanner output only in deployment documentation; rejected because the process boundary must enforce the limit.
- **Consequences:** Scanner diagnostics cannot consume web-process memory and are not exposed to callers. Operators must use scanner-local logging for diagnostics. This remains a bounded safeguard, not evidence of antivirus effectiveness, parser isolation or complete native sandbox coverage.
- **Validation:** Added a regression scanner that emits 8 MB on each output stream and exits cleanly; focused security tests pass and the changed security module passes Ruff. E11-04 is not promoted.
- **Implementation/evidence:** [scanner boundary](../backend/app/security.py), [security tests](../backend/tests/test_security.py), [ingestion contract](ingestion-contract.md), [story status](../frontend/src/storyStatus.ts).
# DD-200 — Generate deterministic, non-persistent preview sample data

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E5-09 remains partial pending broader type/locale coverage
- **Affected stories:** E5-09
- **Context:** The editor relied on hand-authored sample data and hard-coded values for a few inserted blocks. Owners could not regenerate a useful preview dataset after adding bindings, tables, loops or conditions.
- **Choice:** Add a local deterministic generator exposed by `POST /api/templates/{template_id}/sample-data` and a workspace action. Prefer the template's bounded `data_schema`; otherwise infer scalar values from supported bindings, create one repeat-table/loop row, and set condition paths true. Locale affects text examples and the generated values are returned to the editor without persistence.
- **Alternatives:** Use random/faker data; rejected because previews should be reproducible and would add a dependency/licence surface. Persist generated values automatically; rejected because generation is a preview aid and must not silently change template data. Ask an external AI service; rejected because the local CPU/offline path is required and preview data does not need external inference.
- **Consequences:** Owners can refresh usable preview data without manually editing JSON. The generator intentionally covers the bounded template contract only; dates, currencies, custom schemas, nested loop scopes and locale semantics need additional fixtures before E5-09 can be marked fully implemented.
- **Validation:** `backend/.venv/Scripts/python.exe -m pytest -q tests/test_template_logic.py` and `npm run build` pass. The focused test covers schema-driven object/number/boolean values, locale-sensitive text, date inference, condition fields and repeat-table rows. No PDF/native-reader claim is made.
- **Implementation/evidence:** [template generator](../backend/app/template_logic.py), [API route](../backend/app/main.py), [editor action](../frontend/src/main.tsx), [API reference](api-reference.md), [focused test](../backend/tests/test_template_logic.py).

# DD-201 — Add bounded operational enablers for E1 R2 stories

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented as partial slices
- **Affected stories:** E1-07, E1-08, E1-09, E1-10, E1-11, E1-12
- **Context:** The foundation had migration coverage and Compose deployment, but no repository-local Helm chart, explicit offline bundle manifest, recoverable backup command, retention purge command, or documented non-Docker contributor path.
- **Choice:** Add reviewable, CPU-only operational artifacts: a minimal Helm chart, an offline bundle manifest that explicitly calls out unbundled fonts/models, tar plus PostgreSQL backup/restore tooling, a dry-run-first local retention purge, and contributor setup documentation. Keep these slices opt-in and avoid changing the normal Compose deployment or adding dependencies.
- **Alternatives:** Claim the source stories from the existing Compose file; rejected because Helm, restore, retention and offline behavior need distinct artifacts. Add an in-application scheduler immediately; deferred because deployment operators need an explicit command and object-store semantics must be designed for both local and S3 backends. Bundle fonts/models now; rejected because DD-013/licence and engine evidence remain unresolved.
- **Consequences:** Operators have inspectable starting points for the six E1 stories, while full acceptance remains partial pending upgrade-from-two-releases tests, a live Kubernetes smoke test, a genuinely offline image/model/font bundle, restore validation against disposable PostgreSQL, scheduled S3 retention, and a complete local hot-reload integration path.
- **Validation:** Python compilation, `38 passed` focused backend tests, frontend production build, status audit, and `git diff --check` passed after this batch. Helm was not installed, so chart linting was not run; no Kubernetes cluster, offline network-isolated install, backup restore, or production retention run is claimed.
- **Implementation/evidence:** [Helm chart](../charts/docplatform), [offline manifest](../templates/docplatform-offline-bundle.json), [backup tool](../scripts/backup_restore.py), [retention tool](../scripts/purge_retention.py), [local development guide](local-development.md), [story status](../frontend/src/storyStatus.ts).

# DD-202 — Keep themes, charts and locked backgrounds data-only

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented as partial slices
- **Affected stories:** E2-12, E2-14, E2-15
- **Context:** The renderer already bounded text, tables, images and codes, but had no data-only representation for brand tokens, simple charts or a locked page background.
- **Choice:** Accept a definition `theme` map of bounded CSS token names/values, a chart block rendered as sanitized SVG from an array of labels and numeric values, and a page `background` only when it is a data-image URI. Do not permit arbitrary CSS, network URLs, scripts or chart libraries.
- **Alternatives:** Add a chart dependency; deferred because the current SVG contract is sufficient for a bounded preview and avoids a new licence graph. Permit remote backgrounds; rejected because renderer network access must remain disabled. Treat theme values as arbitrary CSS; rejected because it expands the injection surface.
- **Consequences:** Preview HTML can represent basic visual themes, bar/line/pie-shaped chart requests and locked raster backgrounds. Chart geometry is currently a bounded bar representation, chart pagination/reader fidelity and final PDF embedding remain unverified.
- **Validation:** Focused template tests pass with theme-token, SVG geometry, and data-image background assertions; frontend build and Python compilation pass. Final browser/PDF acceptance remains partial.
- **Implementation/evidence:** [renderer](../backend/app/rendering.py), [focused tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).

# DD-203 — Add explicit template sync and opt-in publish approval boundaries

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented as partial slices
- **Affected stories:** E3-08, E3-09
- **Context:** Portable template export/import existed, but there was no repository-file sync command and publishing did not expose an operator-controlled review gate.
- **Choice:** Add a shell-free Python sync command that pulls exports into plain JSON/ZIP files or creates templates from JSON, and add `template_publish_requires_approval` plus an explicit version review endpoint. Keep approval disabled by default for local compatibility; when enabled, only an approved version can publish.
- **Alternatives:** Run arbitrary git commands inside the API; rejected because repository credentials and network access do not belong in document workers. Make approval mandatory by default; rejected because existing local seeded templates and single-user development need a deliberate migration/configuration choice. Treat draft status as approval; rejected because it does not identify reviewer intent.
- **Consequences:** CI can build a small pull/push workflow around plain files, and deployments can require reviewer approval before publish. Authentication, reviewer identity, signed commits, conflict handling and a CI integration test remain incomplete.
- **Validation:** Python compilation, focused backend tests, frontend build, status audit, and `git diff --check` pass. No remote Git server, multi-user review, or production promotion is claimed.
- **Implementation/evidence:** [sync command](../scripts/sync_templates.py), [approval configuration](../backend/app/config.py), [review/publish routes](../backend/app/main.py), [story status](../frontend/src/storyStatus.ts).

# DD-204 — Keep accessibility and cross-reference foundations explicit

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented as partial slices
- **Affected stories:** E2-13, E2-16
- **Context:** The editor already used semantic headings, labels, focusable controls and keyboard handlers, but no accessibility certification existed. The renderer had no bounded table-of-contents or anchor contract.
- **Choice:** Preserve the semantic/keyboard foundations and mark E2-13 partial pending WCAG 2.2 AA audit and assistive-technology coverage. Add a data-only `toc` block, declared bounded anchors, and escaped same-document links; leave pagination-derived page numbers explicitly unimplemented.
- **Alternatives:** Claim WCAG from semantic markup alone; rejected because keyboard, screen-reader, contrast and browser coverage require an audit. Generate page numbers in the renderer; deferred because pagination engine selection and final PDF evidence are unresolved. Permit arbitrary anchor URLs; rejected because cross-document navigation is outside this contract and expands security scope.
- **Consequences:** Templates can express a safe structural TOC and same-document references while remaining honest about page-number updates. Accessibility and final TOC pagination remain partial.
- **Validation:** Focused rendering tests cover escaped anchors and TOC links; frontend build and existing browser contract tests remain applicable. No WCAG certification or final PDF page-reference claim is made.
- **Implementation/evidence:** [renderer](../backend/app/rendering.py), [rendering tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).
# DD-206 — Expose designer PDF generation in the template editor

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented
- **Affected stories:** E2-01, E4-08, E6-01, E6-04, E6-05
- **Context:** The dedicated `render-pdf` API already generated a candidate PDF, but the browser editor exposed only the deterministic HTML server preview. Template owners needed a direct UI action and an in-browser result.
- **Choice:** Add a `Generate PDF` editor action. It saves the current editor state as a draft, calls `POST /api/templates/{template_id}/render-pdf` with the draft sample data and selected locale, decodes the returned Base64 PDF into a browser Blob URL, embeds it in the editor, and exposes a download link. Revoke replaced Blob URLs and clear PDF state when changing templates.
- **Alternatives:** Continue requiring API/PowerShell use; rejected because it leaves the primary owner workflow incomplete. Print the HTML iframe from the browser; rejected because it bypasses the dedicated isolated PDF renderer. Add a new frontend PDF dependency; rejected because the browser can display a PDF Blob natively and no dependency is needed.
- **Consequences:** Owners can generate and inspect the current candidate PDF without leaving the template editor. The action inherits the API renderer's current candidate/native-reader and fidelity limitations; it does not promote E4-01 or E6-01 acceptance.
- **Validation:** `npm run build` passed; the focused Playwright workflow passed against a rebuilt Compose stack (`1 passed`), including HTTP 200 from `/render-pdf`, embedded PDF visibility and a Blob download link. Focused backend worker/PDF/process tests passed (`18 passed, 1 skipped`). The generated artifact remains labelled as a candidate by the API report.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [editor strings](../frontend/src/i18n.ts), [editor styles](../frontend/src/editor.css), [worker boundary](../backend/app/worker.py), [engine sandbox](../backend/app/process_sandbox.py), [worker child](../backend/app/worker_child.py), [configuration](../config.toml), [API reference](api-reference.md), [quickstart](quickstart.md), [rendering candidates](rendering-candidates.md).

# DD-207 — Stage uploaded image assets for isolated designer PDF rendering

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E6-01 remains partial for native-reader/fidelity evidence
- **Affected stories:** E2-03, E6-01, E6-05, E11-04
- **Context:** Uploaded logos were stored as `/api/assets/...` references. The HTML server preview could resolve those same-origin URLs, but the isolated PDF engine has network access disabled and therefore produced a missing/thumbnail image result.
- **Choice:** During the API-owned PDF flow, resolve matching stored asset references through the configured object store and replace them with bounded data URIs before passing HTML to the credential-free PDF worker. Revalidate stored SVG markup, fail clearly when a referenced asset is missing, and leave external URLs network-disabled.
- **Alternatives:** Permit the PDF worker to fetch `/api/assets/...`; rejected because it would require credentials/network access and weaken the renderer boundary. Store binary data in the canonical template JSON; rejected because it duplicates assets and bypasses object-store limits. Embed assets only in the browser; rejected because the generated PDF must be authoritative.
- **Consequences:** Uploaded PNG/JPEG/GIF/WebP/SVG images are available to the isolated PDF renderer without network access. Data URI expansion counts against existing bounded HTML/output limits; broad image parser/malware coverage and final reader fidelity remain open.
- **Validation:** PDF endpoint regression passed (`6 passed` in `tests/test_pdf_render.py`); the browser upload→save→generate-PDF flow passed (`1 passed`) against rebuilt Compose; frontend build passed during the image change. The PDF report remains `candidate` with native-reader review pending.
- **Implementation/evidence:** [PDF route](../backend/app/main.py), [PDF renderer](../backend/app/pdf_render.py), [sandbox](../backend/app/process_sandbox.py), [backend regression](../backend/tests/test_pdf_render.py), [browser regression](../frontend/tests/foundation.spec.ts), [template contract](template-contract.md).

- **Operational follow-up:** Set the local `job_memory_bytes` default to 768 MiB so the packaged Chromium child can run within the existing Compose worker memory ceiling. This is a resource-execution adjustment, not evidence of PDF fidelity or native-reader acceptance.
- **Runtime follow-up:** Chromium/Node PDF children do not inherit the Python `RLIMIT_AS` cap because Node's WebAssembly runtime fails under any finite inherited address-space limit. They remain in the credential-free isolated worker, retain CPU, wall-time, output-size and network-denial controls, and are bounded by the Compose worker memory ceiling. This limitation remains explicit for future native per-engine memory enforcement.

# DD-209 — Preserve image alignment and remove component references in the editor

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; broader component lifecycle and final PDF fidelity remain partial
- **Affected stories:** E2-01, E2-03, E2-10, E2-11, E6-01
- **Context:** The editor stored alignment for ordinary text, but its image serialization branch omitted `align`, and newly added images could inherit stale multi-selection state, so centered images could revert to the renderer default. Reusable component instances could be inserted but had no clearly discoverable per-instance removal control.
- **Choice:** Persist the image alignment value, clear stale selection when inserting an image, and render the image at its requested width inside a full-width figure using the same `text-align` primitive that centers text. Add a direct `Remove component: <name>` action for every component instance, an always-visible component removal control that falls back to the first component instance when focus is stale, and a `Delete selected block` action for any selected template block; each changes only the current draft until the owner saves it.
- **Alternatives:** Infer alignment from surrounding HTML or apply arbitrary CSS; rejected because the template contract must remain explicit and bounded. Delete the reusable component record when removing an instance; rejected because that would unexpectedly affect other templates and exceed the requested scope. Provide only a component-specific deletion workflow; rejected because owners also need a clear escape hatch for image, table and text blocks.
- **Consequences:** Image alignment is preserved consistently in server preview and candidate PDF input, and owners can remove an inserted component without destroying the reusable definition. The PDF engine remains a candidate and component versioning/dependency management is not claimed.
- **Validation:** The current rebuilt Compose evidence includes the real Chromium PDF content-stream assertion that the image transform is at the content midpoint; the focused image/component/copy browser set passed (`6 passed`), and the complete Playwright suite passed (`38 passed`). The backend suite passed (`216 passed, 8 skipped, 3 warnings`), and the frontend production build passed. Native-reader approval remains pending, but the generated PDF artifact has coordinate-level centering evidence.
- **Implementation/evidence:** [editor serialization and removal action](../frontend/src/main.tsx), [translations](../frontend/src/i18n.ts), [editor styles](../frontend/src/editor.css), [renderer](../backend/app/rendering.py), [renderer tests](../backend/tests/test_template_logic.py), [browser tests](../frontend/tests/foundation.spec.ts), [template contract](template-contract.md).

# DD-211 — Sequence the next 20 story slices by the implementation plan

- **Date:** 2026-09-25
- **Status:** Accepted and In Progress; this records sequencing, not completion of the listed acceptance criteria
- **Affected stories:** E4-01, E1-06, E1-07, E1-08, E1-09, E1-10, E1-11, E1-12, E2-04, E2-07, E2-08, E2-09, E2-10, E2-11, E2-12, E2-13, E2-14, E2-15, E2-16, E3-08
- **Context:** The implementation plan defines delivery groups and prerequisites rather than a literal numbered “next 20” queue. The user requested the next 20 sequenced stories after the current defect work.
- **Choice:** Use the plan’s M0/M1 order: finish the E4-01 rendering feasibility evidence first, then carry the E1 foundation and operational slices, followed by the remaining E2 editor/rendering slices and E3-08 template sync. Preserve source release and priority assignments; keep native-reader, licence, accessibility, deployment and historical-upgrade gates partial until their evidence exists.
- **Alternatives:** Select the twenty lowest numeric IDs; rejected because it would revisit already implemented MVP stories and ignore the plan’s E4 prerequisite. Treat partial status as complete; rejected because the repository explicitly distinguishes candidate evidence from native-reader, licence and deployment acceptance. Implement R2/R4 infrastructure ahead of M0/M1 gates; rejected because it would reorder source delivery without an accepted product decision.
- **Consequences:** Work has a traceable order and explicit evidence boundaries. Some slices may improve implementation and tests without being promoted to `implemented` until their source acceptance is actually met.
- **Validation:** Sequencing is derived from [implementation plan](implementation-plan.md), [source stories](epics.md), and [story status overlay](../frontend/src/storyStatus.ts). The E4-01 candidate comparison was regenerated against the current renderer for the script-matrix and page-flow fixtures, producing reproducible HTML/PDF/PNG hashes with Chromium 153.0.8010.12; native-reader and human visual scores remain intentionally pending. Completion evidence will be appended as each story slice is implemented.
- **Implementation/evidence:** [implementation plan](implementation-plan.md), [story status](../frontend/src/storyStatus.ts).
# DD-212 — Expose bounded rendering contracts through the template editor

- Date: 2026-09-25
- Status: Accepted and In Progress
- Affected story IDs: E2-12, E2-14, E2-15, E2-16
- Context: The renderer already supported bounded theme variables, data-image page backgrounds, charts, and table-of-contents output, but the editor did not persist or expose these contracts. This made the features inaccessible through the required UI workflow.
- Choice: Add editor controls for a bounded accent color and local page-background image, plus add chart and TOC block insertion actions. Persist only the existing data-only fields (`theme.accent`, `page.background`, and bounded chart/TOC block fields); do not add arbitrary CSS, script execution, external URLs, or a new rendering dependency.
- Alternatives considered: Leave the capabilities API-only (does not satisfy the editor workflow); add a general CSS editor (unsafe and outside the bounded template contract); add client-side chart rendering (would create editor/PDF divergence).
- Consequences: The editor can create and save these bounded blocks/settings and the server preview exercises the same renderer used by PDF generation. More detailed chart and anchor authoring controls remain follow-up work; acceptance remains partial until those controls and required visual/native-reader evidence are complete.
- Validation: `npm run build` passed; the focused Playwright regressions passed (image-centering PDF, chart/TOC/background, component removal/update, deletion, and keyboard flows); the full backend suite passed (199 passed, 6 skipped, 3 warnings). Native-reader review and broad visual approval remain pending.
- Implementation references: `frontend/src/main.tsx`, `frontend/src/i18n.ts`, `frontend/tests/foundation.spec.ts`.
# DD-213 — Make repository template sync idempotent for CI

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E3-08
- Context: The repository sync helper could pull a portable definition but its push path always attempted template creation, so a second CI run against the same template ID failed with a conflict.
- Choice: Before push, perform a read-only template lookup. Create the explicit template ID when absent; otherwise append a version through the existing version API with a fixed sync change summary. Keep repository sync outside document workers and do not execute Git commands or access credentials from the API.
- Alternatives considered: Delete and recreate templates (loses version history); mutate database files directly (bypasses API governance); invoke Git in the service (expands credential/network scope).
- Consequences: Repeated CI pushes are deterministic and preserve template version history. Authentication, conflict policy, signed commits, and a live remote Git integration remain outside this partial slice.
- Validation: Isolated repository-tool tests passed (2 tests); the template/render focus passed (35 tests including 3 warnings); the full backend suite passed (199 passed, 6 skipped, 3 warnings). E3-08 remains partial because no live CI repository or multi-user conflict test is claimed.
- Implementation references: `scripts/sync_templates.py`, `backend/tests/test_repository_tools.py`, `docs/design-decisions.md`.
# DD-214 — Make local backup restore testable and archive-safe

- Date: 2026-09-25
- Status: Accepted and Implemented as partial slices
- Affected story IDs: E1-10, E1-11
- Context: The operational scripts existed, but backup creation/restore and retention behavior had no automated evidence; archive extraction also needed an explicit traversal boundary.
- Choice: Factor backup and restore into callable functions, validate the backup manifest, reject archive members outside the target directory, and use the standard data extraction filter. Keep PostgreSQL dump/restore as the explicit external command and keep retention as a dry-run-capable operator command.
- Alternatives considered: Extract archives without validation (unsafe); silently restore incompatible formats (ambiguous); add an in-application scheduler now (requires unresolved object-store scheduling semantics).
- Consequences: Local operators have testable, safer primitives and retention behavior is covered in both dry-run and deletion modes. Historical-release restore, S3 scheduling, and production-disaster recovery remain unverified.
- Validation: Repository-tool suite passed 5 tests; the full backend suite passed (199 passed, 6 skipped, 3 warnings); script compilation and `git diff --check` passed. E1-10 and E1-11 remain partial because disposable-PostgreSQL restore and scheduled production retention evidence are not claimed.
- Implementation references: `scripts/backup_restore.py`, `scripts/purge_retention.py`, `backend/tests/test_repository_tools.py`.
# DD-215 — Make editor multi-selection actionable for reusable components

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E2-10, E2-11
- Context: The editor retained `selectedBlockIds` for alignment and component creation, but the block list had no modifier-click path to populate that selection and no UI action to update an existing reusable component.
- Choice: Use Control/Command-click on block grip buttons for additive/toggle selection, keep the active block explicit, and expose an update action that sends the selected non-component blocks to the existing component `PUT` endpoint. Keep component references versioned and preserve the renderer’s expand-at-render-time behavior.
- Alternatives considered: Infer selection from focus (ambiguous for text editing); update component definitions locally only (would not affect other templates); add drag-based selection (more interaction surface without improving keyboard access).
- Consequences: Owners can select content and update a reusable component through the UI; cross-template propagation still depends on a subsequent render and the broader component governance screen remains incomplete.
- Validation: Frontend build passed; Playwright component-update, component-removal, keyboard undo/redo, image-PDF, and chart/TOC regressions passed. E2-10/E2-11 remain partial pending broader browser/accessibility and cross-template evidence.
- Implementation references: `frontend/src/main.tsx`, `frontend/src/i18n.ts`, `frontend/tests/foundation.spec.ts`.
# DD-216 — Model database and independent worker pools in the Helm chart

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E1-08
- Context: The initial chart rendered the web Deployment but omitted the PostgreSQL workload and the independently scalable render/extraction worker processes that the Compose deployment already defined.
- Choice: Add a single-replica PostgreSQL StatefulSet with a persistent volume claim and headless Service, and generate one worker Deployment per configured worker kind from `values.yaml`. Workers use the existing `app.worker_service` entrypoint and receive the same database configuration contract as the web service.
- Alternatives considered: Keep database/worker resources implicit (install would not be self-contained); run workers inside the web pod (loses independent scaling and failure boundaries); add a managed database assumption (outside the self-hosted chart scope).
- Consequences: The chart now expresses the intended web/database/worker topology and worker replica values are meaningful. Secrets, network policies, migration ordering, image pinning, and a live cluster smoke test remain follow-up gates; the chart is not claimed production-ready.
- Validation: Static chart-contract regression passed; Helm lint/template and Kubernetes smoke validation remain pending because Helm and a cluster are not installed in this environment.
- Implementation references: `charts/docplatform/templates/postgres.yaml`, `charts/docplatform/templates/worker.yaml`, `charts/docplatform/values.yaml`, `backend/tests/test_repository_tools.py`.
# DD-217 — Add an executable offline-bundle input verifier

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E1-09
- Context: The offline manifest documented required images and checks, but no command validated those inputs or worked consistently from repository and backend working directories.
- Choice: Add a shell-independent Python verifier that validates the manifest format and runtime network policy, optionally inspects required local Docker images, and runs `docker compose config --quiet`. Resolve default paths from the repository root and expose an explicit image-inspection skip only for contract testing.
- Alternatives considered: Treat the manifest as verification (indirect and insufficient); download assets during verification (violates offline intent); make image inspection mandatory in unit tests (couples tests to a local Docker daemon).
- Consequences: Operators get a repeatable preflight check with clear failure output. Fonts/models remain explicitly unbundled, and the command does not claim a network-isolated install or licence approval.
- Validation: Offline verifier passed from both repository-root and backend working directories with the pinned PostgreSQL image present; its focused tests passed (8 tests); the full backend suite passed (202 passed, 6 skipped, 3 warnings); full offline installation remains unverified.
- Implementation references: `scripts/verify_offline_bundle.py`, `templates/docplatform-offline-bundle.json`, `docs/local-development.md`, `backend/tests/test_repository_tools.py`.
# DD-218 — Expose bounded anchors through the editor for TOC generation

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E2-16
- Context: The renderer supported safe same-document TOC links and declared anchors, but the editor exposed only TOC insertion and gave users no way to author the anchor metadata needed to populate it.
- Choice: Add active-block controls for a bounded anchor ID, TOC label, and level (1–6), persist them through the existing text-block contract, and keep link generation restricted to validated same-document anchors.
- Alternatives considered: Infer anchors from arbitrary text (unstable and collision-prone); accept raw URLs (outside the story and expands navigation scope); claim page-number references before pagination is selected (unsupported by current evidence).
- Consequences: Owners can create a structural TOC in the UI and the server preview exposes the resulting link. Pagination-derived page numbers and final PDF cross-reference fidelity remain partial.
- Validation: Frontend build and rebuilt Compose stack passed; Playwright verified the saved anchor metadata, rendered anchor, and TOC link. E2-16 remains partial pending pagination and final-output evidence.
- Implementation references: `frontend/src/main.tsx`, `frontend/src/i18n.ts`, `frontend/tests/foundation.spec.ts`, `backend/app/rendering.py`.
# DD-219 — Emit distinct bounded SVG geometry for chart types

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E2-14
- Context: The chart contract accepted `bar`, `line`, and `pie`, but the renderer emitted bar rectangles for every accepted value, so the type selector did not affect output.
- Choice: Emit bounded rectangles for bars, a polyline with points for lines, and sanitized numeric SVG arc paths for pies. Keep all geometry generated locally from at most the existing bounded data set; do not add a chart dependency or permit arbitrary SVG.
- Alternatives considered: Reject line/pie until a dependency is approved (would leave the exposed contract misleading); use a chart library (adds licence/dependency review); accept user SVG (unsafe and outside the declarative contract).
- Consequences: The editor and server preview now preserve meaningful chart-type semantics. Color/theme, pagination, PDF font embedding and native-reader/chart accessibility remain partial.
- Validation: Chart geometry tests passed for all three types; frontend build passed; the rebuilt browser test verified the editor’s line selection persists and renders a polyline; the full backend suite passed (203 passed, 6 skipped, 3 warnings). E2-14 remains partial pending final PDF and reader evidence.
- Validation update: The full backend suite subsequently passed (204 passed, 6 skipped, 3 warnings); the prior chart-specific evidence remains valid.
- Implementation references: `backend/app/rendering.py`, `backend/tests/test_template_logic.py`, `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts`.
# DD-220 — Separate worker-pool completion tests from throughput benchmarks

- Date: 2026-09-25
- Status: Accepted and Implemented
- Affected story IDs: E12-03
- Context: The full backend suite exposed a host-sensitive assertion requiring two Windows worker threads to finish faster than one; one run measured 3.374s for two workers versus 3.017s for one even though both completed successfully. The repository already has a repeatable Compose benchmark for comparative throughput evidence.
- Choice: Keep the real isolated-job test responsible for successful completion at both pool sizes, and leave comparative timing to `scripts/benchmark_compose_workers.py`, which records repeated samples and medians. Do not make a single-process Windows test a throughput gate.
- Alternatives considered: Increase the job count until this host happens to pass (would remain timing-sensitive); delete the test (loses worker-pool execution coverage); claim throughput from topology alone (insufficient acceptance evidence).
- Consequences: Full-suite results are stable across host scheduling variance while the benchmark remains the authoritative performance evidence. E12-03 remains partial unless the benchmark evidence meets the current documented acceptance boundary.
- Validation: The revised worker-pool test and full backend suite passed (204 passed, 6 skipped, 3 warnings) after removing the host-sensitive ordering assertion; no new universal throughput claim is made.
- Implementation references: `backend/tests/test_jobs.py`, `scripts/benchmark_compose_workers.py`, `docs/design-decisions.md`.
# DD-221 — Add a manual, API-key-scoped CI template sync workflow

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E3-08
- Context: The sync helper was idempotent and tested, but there was no repository workflow showing a safe CI invocation. Automatic pushes would require an explicit conflict, authentication, and deployment policy.
- Choice: Add a manual GitHub Actions workflow accepting a base URL and comma-separated template IDs, read the API key only from `DOCPLATFORM_SYNC_API_KEY`, grant read-only repository contents permission, and invoke the existing sync helper. Add optional API-key headers to pull and push requests.
- Alternatives considered: Run on every push (could publish unintended drafts); store the API key in workflow inputs (would expose it); grant write repository permissions (not required for this workflow).
- Consequences: An operator can run a documented repository-to-platform sync without UI access while preserving version history. Remote Git conflict handling, signed commits, approval policy integration, and a live CI run remain unverified.
- Validation: Workflow YAML parses, the repository sync/tool suite passed (9 tests), and the full backend suite passed (204 passed, 6 skipped, 3 warnings); no remote repository or production API key was contacted.
- Implementation references: `.github/workflows/template-sync.yml`, `scripts/sync_templates.py`, `docs/local-development.md`, `backend/tests/test_repository_tools.py`.
# DD-222 — Add core editor accessibility contract coverage

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E2-13
- Context: The editor used labels, roles, and keyboard handlers, but its core controls had no focused browser regression asserting accessible names and keyboard focusability.
- Choice: Add a Playwright contract test for the formatting toolbar, page/structure settings regions, block selection name, focus behavior, and selected-block deletion action. Keep this as evidence for the core interaction contract, not a WCAG conformance claim.
- Alternatives considered: Claim WCAG 2.2 AA from static markup; rejected because assistive-technology, contrast, zoom, error, and full keyboard audits remain necessary. Add an unreviewed accessibility dependency; deferred pending dependency/licence review.
- Consequences: Regressions that remove names or keyboard focus from these controls are caught in browser tests. Full accessibility acceptance remains partial.
- Validation: The focused Playwright accessibility contract passed; no WCAG certification or assistive-technology review is claimed.
- Implementation references: `frontend/tests/foundation.spec.ts`, `frontend/src/main.tsx`, `docs/design-decisions.md`.
# DD-223 — Verify code-block output through the browser PDF route

- Date: 2026-09-25
- Status: Accepted and Implemented as a partial slice
- Affected story IDs: E2-04
- Context: The editor and server preview already exercised QR, Code 128, and EAN-13 SVG generation, but the browser regression stopped before calling the dedicated PDF endpoint.
- Choice: Extend the fresh-template browser flow to select each code type, save and inspect its server SVG, then call `Generate PDF` and assert a successful nontrivial PDF response for each type. Keep scanner/device acceptance separate from artifact-generation evidence.
- Alternatives considered: Assert only the HTML preview (misses the production output boundary); claim scanner compatibility from SVG presence (unsupported); use the polluted shared sample fixture (causes unrelated block-limit failures).
- Consequences: All three editor code types now have UI-to-dedicated-PDF route coverage on a fresh template. Final-engine scan fidelity remains partial.
- Validation: The Playwright code-format/PDF regression passed for QR, Code 128, and EAN-13; native scanner acceptance is not claimed.
- Implementation references: `frontend/tests/foundation.spec.ts`, `frontend/src/main.tsx`, `backend/app/codes.py`, `backend/app/pdf_render.py`.
# DD-224 - Persist bounded theme font and spacing tokens through rendering

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E2-12 remains partial pending broader typography acceptance
- **Affected stories:** E2-12
- **Context:** Theme accent and page background were already persisted, but font family and paragraph spacing were not configurable at the theme level. Renderer CSS must remain bounded and must not accept arbitrary CSS or network-bearing values.
- **Choice:** Add UI controls for a small font-family selection and numeric spacing range 0.8–2.0. Persist `theme.font_family` and `theme.spacing`; render them through validated CSS variables with safe fallbacks.
- **Alternatives:** Allow arbitrary CSS theme values; rejected because templates must not execute or inject unbounded CSS. Apply only editor-local styles; rejected because generated HTML/PDF would diverge from the saved template contract.
- **Consequences:** Theme typography now reaches the server preview and generated document path. Full multilingual font coverage, native-reader approval and visual design acceptance remain unverified.
- **Validation:** Backend theme tests pass for valid and invalid values; frontend typecheck/Vite build passes. The browser regression saves Georgia/1.8 and asserts both CSS variables in the server preview.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [renderer](../backend/app/rendering.py), [frontend regression](../frontend/tests/foundation.spec.ts), [renderer tests](../backend/tests/test_template_logic.py), [story status](../frontend/src/storyStatus.ts).
# DD-225 - Exercise recent migration boundaries without claiming historical-release coverage

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E1-07 remains partial
- **Affected stories:** E1-07
- **Context:** Migration tests previously covered the initial `0001_templates` revision and current head, but did not exercise the recent pre-head boundaries. The source story requires upgrades from the previous two product releases, while this repository has one commit and no release database fixtures.
- **Choice:** Add an integration regression from `0010_review_events` and `0011_correction_snapshots` to head, preserving a representative template row and metadata. Keep the status partial until historical release artifacts are supplied.
- **Alternatives:** Treat migration revision numbers as product releases; rejected because schema revisions do not prove released application compatibility. Fabricate old database fixtures; rejected because that would be false evidence. Leave the chain untested at recent boundaries; rejected because the regression is useful and low-risk.
- **Consequences:** Recent migration compatibility is exercised and data preservation is explicit. Historical release upgrade, rollback policy and zero-downtime deployment evidence remain open.
- **Validation:** Added a parameterized PostgreSQL integration test in `backend/tests/test_foundation.py`; it runs when the isolated `TEST_DB_PORT` fixture is configured and is reported as skipped otherwise.
- **Implementation/evidence:** [migration tests](../backend/tests/test_foundation.py), [migration guide](e1-foundation.md), [migration implementation](../backend/app/migrations.py).
# DD-226 - Verify chart blocks through the dedicated PDF generation route

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E2-14 remains partial pending embedded-font and native-reader evidence
- **Affected stories:** E2-14
- **Context:** Chart tests previously proved bounded SVG geometry in the renderer and the editor server preview, but did not exercise the dedicated production PDF action for a chart-authored template.
- **Choice:** Extend the browser regression to save a fresh chart template, invoke `/render-pdf`, assert a valid PDF base64 signature and report, and verify the generated PDF iframe appears.
- **Alternatives:** Assert only the preview SVG; rejected because it bypasses the output boundary. Inspect only a PDF byte signature; rejected because it would not prove editor-to-endpoint wiring. Claim chart accessibility or embedded-font correctness; rejected because those require separate reader/font evidence.
- **Consequences:** The chart path now has end-to-end UI-to-PDF candidate evidence. Native chart rendering, embedded font coverage and reader acceptance remain explicitly open.
- **Validation:** The focused Playwright chart/theme test exercises the save, server preview and PDF endpoint; backend renderer tests cover bar, line and pie geometry.
- **Implementation/evidence:** [browser regression](../frontend/tests/foundation.spec.ts), [renderer tests](../backend/tests/test_template_logic.py), [PDF route](../backend/app/main.py).
# DD-227 - Make the Helm chart renderable by defining referenced helpers

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E1-08 remains partial pending Helm and cluster evidence
- **Affected stories:** E1-08
- **Context:** The chart templates referenced `docplatform.name` and `docplatform.labels`, but the helper template was absent. Static resource checks did not detect that rendering failure.
- **Choice:** Add the standard local name and label helpers and extend the chart contract test to require them and the application chart metadata.
- **Alternatives:** Remove the helper references and duplicate labels; rejected because duplication increases drift. Claim the static test was sufficient; rejected because an unresolved template reference prevents installation.
- **Consequences:** Helm has the definitions required to render the current chart resources. Actual `helm lint`, Kubernetes installation, scaling and readiness smoke tests remain unverified because Helm and a cluster are not available on this host.
- **Validation:** Added helper-presence assertions to `backend/tests/test_repository_tools.py`; the test is runnable offline. Tool availability was checked and recorded: Helm unavailable; kubectl client present but no cluster test was run.
- **Implementation/evidence:** [helpers](../charts/docplatform/templates/_helpers.tpl), [chart contract test](../backend/tests/test_repository_tools.py), [chart](../charts/docplatform).
# DD-228 - Correct the documented non-Docker startup contract

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E1-12 remains partial pending a full local hot-reload integration run
- **Affected stories:** E1-12
- **Context:** The local-development guide invoked `app.main:app`, but the service exposes the application through the `create_app` factory. The frontend development server also needed an explicit loopback host while its Vite proxy routes API and health calls.
- **Choice:** Document Uvicorn's `create_app --factory` startup and pin the Vite dev command to `127.0.0.1`; add a contract test tying the guide to the Vite proxy configuration.
- **Alternatives:** Add a second global `app` object; rejected because it would bypass the existing settings/dependency factory. Direct the browser to the backend without a proxy; rejected because it changes the contributor workflow and origin behavior.
- **Consequences:** The documented commands now match the actual application entrypoint and local proxy. A complete hot-reload run still requires PostgreSQL and an operator-managed local dependency environment.
- **Validation:** Added `test_local_development_guide_uses_factory_reload_and_vite_proxy` to the repository-tools suite; no claim is made for an unavailable local PostgreSQL instance or a long-running hot-reload session.
- **Validation update (2026-09-25):** Started the documented Uvicorn factory command on an isolated port with the repository virtual environment. `/health/live` returned HTTP 200; `/health/ready` returned the expected 503 because no local PostgreSQL instance was configured. The process shut down cleanly; full readiness and Vite proxy acceptance still require PostgreSQL.
- **Implementation/evidence:** [local-development guide](local-development.md), [Vite config](../frontend/vite.config.ts), [contract test](../backend/tests/test_repository_tools.py).
# DD-229 - Require explicit offline asset and verification declarations

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E1-09 remains partial pending a real network-isolated installation
- **Affected stories:** E1-09
- **Context:** The offline manifest documented fonts/models and verification commands, but the verifier accepted manifests that omitted both fields. That made an incomplete preflight contract look valid.
- **Choice:** Require non-empty `fonts_and_models` and `verification` fields in the verifier, while allowing the value to explicitly state that assets are not bundled.
- **Alternatives:** Assume missing fields mean no assets are needed; rejected because rendering/OCR assets are unresolved dependencies. Require bundled fonts/models immediately; rejected because licence and engine review remain open.
- **Consequences:** Offline preflight output now proves that asset and verification policy was declared, without overstating installation or licensing evidence.
- **Validation:** Added a rejection regression and updated the valid-manifest test; the repository’s offline verifier test suite remains runnable without network access.
- **Implementation/evidence:** [verifier](../scripts/verify_offline_bundle.py), [manifest](../templates/docplatform-offline-bundle.json), [tests](../backend/tests/test_repository_tools.py).
# DD-230 - Schedule retention through operator-owned one-shot jobs

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E1-11 remains partial for S3 scheduling and production-run evidence
- **Affected stories:** E1-11
- **Context:** The retention command safely purged local files and supported dry runs, but no documented schedule existed. Embedding a daemon in the web process would couple deletion policy to application availability and make deployment semantics ambiguous.
- **Choice:** Keep purge one-shot and document cron and Windows Task Scheduler invocations, with a required dry-run rehearsal and separate local roots for uploads/outputs. Leave S3 lifecycle scheduling to the storage operator.
- **Alternatives:** Add an in-process scheduler; rejected because it creates duplicate execution and lifecycle coupling. Claim Compose restart as scheduling; rejected because restarts are not retention policy. Purge S3 through local filesystem code; rejected because object-store semantics differ.
- **Consequences:** Operators have explicit repeatable schedules and an auditable dry-run step. Scheduled production execution, S3 lifecycle configuration and deletion reporting remain open.
- **Validation:** Added a documentation contract test to the repository-tools suite; existing dry-run/deletion tests cover the command behavior.
- **Implementation/evidence:** [retention command](../scripts/purge_retention.py), [schedule guide](local-development.md), [tests](../backend/tests/test_repository_tools.py).
# DD-231 - Expose editor multi-selection state to assistive technology

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E2-13 remains partial pending a full WCAG/assistive-technology audit
- **Affected stories:** E2-13
- **Context:** Block grips were keyboard-focusable and named, but their selected/unselected state was not exposed. This made modifier-based multi-selection invisible to semantic consumers.
- **Choice:** Add `aria-pressed` to each block-selection grip, driven by the same `selectedBlockIds` state used by alignment and component-update actions. Add a browser regression that verifies the state before and after modifier selection.
- **Alternatives:** Encode selection only through CSS; rejected because it is not available to screen readers. Use `aria-selected` on a non-listbox structure; rejected because the controls are buttons and pressed-state semantics match their interaction.
- **Consequences:** Keyboard and assistive-technology consumers can observe selection state. Contrast, zoom, screen-reader narration and full WCAG 2.2 AA conformance remain unverified.
- **Validation:** Frontend typecheck/build and the core Playwright accessibility regression cover focus, accessible names, deletion state and multi-selection state.
- **Implementation/evidence:** [editor](../frontend/src/main.tsx), [browser regression](../frontend/tests/foundation.spec.ts), [status overlay](../frontend/src/storyStatus.ts).
# DD-232 - Carry the resolved preview locale into PDF generation evidence

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E2-08 remains partial pending shaping and native-reader parity
- **Affected stories:** E2-08
- **Context:** The editor sent the selected locale to server preview and PDF generation, but the PDF response did not expose the resolved locale, so the UI regression could not prove both paths used the same locale.
- **Choice:** Add `report.render_locale` from the isolated render result and assert it in both the API test and browser locale/PDF flow.
- **Alternatives:** Infer locale from the request in the browser; rejected because the server may normalize or default it. Claim parity from the preview HTML `lang` alone; rejected because it does not exercise the PDF route.
- **Consequences:** Integrators can observe the resolved candidate-render locale and the regression covers preview-to-PDF propagation. Glyph shaping, font coverage and native-reader parity remain open.
- **Validation:** Added API and Playwright assertions for `de-DE`; existing renderer and PDF tests remain applicable.
- **Implementation/evidence:** [PDF route](../backend/app/main.py), [PDF tests](../backend/tests/test_pdf_render.py), [editor regression](../frontend/tests/foundation.spec.ts), [editor type](../frontend/src/main.tsx).
# DD-233 - Composite locked PDF page backgrounds in the isolated output path

- **Date:** 2026-09-25
- **Status:** Accepted and Implemented; E2-15 remains partial pending broader page-size/reader visual evidence
- **Affected stories:** E2-15
- **Context:** Page backgrounds supported data-image rasters in HTML, but the story requires an existing PDF page as a locked background. The generated foreground PDF must receive that page without granting templates code or network access.
- **Choice:** Add a pinned `pypdf` runtime dependency and merge a validated `data:application/pdf;base64,` background behind each generated PDF page. Scale the background proportionally to cover the foreground page and reuse the last background page when the foreground has more pages. Expose a PDF upload control in the editor.
- **Alternatives:** Rasterize PDF pages through an unpinned OS binary; rejected because availability and licensing would vary. Embed a browser PDF iframe; rejected because it is not part of printed page output. Accept remote PDF URLs; rejected by the offline/network boundary.
- **Consequences:** Owners can provide a local locked PDF background and the generated PDF contains composited pages. The dependency is recorded for licence review; multi-size visual corpus, crop policy review and native-reader fidelity remain partial.
- **Validation:** Added unit coverage for scaling/merging and invalid input, plus a browser upload/save/generate-PDF regression. `pypdf==6.1.3` was inspected from its wheel; its BSD-style licence remains subject to the unresolved project allow-list.
- **Implementation/evidence:** [PDF compositor](../backend/app/pdf_background.py), [PDF route](../backend/app/main.py), [editor](../frontend/src/main.tsx), [backend tests](../backend/tests/test_pdf_render.py), [browser regression](../frontend/tests/foundation.spec.ts), [dependency review](dependencies.md).
## DD-234: Verify repository template sync through the export boundary

- **Date:** 2026-09-25
- **Status:** Implemented for the bounded local sync slice; live repository CI and multi-user conflict handling remain partial.
- **Affected stories:** E3-08
- **Context:** The repository sync command already pushed JSON definitions and pulled template exports, but tests only covered push create/update behavior and the workflow text. That left the pull archive-to-plain-file contract and API-key propagation unverified.
- **Choice:** Add a mocked HTTP round-trip test for `pull` that supplies a portable ZIP containing `manifest.json` and `definition.json`, then verifies the saved ZIP, decoded JSON definition, export URL, method and `x-api-key` header. Keep the command shell-free and preserve the existing manual workflow boundary.
- **Alternatives:** Treat workflow presence as sufficient evidence; rejected because it does not exercise archive extraction or request construction. Add a live repository test; deferred because no repository credentials or external CI target is in scope.
- **Consequences:** The local sync contract now has executable evidence for both push and pull paths. The story remains partial for live CI integration, conflict policy, signed commits and multi-user coordination.
- **Validation:** `pytest -q backend/tests/test_repository_tools.py` passes with the new pull test; full backend validation remains the existing suite evidence.
- **Implementation references:** [sync command](../scripts/sync_templates.py), [repository-tool tests](../backend/tests/test_repository_tools.py), [workflow](../.github/workflows/template-sync.yml).
## DD-235: Verify TOC links in the generated PDF, not only in HTML preview

- **Date:** 2026-09-25
- **Status:** Implemented as a partial E2-16 evidence slice.
- **Affected stories:** E2-16
- **Context:** The editor and server-preview tests verified bounded anchor metadata and same-document HTML links, while the story concerns generated documents whose page references must survive output rendering.
- **Choice:** Add a Chromium PDF regression that parses the generated PDF annotations and requires a link annotation targeting the declared `/intro` anchor. Keep page-number assertions out of scope until pagination and final reader review are established.
- **Alternatives:** Assert only the HTML `href`; rejected because the PDF engine can transform or drop annotations. Claim page numbers from the anchor destination; rejected because the current contract emits named destinations and does not yet prove pagination numbering.
- **Consequences:** E2-16 now has output-level evidence for named TOC navigation. Dynamic page-number updates and native-reader review remain partial.
- **Validation:** The focused PDF suite passes, including centered-image geometry, page-background compositing and the generated-PDF TOC annotation test.
- **Implementation references:** [PDF tests](../backend/tests/test_pdf_render.py), [renderer](../backend/app/rendering.py), [anchor decision](design-decisions.md#dd-218--expose-bounded-anchors-through-the-editor-for-toc-generation).
## DD-236: Isolate browser editor tests from persisted template mutations

- **Date:** 2026-09-25
- **Status:** Implemented
- **Affected stories:** E2-01, E2-02, E2-03, E2-04, E2-05, E2-06, E2-07, E2-08, E2-10, E2-11, E2-12, E2-13, E2-14, E2-15, E2-16
- **Context:** The browser suite uses a persistent local API database. Tests that edited the shared Welcome letter could change the block set seen by later tests, producing failures unrelated to the behavior under test. Similar-label controls also made substring ARIA queries ambiguous after the locked PDF background control was added.
- **Choice:** Use a fresh Invoice starter for block-insertion/table drag tests that do not need shared-template persistence, and make overlapping label queries exact where the test targets a specific control. Keep the shared-template tests only where they explicitly exercise reusable component or persisted sample behavior.
- **Alternatives:** Reset the database between every browser test; rejected because it would hide persistence/version behavior and diverge from the deployed test topology. Make product labels unique by removing useful control context; rejected because accessible names should distinguish the controls semantically.
- **Consequences:** The full browser suite now tests each editor contract against deterministic starting blocks while retaining explicit persistence coverage. The suite still runs against the real Compose API and renderer.
- **Validation:** Full Playwright suite passed after the isolation and target-selection fixes; direct image/removal regressions passed independently as well.
- **Implementation references:** [browser tests](../frontend/tests/foundation.spec.ts), [editor](../frontend/src/main.tsx).
## DD-237: Publish a traceability matrix for the sequenced 20 stories

- **Date:** 2026-09-25
- **Status:** Implemented
- **Affected stories:** E4-01, E1-06, E1-07, E1-08, E1-09, E1-10, E1-11, E1-12, E2-04, E2-07, E2-08, E2-09, E2-10, E2-11, E2-12, E2-13, E2-14, E2-15, E2-16, E3-08
- **Context:** DD-211 sequenced the next 20 story slices, but evidence was distributed across individual decision records, source files and tests. A passing slice could otherwise be mistaken for full source-story acceptance.
- **Choice:** Add a dedicated matrix that maps every sequenced ID to its implementation slice, strongest validation evidence and residual acceptance gate. Keep the existing story-status overlay and individual decision records authoritative for status; the matrix is a navigation and audit aid.
- **Alternatives:** Mark every story implemented after its first green test; rejected because several source acceptances require external/native-reader, deployment, calibration or operational evidence. Leave evidence only in individual records; rejected because it makes a 20-story completion audit unnecessarily error-prone.
- **Consequences:** Reviewers can distinguish implemented code from fully accepted source scope and can see exactly what evidence is still missing. No backlog priority, release assignment or acceptance criterion is changed.
- **Validation:** The matrix records the current final evidence: 39 Playwright tests passed, the complete backend suite passed with the isolated PostgreSQL fixture (`232 passed, 3 skipped, 3 warnings`), frontend TypeScript/Vite build passed with 47 modules transformed, and the Must-story audit reported no missing IDs.
- **Implementation references:** [next-20 validation matrix](next-20-validation.md), [sequence decision](design-decisions.md#dd-211--sequence-the-next-20-story-slices-by-the-implementation-plan), [story status overlay](../frontend/src/storyStatus.ts).
## DD-238: Lock the component-removal regression to its disabled-state contract

- **Date:** 2026-09-25
- **Status:** Implemented
- **Affected stories:** E2-10, E2-11
- **Context:** The reported defect was specifically that `Remove component` stayed disabled regardless of which block was selected. The existing removal test proved successful deletion after insertion but did not prove the negative state before an instance existed.
- **Choice:** Add a browser regression that asserts the control is disabled with no component instance, remains disabled after selecting an ordinary block, and becomes enabled only after inserting a reusable component. Keep ordinary-block deletion as a separate action.
- **Alternatives:** Enable removal for every selected block; rejected because it conflates component-instance removal with draft-block deletion. Test only the enabled click path; rejected because it misses the reported failure mode.
- **Consequences:** The UI state contract is now protected at the exact boundary that previously regressed, while the reusable definition remains untouched by instance removal.
- **Validation:** The focused and full Playwright suites pass with this regression included; backend and frontend build validation remain green.
- **Implementation references:** [browser regression](../frontend/tests/foundation.spec.ts), [editor actions](../frontend/src/main.tsx), [component contract](template-contract.md).
## DD-239: Do not claim TOC page numbers from unsupported Chromium CSS

- **Date:** 2026-09-25
- **Status:** Investigated; page-number implementation remains deferred
- **Affected stories:** E2-16, E4-01
- **Context:** E2-16 requires TOC numbers to update after pagination changes. Chromium preserved named `/Dest` link annotations in generated PDFs, but an isolated render experiment showed that `target-counter(attr(href), page)` produces no page-number text in the PDF.
- **Choice:** Keep bounded same-document TOC links and generated named destinations as the verified implementation. Do not inject unsupported CSS or mark page-number acceptance complete. Revisit page numbers only after selecting an engine/API that exposes reliable post-pagination destinations or after adding a tested PDF post-processing layer.
- **Alternatives:** Claim the ordered-list number is the target page; rejected because it is only the entry index. Add a JavaScript pagination approximation; rejected because it would be sensitive to print layout and expand template/runtime behavior. Add a PDF library immediately; deferred pending engine, dependency and text-overlay evidence.
- **Consequences:** The current output remains navigable and safe, but E2-16 is honestly partial for page-number references. The limitation is now tied to reproducible engine evidence rather than an untested assumption.
- **Validation:** Chromium PDF experiment with one TOC link and a forced second-page anchor produced a `/Dest` annotation but no `target-counter` text; the existing PDF annotation regression remains passing.
- **Implementation references:** [renderer](../backend/app/rendering.py), [PDF regression](../backend/tests/test_pdf_render.py), [validation matrix](next-20-validation.md).
## DD-240: Cover all bounded image alignment modes in PDF geometry tests

- **Date:** 2026-09-25
- **Status:** Implemented
- **Affected stories:** E2-03, E2-10
- **Context:** The reported defect was centered-image drift between editor and PDF. The existing Chromium regression proved the center case, but left and right are part of the same bounded image alignment contract and could regress independently.
- **Choice:** Parameterize the real Chromium PDF content-stream assertion across `left`, `center`, and `right`, comparing the image transform against the rendered figure’s content midpoint/edges within the existing three-unit tolerance.
- **Alternatives:** Test only HTML styles; rejected because that misses the PDF transform. Add screenshot-only assertions; rejected because screenshots do not provide a stable coordinate invariant for this defect.
- **Consequences:** All supported image alignment modes now have artifact-level coverage without adding a renderer dependency or changing the document contract.
- **Validation:** The focused PDF suite passes with three alignment cases; the full browser suite continues to assert the uploaded center-image flow and its generated PDF coordinates.
- **Implementation references:** [PDF geometry tests](../backend/tests/test_pdf_render.py), [image renderer](../backend/app/rendering.py), [browser regression](../frontend/tests/foundation.spec.ts).
## DD-241: Resolve TOC page numbers through bounded PDF post-processing

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded candidate-output slice; native-reader review remains pending
- **Affected stories:** E2-16, E4-01
- **Context:** DD-239 established that Chromium does not emit CSS `target-counter()` values, leaving TOC links navigable but unnumbered. The generated PDF does retain named link destinations and page content, which provides a deterministic post-render boundary.
- **Choice:** Emit transparent, aria-hidden anchor markers in the renderer HTML. After Chromium produces the PDF, map each named TOC destination to the page containing its marker and overlay the physical page number beside the corresponding link using a built-in PDF Type1 Helvetica resource. Enforce the existing byte limit and leave documents without matching markers unchanged.
- **Alternatives:** Rely on unsupported CSS counters; superseded by this tested post-processing path. Approximate pages from DOM offsets; rejected because print pagination can differ from screen layout. Add a new PDF drawing dependency; rejected because pypdf is already reviewed and sufficient for the bounded text overlay.
- **Consequences:** Generated PDFs now carry pagination-aware TOC numbers for bounded declared anchors while preserving their link annotations. Hidden markers are transparent and aria-hidden in the source artifact; native-reader/accessibility review remains required before a broad production claim.
- **Validation:** The real Chromium PDF regression forces the anchor onto page 2, runs the post-processor, verifies extracted TOC text contains page `2`, and verifies the `/intro` link annotation remains present. The focused PDF suite passes (`12 passed`).
- **Implementation references:** [TOC post-processor](../backend/app/pdf_toc.py), [renderer](../backend/app/rendering.py), [PDF route](../backend/app/main.py), [PDF tests](../backend/tests/test_pdf_render.py), [superseded limitation](design-decisions.md#dd-239-do-not-claim-toc-page-numbers-from-unsupported-chromium-css).
## DD-242: Report the post-processed PDF size at the API boundary

- **Date:** 2026-09-25
- **Status:** Implemented
- **Affected stories:** E2-15, E2-16
- **Context:** Background compositing and TOC page-number overlays occur after the isolated PDF renderer reports its candidate size. Returning that earlier size makes API diagnostics disagree with the actual downloadable document.
- **Choice:** Recompute `report.output_bytes` after all local PDF post-processing and assert it equals the decoded response payload length.
- **Alternatives:** Keep the renderer’s pre-overlay size; rejected because it is operationally misleading. Add a second size field; rejected because the existing report contract already names the final output size.
- **Consequences:** UI/API diagnostics now describe the exact PDF delivered to the browser, including background and TOC overlays.
- **Validation:** PDF endpoint regression verifies the reported byte count against the returned base64 document; the full backend and browser suites remain green.
- **Implementation references:** [PDF route](../backend/app/main.py), [PDF test](../backend/tests/test_pdf_render.py), [TOC post-processor](../backend/app/pdf_toc.py).
## DD-243: Make the editor snap toggle render bounded alignment guides

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded editor slice
- **Affected stories:** E2-10
- **Context:** The editor exposed a `Snap & guides` toggle, but the state only changed the button and no guide was rendered. That was an incomplete implementation of the visible snapping/alignment affordance.
- **Choice:** Render a non-interactive vertical guide at the active block’s left, center or right alignment position while the toggle is enabled. Alignment commands continue to update the selected blocks through the existing bounded alignment contract.
- **Alternatives:** Add freeform canvas coordinates; rejected because the current document model is flow-based and has no positional contract. Keep the toggle visual-only; rejected because it misrepresents the feature.
- **Consequences:** The editor now provides a truthful visual alignment guide without expanding the template schema or introducing arbitrary canvas geometry. Full drag-snapping and cross-browser visual review remain partial.
- **Validation:** The new Playwright regression verifies left-to-center guide movement and toggle visibility; the full browser suite and frontend build are the remaining integration checks.
- **Implementation references:** [editor](../frontend/src/main.tsx), [editor styles](../frontend/src/editor.css), [browser test](../frontend/tests/foundation.spec.ts).
## DD-244: Verify page-flow behavior in generated PDF output

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded E2-07 evidence slice
- **Affected stories:** E2-07
- **Context:** Preview tests asserted `break-before` and `break-inside` CSS, but did not prove actual multi-page output behavior. The source acceptance concerns orphan/split behavior and repeated table headers in the generated document.
- **Choice:** Add a real Chromium PDF fixture with preceding filler and two bounded table rows, then assert two pages, a repeated `Description` header on each page, and each row appearing wholly on its expected page.
- **Alternatives:** Treat CSS declarations as proof; rejected because the PDF engine can paginate differently. Use only a screenshot; rejected because text/page membership is a more stable invariant for this fixture.
- **Consequences:** The current candidate engine has output-level evidence for this representative row-flow case. Broad corpus coverage, headings with following content, oversized rows and native-reader review remain partial.
- **Validation:** The new real-PDF flow test passes as part of the focused PDF suite and full backend suite.
- **Implementation references:** [renderer](../backend/app/rendering.py), [PDF test](../backend/tests/test_pdf_render.py), [page-flow browser tests](../frontend/tests/foundation.spec.ts).
## DD-245: Verify editor copy/paste through the keyboard path

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded E2-10 evidence slice
- **Affected stories:** E2-10
- **Context:** The editor had Ctrl/Cmd copy and paste handlers, but the browser suite only exercised undo/redo and selection. A shortcut regression was needed to prove the active block is copied and duplicated through the UI.
- **Choice:** Add a fresh-template Playwright test that selects the first block, sends `Control+c` and `Control+v`, and verifies the block count and pasted text.
- **Alternatives:** Test the helper functions directly; rejected because it would bypass browser keyboard dispatch and active-selection state. Test only the clipboard API; rejected because the editor uses an internal bounded clipboard state.
- **Consequences:** A future change that breaks keyboard dispatch, active-block tracking or paste insertion is caught at the browser boundary. Native Cmd behavior on macOS remains outside this Windows run.
- **Validation:** The new browser regression passes with the full frontend suite; frontend build remains required after UI test-only changes.
- **Implementation references:** [editor keyboard handler](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [E2-10 matrix row](next-20-validation.md).

## DD-246: Give the resource-sensitive browser PDF fixture an explicit timeout budget

- **Date:** 2026-09-25
- **Status:** Implemented as test-infrastructure hardening
- **Affected stories:** E2-13, E2-14
- **Context:** The full Playwright run reached 37 passing tests but the existing QR/barcode PDF fixture exceeded the default 30-second test timeout while the same fixture passed in isolation. The failure was a test-budget failure, not evidence that the generated response was invalid.
- **Choice:** Set a 90-second timeout on that browser fixture only, covering three sequential PDF generations while retaining status, SVG and HTTP-200 assertions. Do not increase the global browser timeout or weaken the response checks.
- **Alternatives:** Ignore the full-suite timeout because the isolated run passed; rejected because the suite must be reliable under its normal shared-service load. Increase every test timeout; rejected because unrelated regressions should remain fast. Remove PDF assertions; rejected because they are the story’s output boundary.
- **Consequences:** The suite accommodates the documented local Chromium/PDF resource variance without masking failures in other tests. The timeout is a local development budget, not a performance benchmark or production SLO.
- **Validation:** The fixture passed in isolation before and after the timeout change; the complete Playwright browser suite passed with `38 passed` using the explicit budget.
- **Implementation references:** [browser fixture](../frontend/tests/foundation.spec.ts), [next-20 matrix](next-20-validation.md).

## DD-247: Make reusable-component expansion a directly tested render contract

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded E2-11 evidence slice
- **Affected stories:** E2-11
- **Context:** Component references were expanded at render time, which is the mechanism that makes an update visible to every referencing template, but the recursive rule lived inside the API factory and had no direct regression for cross-template propagation or repeated sibling references.
- **Choice:** Extract the pure deep-copy/expansion rule into `app.components`, retain render-time lookup of the current database definitions, and test propagation, repeated references and cycle rejection directly. Stored template definitions continue to retain component IDs.
- **Alternatives:** Copy component content into each template on insertion; rejected because updates would not propagate. Test only mocked browser fetches; rejected because that would not exercise the render contract. Resolve cycles by silently omitting blocks; rejected because it would produce incomplete documents.
- **Consequences:** The render contract is independently executable and protects the UI’s component removal/update behavior. Database-backed API and native-reader acceptance remain separate gates.
- **Validation:** New component unit tests pass; the existing backend and browser suites remain required for API/editor integration.
- **Implementation references:** [component expansion](../backend/app/components.py), [API integration](../backend/app/main.py), [component tests](../backend/tests/test_components.py), [E2-11 matrix](next-20-validation.md).

## DD-248: Scope component removal to the selected component instance

- **Date:** 2026-09-25
- **Status:** Implemented as an E2-11 UI defect correction
- **Affected stories:** E2-10, E2-11
- **Context:** The toolbar action was enabled if any component existed and fell back to removing the first component when the active block was ordinary. That made selection state misleading and could remove the wrong instance.
- **Choice:** Enable the toolbar action only when the active block is a component and remove exactly that active instance. Keep the per-instance removal buttons as a direct alternative.
- **Alternatives:** Preserve the first-component fallback; rejected because it is not selection-safe. Enable removal for every selected block; rejected because ordinary blocks need the separate Delete Block action.
- **Consequences:** The toolbar state now reflects the selected block and cannot silently remove another component. Existing component insertion and direct per-instance removal remain unchanged.
- **Validation:** Extended the Playwright regression to assert disabled ordinary selection, enabled selected-component state and disappearance of the selected instance after removal.
- **Implementation references:** [editor toolbar](../frontend/src/main.tsx), [browser regression](../frontend/tests/foundation.spec.ts), [next-20 matrix](next-20-validation.md).

## DD-249: Bind backup archives to their PostgreSQL dump by checksum

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-10 integrity slice
- **Affected stories:** E1-10
- **Context:** The backup command created a tar archive and a sibling custom-format PostgreSQL dump, but the manifest recorded only a timestamp. A restore could therefore combine an object archive with an unrelated database dump without detecting the mismatch.
- **Choice:** Run `pg_dump` before writing the tar manifest, record the sibling dump filename and SHA-256 checksum, and preflight the checksum before extracting objects or invoking `pg_restore`. Preserve compatibility with older v1 manifests that lack the optional checksum field.
- **Alternatives:** Put the database dump inside the tar archive; rejected because `pg_dump` already produces a binary artifact and the existing operator layout uses a sibling dump. Trust matching filenames; rejected because filenames do not prove content identity. Restore first and validate later; rejected because it could mutate the database before detecting a bad pairing.
- **Consequences:** New backups fail closed on missing or mismatched database dumps before object extraction/database restore. Legacy manifests remain readable but do not gain retroactive integrity evidence.
- **Validation:** Repository-tool tests cover manifest checksum creation, successful round-trip restore, traversal rejection and checksum mismatch rejection. A live disposable-PostgreSQL run created a custom-format dump, removed a probe table and object, restored both through the command path, and verified the table value and object contents. Production disaster-recovery and object-store restore evidence remains open.
- **Implementation references:** [backup command](../scripts/backup_restore.py), [repository-tool tests](../backend/tests/test_repository_tools.py), [E1-10 matrix](next-20-validation.md).

## DD-261: Keep E1-07 historical upgrades separate from E1-10 backup acceptance

- **Date:** 2026-09-25
- **Status:** Implemented as a traceability correction
- **Affected stories:** E1-07, E1-10
- **Context:** The E1-10 matrix row incorrectly listed historical-version restore evidence as its residual gate. The source backlog assigns previous-release migration tests to E1-07, while E1-10 requires backup/restore reproduction of templates, results and settings.
- **Choice:** Keep historical-release compatibility exclusively under E1-07. Record E1-10’s remaining boundary as production disaster-recovery/object-store execution, while retaining the live disposable-PostgreSQL round-trip evidence for the implementation slice.
- **Alternatives:** Require historical-version dumps for E1-10; rejected because it duplicates E1-07 and changes source-story scope. Remove all residual gates; rejected because a local disposable run is not production disaster-recovery evidence.
- **Consequences:** The 20-story matrix accurately maps residual evidence to the owning story without weakening either acceptance criterion.
- **Validation:** Compared the corrected matrix rows with the source E1-07/E1-10 story definitions; the E1-10 live round-trip evidence remains recorded in DD-249.
- **Implementation references:** [source stories](epics.md), [next-20 matrix](next-20-validation.md), [migration decision](#dd-225--exercise-recent-migration-boundaries-without-claiming-historical-release-coverage), [backup decision](#dd-249-bind-backup-archives-to-their-postgresql-dump-by-checksum).

## DD-250: Make local retention discovery deterministic and symlink-safe

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-11 safety slice
- **Affected stories:** E1-11
- **Context:** The retention command recursively discovered old files but did not state how symlinks were treated and silently did nothing when the configured root was missing. Retention must not use an operator typo or an external symlink target as an apparent successful purge.
- **Choice:** Reject a missing/non-directory root, skip symlinks explicitly, and sort eligible regular files before printing/deleting them. Keep the one-shot dry-run and operator-owned scheduling model.
- **Alternatives:** Follow symlinks; rejected because retention should not operate outside the configured object root. Treat a missing root as empty; rejected because it hides configuration errors. Add an in-process scheduler; rejected under DD-230 because deployment-owned scheduling remains the chosen boundary.
- **Consequences:** Local retention plans are deterministic and cannot delete symlink targets; invalid roots fail before any deletion. S3 lifecycle and scheduled production execution remain outside this local command.
- **Validation:** Repository-tool tests cover dry-run/deletion behavior, old symlink preservation and missing-root rejection; full production scheduling remains an external gate.
- **Implementation references:** [retention command](../scripts/purge_retention.py), [repository-tool tests](../backend/tests/test_repository_tools.py), [E1-11 matrix](next-20-validation.md).

## DD-251: Validate repository template IDs inside the sync command

- **Date:** 2026-09-25
- **Status:** Implemented as an E3-08 safety slice
- **Affected stories:** E3-08
- **Context:** The manual workflow split a comma-separated input in shell and the Python sync command used each ID directly in local filenames. Invalid IDs could escape the intended repository directory or make shell parsing the source of truth.
- **Choice:** Accept repeated or comma-separated IDs, normalize/deduplicate them in Python, and allow only bounded alphanumeric, dot, underscore and hyphen identifiers beginning with an alphanumeric character. Pass the workflow input as one quoted argument and keep the API-key secret boundary unchanged.
- **Alternatives:** Keep shell splitting; rejected because it duplicates parsing and weakens the Python boundary. Accept arbitrary IDs and sanitize filenames after the fact; rejected because the API path and local artifact name should share one explicit identifier contract. Remove multi-ID dispatch; rejected because it is part of the workflow’s operator contract.
- **Consequences:** Repository sync cannot write outside its target directory through a template ID, and workflow parsing is deterministic. Remote Git conflict handling, signed commits and live CI remain outside this slice.
- **Validation:** Repository-tool tests cover multi-ID normalization, deduplication, invalid path rejection and the shell-free workflow shape; live repository CI remains an external gate.
- **Implementation references:** [sync command](../scripts/sync_templates.py), [workflow](../.github/workflows/template-sync.yml), [repository-tool tests](../backend/tests/test_repository_tools.py), [E3-08 matrix](next-20-validation.md).

## DD-252: Name block editors and verify keyboard selection at the browser boundary

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded E2-13 accessibility slice
- **Affected stories:** E2-10, E2-13
- **Context:** The editor exposed named selection grips and toolbar groups, but block textareas themselves had no accessible name and the browser suite did not prove keyboard activation of a block selector.
- **Choice:** Give each block textarea a contextual accessible name and add a Playwright regression that focuses the selection grip, activates it with Enter, and verifies pressed/active state. Keep broader WCAG 2.2 AA and assistive-technology review as separate acceptance gates.
- **Alternatives:** Rely on surrounding visual text; rejected because the textarea has no semantic label. Test only click behavior; rejected because keyboard activation is part of the story. Claim full accessibility from Playwright; rejected because browser automation does not replace screen-reader, keyboard-only and WCAG audit evidence.
- **Consequences:** Core block editing and selection are more discoverable to assistive technology and protected against regressions. Full editor accessibility remains partial.
- **Validation:** The new browser regression and complete Playwright suite are required; frontend build runs through the rebuilt Compose image.
- **Implementation references:** [editor labels](../frontend/src/main.tsx), [browser test](../frontend/tests/foundation.spec.ts), [E2-13 matrix](next-20-validation.md).

## DD-253: Remove embedded patch text from the Helm values document

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-08 defect correction
- **Affected stories:** E1-08
- **Context:** Containerized Helm linting found that `charts/docplatform/values.yaml` contained an accidental `*** Add File` patch fragment and helper-template text after the resource values, making the chart invalid YAML. Static repository tests had only inspected selected strings and did not parse the chart.
- **Choice:** Remove the patch fragment from `values.yaml`, keep the canonical helper definitions in `_helpers.tpl`, and validate the chart with the pinned Helm 3.17.3 container.
- **Alternatives:** Ignore the lint failure because the static tests passed; rejected because the chart could not be installed. Duplicate helpers in `values.yaml`; rejected because values must remain data-only. Claim Kubernetes readiness from lint; rejected because no live cluster smoke test was run.
- **Consequences:** The chart is syntactically lintable and remains a reviewable CPU-only topology definition. Live installation, upgrade, scaling and smoke behavior remain unverified.
- **Validation:** `docker run --rm -v "${PWD}/charts/docplatform:/chart:ro" alpine/helm:3.17.3 lint /chart` passed with zero failed charts; repository chart tests remain required.
- **Implementation references:** [chart values](../charts/docplatform/values.yaml), [Helm helpers](../charts/docplatform/templates/_helpers.tpl), [E1-08 matrix](next-20-validation.md).

## DD-254: Record rendered Helm topology as static deployment evidence

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-08 validation update
- **Affected stories:** E1-08
- **Context:** Helm lint established that the chart parses, but the topology contract also requires independent web, render-worker, extraction-worker and database resources. A rendered manifest gives stronger static evidence without requiring a cluster.
- **Choice:** Render the chart with the pinned Helm 3.17.3 container and retain the output artifact for review. Verify the generated resource kinds and worker commands; keep live install, upgrade, scaling and smoke acceptance separate.
- **Alternatives:** Infer topology from template source only; rejected because values/rendering errors can alter output. Treat `helm template` as a cluster smoke test; rejected because it does not exercise scheduling, probes, storage or networking.
- **Consequences:** The repository now has reproducible lint and rendered-manifest evidence for the intended topology. Cluster behavior and operational readiness remain unverified.
- **Validation:** Helm lint passed and `helm template docplatform /chart --namespace docplatform` produced the expected Service, web Deployment, two worker Deployments and PostgreSQL StatefulSet in [the rendered artifact](../artifacts/helm-template.yaml).
- **Implementation references:** [chart](../charts/docplatform), [rendered manifest](../artifacts/helm-template.yaml), [E1-08 matrix](next-20-validation.md).

## DD-255: Record bounded Compose worker throughput without promoting capacity claims

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-06 evidence slice
- **Affected stories:** E1-06, E12-01
- **Context:** The CPU-only benchmark covered deterministic in-process paths, but the Compose topology also has a PostgreSQL-backed job queue and isolated render workers. A small local run can verify that the real queue/worker path executes and that scaling the render-worker service changes observed throughput.
- **Choice:** Run the existing Compose benchmark with four jobs, 20 HTML blocks and one measured repeat at one and two render workers. Store the report, restore the normal one-worker topology, and label the result as local observed throughput—not a minimum-hardware, OCR/PDF, autoscaling or multi-host capacity claim.
- **Alternatives:** Infer worker scaling from YAML; rejected because it would not exercise the queue or child process. Use a large load test; rejected because no production workload or capacity target was supplied. Claim CPU sizing from HTML-only renders; rejected because OCR/PDF engines and minimum hardware remain open.
- **Consequences:** The repository now has real queue/worker evidence and a reproducible comparison while preserving conservative scope. The benchmark leaves a generated template in local development data and does not replace deployment/load acceptance.
- **Validation:** `scripts/benchmark_compose_workers.py --base-url http://127.0.0.1:8000 --jobs 4 --blocks 20 --repeats 1` observed one-worker median 3.940s and two-worker median 2.532s; Compose was restored to one render worker afterward.
- **Implementation references:** [benchmark script](../scripts/benchmark_compose_workers.py), [benchmark artifact](../artifacts/compose-worker-throughput.json), [foundation guidance](e1-foundation.md), [E1-06 matrix](next-20-validation.md).

## DD-256: Execute migration compatibility tests against isolated PostgreSQL

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-07 evidence update
- **Affected stories:** E1-07
- **Context:** The migration compatibility tests were marked integration-only and had previously been observed as skipped when the isolated test database was not running. The repository already defines a disposable PostgreSQL Compose fixture and dedicated test credentials.
- **Choice:** Start only `compose.test.yaml`’s tmpfs PostgreSQL service, run the six integration-marked tests with `TEST_DB_PORT=55432`, and tear the fixture down afterward. Record the two current pre-head boundaries as executed evidence, without relabeling them as historical product releases.
- **Alternatives:** Count skipped integration tests as migration evidence; rejected because no database transition had executed. Run against the development database; rejected because tests drop/recreate the public schema. Claim previous-release coverage; rejected because release tags and historical databases are absent.
- **Consequences:** Current migration-chain behavior is now verified against real PostgreSQL with isolated credentials and ephemeral storage. Historical-release compatibility remains an explicit gate.
- **Validation:** `pytest -q -m integration` passed `6 passed, 222 deselected, 3 warnings`; `docker compose -f compose.test.yaml down` removed the test container and network afterward.
- **Implementation references:** [migration tests](../backend/tests/test_foundation.py), [test Compose fixture](../compose.test.yaml), [foundation evidence](e1-foundation.md), [E1-07 matrix](next-20-validation.md).

## DD-257: Regression-test locked PDF backgrounds across page geometries

- **Date:** 2026-09-25
- **Status:** Implemented as a bounded E2-15 evidence slice
- **Affected stories:** E2-15
- **Context:** The background merge path had a one-page smoke test, but page-size/orientation changes can expose scaling or mediabox regressions even when the default portrait case passes.
- **Choice:** Add parameterized PDF tests for portrait, landscape and an alternate page size, asserting that compositing preserves the foreground page geometry and emits a readable page content stream. Keep visual reader review and broader background fidelity acceptance separate.
- **Alternatives:** Test only CSS/data-URI persistence; rejected because the final PDF merge is the behavior under test. Assert only that a PDF is returned; rejected because a returned PDF can have the wrong page geometry. Claim proportional visual fidelity from mediabox checks; rejected because human/native-reader review remains necessary.
- **Consequences:** Changes to background compositing are protected across representative page geometries without adding a rendering dependency. Full page-size corpus and native-reader review remain open.
- **Validation:** The new three-case PDF regression passes in the focused PDF suite; full backend validation remains required.
- **Implementation references:** [background merger](../backend/app/pdf_background.py), [PDF tests](../backend/tests/test_pdf_render.py), [E2-15 matrix](next-20-validation.md).

## DD-258: Verify the documented non-Docker hot-reload path against isolated PostgreSQL

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-12 evidence update
- **Affected stories:** E1-12
- **Context:** The repository documented Uvicorn factory reload and a Vite API/health proxy, but prior validation only proved isolated liveness without PostgreSQL-backed readiness. The test Compose fixture provides a safe disposable database for a complete local-path check.
- **Choice:** Initialize the isolated test database, start `uvicorn app.main:create_app --factory --app-dir backend --reload` on port 8010, start Vite on port 5173, and verify direct liveness/readiness plus the proxied seeded-template API. Stop both servers and remove the test database afterward.
- **Alternatives:** Test only process startup; rejected because readiness and proxy routing are the story’s useful boundary. Use the normal development database; rejected because the test fixture resets its schema. Leave servers running; rejected because validation must not leak background processes or temporary data.
- **Consequences:** The documented non-Docker path has current end-to-end evidence for factory reload, PostgreSQL readiness, Vite serving and API proxying. Fresh-machine dependency installation and long-lived edit-triggered reload remain outside this one-shot smoke test.
- **Validation:** Direct liveness, readiness, Vite root and Vite `/api/templates` proxy all returned HTTP 200; the proxy response contained `sample-welcome`; Uvicorn/Vite and the isolated database were stopped afterward.
- **Implementation references:** [local development guide](local-development.md), [Vite proxy](../frontend/vite.config.ts), [E1-12 matrix](next-20-validation.md).

## DD-259: Validate EAN-13 check digits at the code-rendering boundary

- **Date:** 2026-09-25
- **Status:** Implemented as an E2-04 validation hardening slice; E2-04 remains partial
- **Affected stories:** E2-04
- **Context:** The code renderer bounded EAN-13 input to 12 or 13 digits, but a supplied 13-digit value could have an invalid check digit. That allowed malformed barcode input to reach SVG generation and left the contract dependent on library behavior.
- **Choice:** Validate the EAN-13 modulo-10 check digit explicitly. Continue accepting 12-digit payloads, for which the encoder generates the check digit, and retain the existing 1–200 character bound for all code values.
- **Alternatives:** Trust the barcode dependency to reject malformed values; rejected because the application contract should be explicit and stable. Accept arbitrary digit strings; rejected because malformed EAN output is not a valid barcode contract. Add scanner hardware to unit tests; deferred because scanner/device compatibility remains a separate acceptance gate.
- **Consequences:** Invalid 13-digit EAN values fail deterministically before SVG generation, with focused negative coverage for malformed shape, checksum and general value bounds. Scanner acceptance and final-engine fidelity remain unverified.
- **Validation:** Focused renderer tests pass for QR, Code 128 and EAN-13 generation, malformed EAN shape/checksum rejection, and empty/oversized values.
- **Implementation references:** [code generators](../backend/app/codes.py), [renderer tests](../backend/tests/test_template_logic.py), [template contract](template-contract.md), [E2-04 matrix](next-20-validation.md).

**Validation update:** The complete backend suite subsequently passed with the isolated PostgreSQL fixture (`232 passed, 3 skipped, 3 warnings`), the full Playwright suite passed (`39 passed`), and the TypeScript/Vite build passed with 47 modules transformed.

## DD-260: Verify declared offline bundle assets by bounded path and checksum

- **Date:** 2026-09-25
- **Status:** Implemented as an E1-09 hardening slice; E1-09 remains partial
- **Affected stories:** E1-09
- **Context:** The offline-bundle verifier checked the runtime network policy, required images and the existence of an asset description, but a future manifest could declare bundled fonts/models without proving that the files existed or matched the release artifact.
- **Choice:** Support an optional `assets` list containing relative paths and SHA-256 digests. Resolve paths beneath the manifest directory, reject traversal/non-file entries and malformed digests, and fail on checksum mismatch. Keep the current manifest explicit that fonts/models are not bundled until those assets pass separate review.
- **Alternatives:** Trust the descriptive `fonts_and_models` text; rejected because prose cannot bind an artifact to a release. Permit absolute paths; rejected because verification must be reproducible within the bundle boundary. Add unreviewed fonts/models now; rejected because dependency and font licensing remains unresolved.
- **Consequences:** Future offline bundles can be verified deterministically without network access, while the current no-bundled-assets limitation remains visible and honest.
- **Validation:** Repository-tool tests pass for valid asset hashes, modified-file rejection, traversal rejection and the existing manifest/Compose checks.
- **Implementation references:** [offline verifier](../scripts/verify_offline_bundle.py), [repository-tool tests](../backend/tests/test_repository_tools.py), [offline manifest](../templates/docplatform-offline-bundle.json), [E1-09 matrix](next-20-validation.md).
## DD-262: Make image alignment explicit in PDF layout and editor UX

- **Date:** 2026-09-26
- **Status:** Accepted and Implemented; final-engine/native-reader acceptance remains subject to E4-01
- **Affected stories:** E2-03, E2-10, E4-01, E6-01, E6-05
- **Context:** The editor persisted an image's alignment, but the generated HTML expressed it only as `text-align` on a block-level figure. Browser preview could appear centered while a PDF conversion engine positioned the replaced image at the figure's start edge. The editor also did not expose image alignment in the image-specific controls and rendered image blocks as text in its local canvas.
- **Choice:** Keep the figure as a full-width flow container and apply explicit `margin-left`/`margin-right:auto` rules to the image element for left, center and right alignment. Add a visible image alignment selector and render image blocks as images in the local editor canvas. Preserve the existing bounded source and width rules.
- **Alternatives:** Rely on `text-align` alone; rejected because it caused the reported PDF defect. Use absolute positioning; rejected because it conflicts with flowing multi-page documents and keep-together behavior. Add a new renderer dependency; rejected because the renderer remains provisional and the defect is in the portable layout contract.
- **Consequences:** Centered images now have engine-independent geometry in the generated artifact, and the editor's local preview reflects the authored image. The change does not claim final PDF-engine selection, native-reader approval, or arbitrary image-source support.
- **Validation:** Added a left/center/right renderer regression asserting explicit PDF-safe margins and alignment metadata. Existing Chromium alignment coverage remains applicable. Frontend typecheck/build is required after the UI change; native-reader and second-engine review remain open.
- **Implementation references:** [renderer](../backend/app/rendering.py), [renderer tests](../backend/tests/test_template_logic.py), [editor](../frontend/src/main.tsx), [editor styles](../frontend/src/editor.css), [source stories](epics.md).

## DD-263: Deliver the next 30 stories as evidence-bounded implementation slices

- **Date:** 2026-09-26
- **Status:** Accepted and Implemented as bounded slices; source-story residual gates remain explicit
- **Affected stories:** E1-06, E1-07, E1-08, E1-09, E1-10, E1-11, E1-12, E2-04, E2-07, E2-08, E2-09, E2-10, E2-11, E2-12, E2-13, E2-14, E2-15, E2-16, E3-08, E3-09, E4-01, E4-02, E4-03, E4-04, E4-05, E4-06, E4-07, E4-08, E4-09, E4-10
- **Context:** The requested tranche crosses deployment, editor, governance and multilingual rendering. Several source acceptance criteria require evidence unavailable in this workspace (live cluster upgrades, licensed bundled assets, native-reader grades, IME/assistive-technology review and a second renderer). Treating implementation slices as fully accepted would violate the project release gates.
- **Choice:** Complete and document the local, CPU-only, contract-level slices for these 30 IDs; maintain `partial` status where source acceptance has an external or empirical gate. Track the exact slice, evidence and residual gate in [next-30 validation](next-30-validation.md), without changing generated backlog priorities or releases.
- **Alternatives:** Mark all 30 fully implemented; rejected because it would invent acceptance evidence. Stop after the PDF defect; rejected because the repository already contains verifiable next-tranche slices that can be consolidated and validated safely.
- **Consequences:** The project has a traceable 30-story delivery boundary and honest remaining work. Some rows remain partial by design; the status overlay continues to distinguish implemented, partial and planned.
- **Validation:** Re-run the focused renderer/editor checks, frontend build, existing backend regression suite where dependencies are available, and `scripts/audit_must_status.py`. Record unavailable environment checks rather than converting them into claims.
- **Implementation references:** [next-30 validation](next-30-validation.md), [story status](../frontend/src/storyStatus.ts), [implementation plan](implementation-plan.md), [source stories](epics.md).

## DD-264: Terminate Windows worker descendants on portable limit breaches

- **Date:** 2026-09-26
- **Status:** Accepted and Implemented as an E12-02 hardening slice; native deployment enforcement remains partial
- **Affected stories:** E12-02, E11-04
- **Context:** The portable worker supervisor already stopped its direct child on wall-time and output-limit failures. On Windows, the fallback used `Popen.kill()`, which does not guarantee termination of a converter, OCR process, or other descendant launched by that child.
- **Choice:** Use Windows `taskkill /T /F` for supervisor-triggered termination, while retaining POSIX process-group termination and the existing Windows Job Object path. Add a platform-isolated regression proving the descendant-tree command is selected.
- **Alternatives:** Kill only the Python parent; rejected because descendants could survive a failed job. Use a new native dependency; rejected because the platform already provides `taskkill` and the project keeps a dependency-free worker boundary. Claim full hostile-parser containment; rejected because deployment-level isolation and native exhaustion evidence remain open.
- **Consequences:** Timeout and output-limit failures have a stronger descendant-cleanup guarantee on Windows without changing the public job contract. The remaining acceptance gate still requires stable native resource-exhaustion and supported-deployment evidence.
- **Validation:** Focused worker tests pass, including the Windows termination-path regression; full backend regression remains the required follow-up.
- **Implementation references:** [worker supervisor](../backend/app/worker.py), [worker tests](../backend/tests/test_jobs.py), [jobs contract](jobs-contract.md), [source stories](epics.md).

## DD-265: Add a held-out confidence-profile evaluation boundary

- **Date:** 2026-09-26
- **Status:** Accepted and Implemented as an E9-04 evidence tool; production calibration remains partial
- **Affected stories:** E9-04, E9-10
- **Context:** The platform could generate and apply isotonic profiles, but there was no dedicated command that compared calibrated confidence on a separate labelled evaluation corpus. Reusing the calibration fixture would leak labels and could be mistaken for acceptance evidence.
- **Choice:** Add an offline evaluator that reports raw versus calibrated accuracy, Brier score and absolute calibration error by schema and overall. Bind the evaluation artifact to its input SHA-256 and reject an exact hash match with the profile's recorded calibration corpus.
- **Alternatives:** Treat the calibration-corpus benchmark as held-out evidence; rejected because it leaks labels. Add a model or remote scoring service; rejected because local CPU/offline operation is required. Promote E9-04 to complete from deterministic fixture metrics; rejected because representative held-out accuracy and calibration review remain unavailable.
- **Consequences:** Operators have a reproducible, provenance-bound path for measuring whether a reviewed profile improves calibration. The checked-in fixture remains contract coverage only, and the application continues to require an explicitly configured profile.
- **Validation:** The evaluator regression covers raw/calibrated metric output; the full backend suite and script smoke command remain required for release evidence.
- **Implementation references:** [evaluator](../scripts/evaluate_calibration.py), [evaluator tests](../backend/tests/test_calibration_evaluation.py), [extraction contract](extraction-contract.md), [source stories](epics.md).

## DD-266: Harden page-flow compatibility and keyboard source selection

- **Date:** 2026-09-26
- **Status:** Accepted and Implemented as bounded E2-07/E10-01 slices; native-reader and full accessibility gates remain partial
- **Affected stories:** E2-07, E10-01
- **Context:** The renderer emitted modern `break-*` rules, but older PDF engines can require `page-break-*` aliases for the same orphan, keep-together and page-break behavior. Source-region SVG controls were keyboard-focusable but did not expose selected state or preserve the exact element box when activated from the keyboard.
- **Choice:** Emit compatible `page-break-before`/`page-break-inside` rules alongside the modern properties for paragraphs, tables and media. When a source element is clicked or activated with Enter/Space, pass its exact box to the review selection and expose `aria-pressed`; expose the same state on field-source links.
- **Alternatives:** Rely on a single CSS property; rejected because candidate engines differ. Treat visual focus alone as selection; rejected because assistive technology needs state and keyboard activation must produce the same provenance highlight as a pointer click. Claim full WCAG or native-reader acceptance; rejected because those reviews remain external gates.
- **Consequences:** Page-flow intent survives more candidate-engine paths, and source highlighting is deterministic across pointer and keyboard interaction. Broader pagination corpus, IME behavior, native-reader review and accessibility audit remain open.
- **Validation:** Focused renderer assertions and frontend typecheck/build are required; the existing browser source-overlay tests cover pointer behavior, with the keyboard state contract added at the component boundary.
- **Implementation references:** [renderer](../backend/app/rendering.py), [renderer test](../backend/tests/test_template_logic.py), [review UI](../frontend/src/main.tsx), [source stories](epics.md).
