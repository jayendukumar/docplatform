# Product backlog: all epics and stories

Source: [Backlog_DocGen_DocTemplating_DocDigitization.docx](../Backlog_DocGen_DocTemplating_DocDigitization.docx). Extracted on 2026-09-22.
Source SHA-256: `38e7749d4115203bf32fab3203b389094ae3176d951542203b4557b7b4c5f20b`.

This is a faithful text/table transcription. Story IDs, acceptance criteria, priorities, sizes and releases are preserved. This transcription does not claim delivery; see [E1 implementation status](e1-foundation.md) for current progress. Regenerate with `python scripts/extract_backlog.py`; put analysis and scope changes in the other planning documents, not in this generated file.

See [stack proposal](tech-stack.md), [delivery analysis](implementation-plan.md), and [decision log](design-decisions.md).

## Product backlog

The full backlog for the platform, grouped into 15 epics with user stories, priority, relative size and target release.

## Conventions and epic index

Stories are written from the persona in the market research; sizes are relative effort, not calendar time, because team size is unknown.

ID: E<epic>-<number>, for example E4-03.

Priority: Must, Should or Could, judged within the story's own release.

Size: S (a few days), M (about a week), L (a few weeks), XL (needs splitting before it is scheduled).

Release: MVP, R2, R3 or R4, matching the roadmap in the main tab.

Personas: Dev (product developer), Owner (template owner), Loc (localization lead), Ops (back-office analyst), Admin (IT or compliance owner).

| Epic | Goal | Stories | Releases spanned |
| --- | --- | --- | --- |
| E1 Platform foundation and deployment | One-command install, storage, config | 12 | MVP, R2 |
| E2 Template editor | No-code visual design of templates | 16 | MVP, R2, R4 |
| E3 Template management and governance | Versions, folders, review and publishing | 15 | MVP, R2 |
| E4 Rendering engine and multi-language | Correct output in every supported script | 18 | MVP, R2, R4 |
| E5 Data binding and template logic | Fields, loops, conditions and formatting | 15 | MVP, R2, R3 |
| E6 Output formats | PDF, DOCX, then Excel, PowerPoint, HTML, archival PDF | 15 | MVP, R2, R3, R4 |
| E7 API, SDKs and integrations | REST, SDKs, webhooks, no-code connectors | 16 | MVP, R2, R3, R4 |
| E8 Digitization: ingestion and OCR | Turn files into machine-readable layout | 20 | MVP, R2, R3, R4 |
| E9 Schema and extraction | Turn layout into validated structured data | 16 | MVP, R2, R3, R4 |
| E10 Review and correction | Human review with correction capture | 14 | MVP, R2, R3, R4 |
| E11 Identity, security and compliance | Users, roles, audit, standards | 16 | MVP, R2, R3, R4 |
| E12 Operations, observability and scale | Queues, limits, batch, metrics | 12 | MVP, R2, R3, R4 |
| E13 AI assistance and agent integration | AI-drafted templates, MCP server | 10 | R3 |
| E14 Ecosystem, documentation and community | Docs, plug-ins, marketplace, contributor path | 13 | MVP, R2, R4 |
| E15 Hosted cloud and billing | Managed service and metering | 10 | R4 |

## E1 Platform foundation and deployment

Goal: anyone can install, configure and upgrade the platform without special skills.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E1-01 | Dev: start the whole platform with one docker compose up | UI and API reachable, sample template preloaded | Must | M | MVP |
| E1-02 | Admin: configure everything through environment variables and one config file | All settings documented; secrets never logged | Must | S | MVP |
| E1-03 | Admin: store templates, uploads and outputs on local disk or S3-compatible storage | Both backends pass the same test suite | Must | M | MVP |
| E1-04 | Admin: keep metadata in PostgreSQL with automatic migrations | Fresh install and upgrade both migrate cleanly | Must | M | MVP |
| E1-05 | Admin: see health and readiness endpoints for each service | Endpoints report dependency status | Should | S | MVP |
| E1-06 | Admin: run on CPU only, with a documented minimum hardware guide | Extraction and rendering work without a GPU | Must | S | MVP |
| E1-07 | Admin: upgrade between versions without data loss | Migration tests run on the previous two releases | Should | M | R2 |
| E1-08 | Admin: deploy on Kubernetes with a Helm chart | Chart installs, scales workers, passes smoke test | Should | L | R2 |
| E1-09 | Admin: install offline with fonts and models bundled | Install works with no internet access | Should | M | R2 |
| E1-10 | Admin: back up and restore data with one command | Restore reproduces templates, results and settings | Should | M | R2 |
| E1-11 | Admin: set retention periods for uploads and outputs | Expired files are purged on schedule | Should | S | R2 |
| E1-12 | Contributor: run the stack locally without Docker | Documented dev mode with hot reload | Could | M | R2 |

## E2 Template editor

Goal: a non-developer can design a production-quality, multi-page template in the browser.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E2-01 | Owner: drag text blocks onto a page and format them (font, size, weight, colour, alignment) | Formatting persists in preview and output | Must | L | MVP |
| E2-02 | Owner: add tables whose rows repeat from a data array | Row count follows data; header repeats across pages | Must | L | MVP |
| E2-03 | Owner: place images and logos, fixed or bound to a data field | Upload, URL and base64 sources all render | Must | M | MVP |
| E2-04 | Owner: add QR codes and barcodes bound to fields | QR, Code 128 and EAN render and scan | Must | M | MVP |
| E2-05 | Owner: add repeating sections and conditional blocks visually | Loop and if-else behave as in the data-binding rules | Must | L | MVP |
| E2-06 | Owner: set page size, orientation, margins, headers, footers and page numbers | Settings apply to every page of the output | Must | M | MVP |
| E2-07 | Owner: control page flow with automatic breaks and keep-together rules | No orphaned headings or split rows in the test set | Must | L | MVP |
| E2-08 | Owner: preview with sample data and switch preview language and locale | Preview matches final render for every supported script | Must | M | MVP |
| E2-09 | Loc: type and edit Arabic, Hebrew, Indic, Thai and CJK text directly on the canvas | Caret, selection and input methods work per script | Must | L | MVP |
| E2-10 | Owner: undo and redo, copy and paste, snapping and alignment guides, keyboard shortcuts | Actions covered by editor tests | Should | M | MVP |
| E2-11 | Owner: reuse components such as header, footer and address block across templates | Editing a component updates every template using it | Should | L | R2 |
| E2-12 | Owner: apply brand themes with colour, font and spacing tokens | Switching theme restyles a template without manual edits | Should | M | R2 |
| E2-13 | Owner: use the editor with keyboard and screen reader | Editor meets WCAG 2.2 AA on core flows | Should | L | R2 |
| E2-14 | Owner: add charts (bar, line, pie) bound to data | Charts render in PDF with embedded fonts | Could | L | R2 |
| E2-15 | Owner: use an existing PDF page as a locked background layer | Background scales correctly; fields overlay it | Could | M | R2 |
| E2-16 | Owner: add tables of contents and page cross-references | Numbers update after content changes | Could | M | R4 |

## E3 Template management and governance

Goal: teams can organize, review, version and safely publish templates at scale.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E3-01 | Owner: organize templates in folders and tags and search them by name, tag and content | Search returns results within a second on 1,000 templates | Must | M | MVP |
| E3-02 | Owner: keep drafts separate from published versions | API renders the published version unless a draft is requested | Must | M | MVP |
| E3-03 | Owner: see version history with a change summary and restore any version | Restore creates a new version, never overwrites | Must | M | MVP |
| E3-04 | Owner: duplicate a template with save-as | Copy carries assets and sample data | Must | S | MVP |
| E3-05 | Owner: start from a gallery of starters (invoice, letter, certificate, receipt) in at least three languages | Each starter passes the script test matrix | Must | M | MVP |
| E3-06 | Dev: attach sample data and see the expected JSON schema derived from the template | Schema updates when fields change | Must | M | MVP |
| E3-07 | Dev: export and import a template as a portable file | Round trip yields an identical render | Must | M | MVP |
| E3-08 | Dev: sync templates with a git repository as plain files | Push and pull work in CI without the UI | Should | L | R2 |
| E3-09 | Owner: submit a template for review, and reviewers approve before publishing | Publish blocked without approval when the policy is on | Should | L | R2 |
| E3-10 | Admin: promote templates across dev, staging and production environments | Promotion is logged and reversible | Should | L | R2 |
| E3-11 | Owner: comment on templates and request changes | Comments anchor to an element | Could | M | R2 |
| E3-12 | Admin: restrict template access per team or folder | Unauthorized users cannot see or render restricted templates | Should | M | R2 |
| E3-13 | Owner: see usage analytics per template (renders, errors, latency) | Dashboard shows the last 30 days | Should | M | R2 |
| E3-14 | Owner: archive templates, with a warning when API keys still use them | Archived templates return a clear API error | Should | S | R2 |
| E3-15 | Owner: move, tag and export many templates at once | Bulk actions are undoable for 10 minutes | Could | S | R2 |

## E4 Rendering engine and multi-language support

Goal: output is correct in every supported script, and we can prove it. This epic carries the main differentiator.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E4-01 | Loc: run a rendering spike that compares candidate engines on Arabic, Hebrew, Hindi, Tamil, Thai, Chinese and Japanese | Native readers grade each output; default engine chosen and recorded | Must | M | MVP |
| E4-02 | Loc: get a bundled Noto font set with script-specific fallback stacks | Every listed script renders without a missing-glyph box | Must | M | MVP |
| E4-03 | Loc: have complex-script shaping on by default for Arabic, Indic and Thai | No user setting needed; test matrix passes | Must | L | MVP |
| E4-04 | Loc: render mixed right-to-left and left-to-right text, numbers and punctuation correctly | Bidi test cases pass in text, tables and headers | Must | L | MVP |
| E4-05 | Loc: get correct line breaking for Chinese, Japanese, Korean and Thai | Breaks follow language rules on the test set | Must | M | MVP |
| E4-06 | Owner: upload custom fonts, with subsetting and a reminder to check the font licence | Uploaded font is embedded in output and listed in the report | Must | M | MVP |
| E4-07 | Dev: get an automatic per-character font fallback with a warning when no font has the glyph | Render response lists missing glyphs | Must | M | MVP |
| E4-08 | Loc: see a public script test matrix rebuilt in CI with visual regression | Any rendering change that alters the matrix fails the build | Must | L | MVP |
| E4-09 | Loc: format dates, numbers and currencies by locale | Output matches CLDR examples for the supported locales | Must | M | MVP |
| E4-10 | Owner: render one template in many languages using per-template translation files | Language chosen per request; missing keys reported | Must | L | MVP |
| E4-11 | Loc: mirror layouts for right-to-left languages (alignment, column order, page numbers) | One template flips correctly with a locale switch | Should | L | R2 |
| E4-12 | Loc: use language-specific hyphenation and justification | Enabled per language; off by default | Could | M | R2 |
| E4-13 | Loc: choose numeral systems such as Arabic-Indic and Devanagari digits | Numerals follow the locale or an override | Should | S | R2 |
| E4-14 | Loc: format non-Gregorian calendars (Hijri, Buddhist) | Dates verified by native reviewers | Could | M | R2 |
| E4-15 | Dev: swap the rendering engine per template behind one interface | Two engines pass the same conformance tests | Should | L | R2 |
| E4-16 | Dev: pin the engine version per template so output stays stable across upgrades | Same input and pinned version give identical output | Should | M | R2 |
| E4-17 | Dev: keep file sizes low through font subsetting and image compression | Size budget reported per render | Should | M | R2 |
| E4-18 | Loc: render vertical Japanese text and ruby annotations | Sample documents approved by native readers | Could | L | R4 |

## E5 Data binding and template logic

Goal: templates turn structured data into documents, including data that came from the digitization pipeline.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E5-01 | Dev: bind fields to JSON with dot paths and array indexes | Nested paths resolve; errors name the failing path | Must | M | MVP |
| E5-02 | Owner: loop over arrays, including nested ones, with an empty-state message | Empty arrays show the message instead of a blank gap | Must | M | MVP |
| E5-03 | Owner: show or hide blocks with conditions and if-else | Conditions support comparison, and, or, not | Must | M | MVP |
| E5-04 | Owner: format values with number, currency, date, percent and text functions | Functions are locale-aware and covered by tests | Must | M | MVP |
| E5-05 | Dev: validate render requests against the template's JSON schema with clear errors | Invalid data returns field-level messages, not a failed render | Must | M | MVP |
| E5-06 | Admin: run template expressions in a sandbox with no code execution or network access | Security tests confirm expressions cannot reach the host | Must | M | MVP |
| E5-07 | Owner: choose what happens when a field is missing (error, blank, placeholder) | Policy set per template and per request | Must | S | MVP |
| E5-08 | Ops: use approved extraction results as a template's data source in one click | Field names from the extraction schema map to template fields | Must | M | MVP |
| E5-09 | Owner: generate sample data automatically for previews | Sample values respect field types and locales | Should | S | MVP |
| E5-10 | Owner: compute totals, counts and averages in tables | Results match spreadsheet calculations in tests | Should | L | R2 |
| E5-11 | Owner: sort, filter and group arrays inside the template | Operations are declarative and preview-safe | Should | M | R2 |
| E5-12 | Ops: generate one document per row from a CSV or Excel upload | Failures are reported per row; successes still download | Should | L | R2 |
| E5-13 | Owner: compose templates from sub-templates | Changes to a sub-template propagate with version pinning | Should | L | R2 |
| E5-14 | Dev: fetch data from an allow-listed REST endpoint at render time | Timeouts and errors handled; calls logged | Could | L | R2 |
| E5-15 | Loc: apply currency rounding rules by locale | Rounding follows the configured rule set | Could | M | R3 |

## E6 Output formats

Goal: produce the formats customers actually send, starting with PDF and Word.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E6-01 | Dev: generate PDF from a designer template | Output opens in Acrobat, Chrome and Preview with fonts embedded | Must | L | MVP |
| E6-02 | Dev: upload a Word template with placeholders and loops and merge JSON into it | Text, tables and images merge; layout preserved | Should | L | MVP |
| E6-03 | Dev: convert merged Word output to PDF | PDF matches the Word layout on the test set | Must | M | MVP |
| E6-04 | Dev: set PDF metadata (title, author, language) | Language tag matches the render locale | Must | S | MVP |
| E6-05 | Dev: get a report of fonts and glyph coverage with each render | Report lists embedded fonts and missing glyphs | Must | S | MVP |
| E6-06 | Owner: get image thumbnails of the first page for previews | PNG returned within the preview flow | Should | S | MVP |
| E6-07 | Dev: protect PDFs with passwords and permissions | Restrictions verified in two PDF readers | Should | M | R2 |
| E6-08 | Dev: bundle several documents into one PDF and add watermarks or stamps | Order and page numbering are configurable | Should | M | R2 |
| E6-09 | Dev: generate Excel files with formats and formulas | Formulas recalculate in Excel and LibreOffice | Should | L | R2 |
| E6-10 | Dev: generate PowerPoint files with slides repeated per record | Overflow creates new slides | Could | L | R2 |
| E6-11 | Dev: generate email-safe HTML | Renders in the major mail clients | Could | M | R2 |
| E6-12 | Dev: render Markdown into a styled document | Style inherits from a chosen template | Could | M | R3 |
| E6-13 | Admin: produce PDF/A archival files | Files pass a PDF/A validator | Should | L | R4 |
| E6-14 | Admin: produce tagged, accessible PDFs | Files pass an accessibility checker | Should | XL | R4 |
| E6-15 | Dev: leave signature fields or hand off to an e-signature service | Field position preserved in the output | Could | L | R4 |

## E7 API, SDKs and integrations

Goal: developers can integrate in an afternoon and non-developers can connect the platform to their tools.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E7-01 | Dev: manage templates and render documents through a REST API | Every UI action has an API equivalent | Must | L | MVP |
| E7-02 | Dev: authenticate with scoped API keys that can be rotated | Keys can be limited to read, render or admin | Must | M | MVP |
| E7-03 | Dev: read an OpenAPI spec and try calls in a built-in explorer | Spec generated from code and tested for drift | Must | S | MVP |
| E7-04 | Dev: render small documents synchronously and larger ones as async jobs with status polling | Job states are queued, running, done, failed | Must | M | MVP |
| E7-05 | Dev: submit scans and read extraction results through the API | Upload, status and result endpoints documented | Must | M | MVP |
| E7-06 | Dev: receive signed webhooks when a job finishes or fails, with retries | Signature verification example provided | Should | M | MVP |
| E7-07 | Dev: use official SDKs for JavaScript or TypeScript and Python | SDKs generated from the spec and published | Should | L | R2 |
| E7-08 | Dev: push and pull templates and render locally with a CLI | CLI works in CI pipelines | Should | M | R2 |
| E7-09 | Dev: embed the template editor in my own product | Editor loads in an iframe or component with token auth | Should | XL | R2 |
| E7-10 | Dev: retry render requests safely with idempotency keys | Duplicate requests return the first result | Should | S | R2 |
| E7-11 | Dev: download outputs through expiring pre-signed links | Links expire after the configured time | Should | S | R2 |
| E7-12 | Admin: set rate limits and quotas per API key | Limits enforced with clear error responses | Should | M | R2 |
| E7-13 | Ops: connect through Zapier, Make and n8n | Connectors published with example flows | Could | L | R2 |
| E7-14 | Dev: submit many render or extraction jobs in one batch call | Partial failures reported per item | Could | M | R2 |
| E7-15 | Ops: ingest files from an email inbox, cloud drive or bucket automatically | New files trigger extraction without manual upload | Could | L | R3 |
| E7-16 | Admin: connect to CRM and ERP systems such as Salesforce and SAP | Two certified connectors released | Could | XL | R4 |

## E8 Digitization: ingestion and OCR pipeline

Goal: turn any incoming file into a machine-readable page model with a traceable source for every value.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E8-01 | Ops: upload PDF and image files (PNG, JPEG, TIFF) in the UI or by API | Multi-file upload with per-file status | Must | M | MVP |
| E8-02 | Ops: have digital and scanned pages detected and routed automatically | Text PDFs skip OCR; scans go through OCR | Must | M | MVP |
| E8-03 | Ops: get layout analysis with reading order, headings, lists and tables | Docling output mapped to the page model | Must | L | MVP |
| E8-04 | Ops: get OCR for scans with a chosen language | PaddleOCR configured per language pack | Must | L | MVP |
| E8-05 | Ops: handle long and multi-page files with page limits and progress | Progress visible; limits configurable | Must | M | MVP |
| E8-06 | Dev: receive a page model as JSON and Markdown with bounding boxes on every element | Schema documented and versioned | Must | M | MVP |
| E8-07 | Ops: click any extracted value and see its source region highlighted | Every value stores page and box provenance | Must | L | MVP |
| E8-08 | Admin: swap or add extraction engines through a plug-in interface | Docling, PaddleOCR and one more engine run behind the same contract | Must | M | MVP |
| E8-09 | Ops: get scans cleaned up by deskew, rotation and contrast fixes | Accuracy improves on a skewed test set | Should | M | MVP |
| E8-10 | Ops: have the script and language of each page detected automatically | Detection accuracy reported on the test set | Should | L | R2 |
| E8-11 | Ops: parse Word, Excel, PowerPoint and HTML files with the same pipeline | Same page model for all inputs | Should | M | R2 |
| E8-12 | Admin: use a GPU when available and fall back to CPU | Both paths tested; GPU is optional | Should | M | R2 |
| E8-13 | Ops: have documents routed to the best engine by type and measured accuracy | Router beats any single engine on the benchmark set | Should | XL | R3 |
| E8-14 | Ops: recover tables without borders and tables spanning pages | Table accuracy tracked on a dedicated set | Should | XL | R3 |
| E8-15 | Ops: classify documents (invoice, receipt, contract, form) and choose a schema automatically | Classifier accuracy reported per class | Should | L | R3 |
| E8-16 | Ops: read handwriting through a vision-language engine | Confidence and hallucination checks in place | Could | XL | R3 |
| E8-17 | Ops: split multi-document scans into separate documents | Page ranges proposed for review | Could | XL | R3 |
| E8-18 | Ops: read barcodes and QR codes on pages | Decoded values stored with page location | Could | M | R3 |
| E8-19 | Ops: parse email files and their attachments | EML and MSG parsed into linked documents | Could | M | R3 |
| E8-20 | Admin: redact sensitive fields before results are stored | Redaction rules configurable per schema | Could | L | R4 |

## E9 Schema and extraction

Goal: turn the page model into validated, structured data that a template or another system can use.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E9-01 | Ops: define an extraction schema with fields, types, required flags and repeating tables | Schema editable in the UI and as JSON Schema | Must | L | MVP |
| E9-02 | Ops: start from bundled schemas for invoice, receipt and purchase order | Each schema has sample documents and expected output | Must | M | MVP |
| E9-03 | Dev: fill schema fields through a pluggable extractor with a bundled local option and optional cloud or LLM plug-ins | Extractor contract documented; local option needs no external calls | Must | L | MVP |
| E9-04 | Ops: see a confidence score on every field | Scores calibrated against the labelled test set | Must | L | MVP |
| E9-05 | Ops: apply validation rules (patterns, ranges, checksums, totals that must add up) | Failed rules flag the field for review | Must | L | MVP |
| E9-06 | Ops: get dates, currencies and numbers normalized by locale | Original and normalized values both kept | Must | M | MVP |
| E9-07 | Ops: extract line items into arrays | Row and column accuracy reported per schema | Must | L | MVP |
| E9-08 | Ops: export results as JSON, CSV or Excel and by webhook | Exports include confidence and review status | Must | M | MVP |
| E9-09 | Dev: run an extraction benchmark on labelled documents and get an accuracy report per schema | Report generated in CI and on demand | Must | M | MVP |
| E9-10 | Loc: match field labels in Arabic, Hindi, Thai, Chinese and other scripts | Label dictionaries per language, tested on native samples | Must | L | R2 |
| E9-11 | Admin: version schemas and migrate stored results | Old results stay readable after schema changes | Should | M | R2 |
| E9-12 | Ops: auto-approve documents whose fields all clear a confidence threshold | Threshold set per schema; audit trail kept | Should | M | R3 |
| E9-13 | Ops: detect duplicate documents by file hash and fuzzy field match | Duplicates flagged before review | Should | M | R3 |
| E9-14 | Ops: check values against reference data such as vendor lists and code tables | Lookup mismatches flagged | Could | L | R3 |
| E9-15 | Dev: supply a few example documents per schema to improve extraction | Accuracy gain measured on the benchmark set | Could | L | R3 |
| E9-16 | Ops: cross-check related documents such as invoice against purchase order | Mismatches shown side by side | Could | XL | R4 |

## E10 Review and correction

Goal: reviewers can verify and fix extracted data quickly, and every correction is captured for improving accuracy.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E10-01 | Ops: review side by side, with the page image on one side and fields on the other | Clicking a field highlights its source region | Must | L | MVP |
| E10-02 | Ops: edit values, draw a box to add a missing field, or mark a field as absent | Edits save instantly and are undoable | Must | L | MVP |
| E10-03 | Ops: see low-confidence and failed-rule fields first and move between them by keyboard | Full review possible without the mouse | Must | M | MVP |
| E10-04 | Ops: approve or reject a document, with states new, in review, approved and rejected | State changes are logged | Must | M | MVP |
| E10-05 | Ops: send approved data to a template in one click | Template opens with data bound and preview shown | Must | M | MVP |
| E10-06 | Admin: keep a log of every correction with original value, new value, user and time | Log exportable as CSV | Must | S | MVP |
| E10-07 | Ops: work from a queue with filters and assign documents to reviewers | Assignment and status visible in the list | Should | M | R2 |
| E10-08 | Ops: use the review screen in right-to-left languages and with non-Latin field labels | Layout mirrors correctly; labels render in every supported script | Should | M | R2 |
| E10-09 | Admin: turn the correction log into evaluation sets and fine-tuning exports | Export format documented; PII options provided | Should | L | R3 |
| E10-10 | Admin: see reviewer metrics such as time per document and correction rate | Metrics by schema and by reviewer | Should | M | R3 |
| E10-11 | Ops: approve many documents at once when confidence is above a threshold | Bulk action requires a confirmation and is logged | Should | M | R3 |
| E10-12 | Admin: adjust rules or examples automatically from repeated corrections | Suggestions shown for approval, never applied silently | Could | XL | R3 |
| E10-13 | Admin: require a second reviewer for high-value fields | Rule configurable per field | Could | M | R4 |
| E10-14 | Ops: comment on a document or field and mention colleagues | Comments visible in the review history | Could | M | R4 |

## E11 Identity, security and compliance

Goal: safe by default for a self-hosted deployment, with the controls regulated buyers ask for arriving in later releases.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E11-01 | Admin: create local users with admin, editor and viewer roles | Role permissions enforced in UI and API | Should | M | MVP |
| E11-02 | Admin: get secure password storage, session handling, CSRF protection and login rate limits | Passes an automated security test suite | Must | M | MVP |
| E11-03 | Admin: run behind TLS with documented configuration | Reference proxy setup in the install guide | Must | S | MVP |
| E11-04 | Admin: have uploads checked by size and type limits, an optional virus-scan hook, and rendering in a sandbox with no network access | Malicious-file test cases contained | Must | L | MVP |
| E11-05 | Admin: scan dependencies and licences in CI against an allow-list of MIT, Apache-2.0 and OFL | Build fails on a disallowed licence; SBOM published | Must | M | MVP |
| E11-06 | Admin: sign in with an identity provider through OIDC or SAML | Tested with two common providers | Should | L | R2 |
| E11-07 | Admin: set fine-grained permissions per folder, template or schema | Permission checks covered by tests | Should | L | R2 |
| E11-08 | Admin: read an exportable audit log of admin, template and API events | Log entries are tamper-evident | Should | M | R2 |
| E11-09 | Admin: encrypt stored files and manage keys | Key rotation documented and tested | Should | L | R2 |
| E11-10 | Admin: publish a security policy and commission an independent penetration test | Findings triaged and fixed before R2 ships | Should | M | R2 |
| E11-11 | Admin: detect and mask personal data in logs and outputs | Masking rules configurable per schema | Should | L | R3 |
| E11-12 | Admin: sync users and groups from the identity provider (SCIM) | Provisioning and removal tested | Could | L | R4 |
| E11-13 | Admin: pin data to a region in the hosted service | Region choice enforced end to end | Should | L | R4 |
| E11-14 | Admin: set retention and deletion policies with deletion evidence | Deletion certificates exportable | Should | M | R4 |
| E11-15 | Admin: fulfil data-subject export and deletion requests | Tooling covers stored documents and results | Should | L | R4 |
| E11-16 | Admin: prepare for SOC 2 or ISO 27001 for the hosted service | Gap assessment complete and controls tracked | Could | XL | R4 |

## E12 Operations, observability and scale

Goal: jobs run reliably under load, and operators can see what is happening.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E12-01 | Dev: rely on a durable job queue so async jobs survive restarts | Jobs resume after a service restart in tests | Must | M | MVP |
| E12-02 | Admin: cap memory, CPU and run time per render or extraction job | A runaway job is stopped without affecting others | Must | L | MVP |
| E12-03 | Admin: scale render workers and extraction workers separately | Adding workers raises throughput in a load test | Must | L | R2 |
| E12-04 | Ops: run large batches with progress and partial-failure handling | Failed items can be retried on their own | Should | L | R2 |
| E12-05 | Admin: get retries with backoff and a dead-letter queue | Poison jobs land in the queue view with a reason | Should | M | R2 |
| E12-06 | Admin: scrape a metrics endpoint and use ready-made dashboards | Dashboards cover throughput, errors, latency | Should | M | R2 |
| E12-07 | Admin: get structured logs with correlation IDs and OpenTelemetry traces | One request traceable from API to output | Should | M | R2 |
| E12-08 | Dev: get faster repeat renders through caching of fonts and compiled templates | Speed-up measured and documented | Should | M | R2 |
| E12-09 | Admin: use a published load-test suite and benchmark results | Results reproducible from the repository | Should | M | R2 |
| E12-10 | Admin: set latency objectives and alerts | Alerts fire in a staged failure test | Could | M | R2 |
| E12-11 | Admin: schedule GPU jobs and control cost for model-based extraction | Queue prioritizes by cost and deadline | Could | L | R3 |
| E12-12 | Admin: upgrade with rolling deploys and no downtime | Upgrade test shows no failed requests | Could | L | R4 |

## E13 AI assistance and agent integration

Goal: use AI to remove template and schema setup work, with humans approving every result. Competitors already ship MCP servers, so agent access is a baseline expectation.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E13-01 | Admin: connect my own model, local or through an API, with prompt and log controls | No data leaves the network unless configured | Must | M | R3 |
| E13-02 | Admin: see AI output always presented as a suggestion, never published automatically | Publish and approve actions require a human | Must | S | R3 |
| E13-03 | Dev: run an evaluation suite for every AI feature, with regression and hallucination checks | Suite runs in CI; release blocked on regression | Must | M | R3 |
| E13-04 | Dev: let agents list templates, render documents and digitize files through an MCP server | Tools documented and tested with two agent clients | Should | M | R3 |
| E13-05 | Owner: turn a sample PDF or Word file into a draft template by detecting fixed and variable regions | Draft reproduces the sample within visual tolerance | Should | XL | R3 |
| E13-06 | Owner: draft a template from a plain-language description | Draft opens in the editor for changes | Should | XL | R3 |
| E13-07 | Loc: translate template text with a glossary and human approval | Glossary terms enforced; changes tracked | Should | L | R3 |
| E13-08 | Ops: get suggested schema fields from a sample document | Suggestions accepted or rejected per field | Should | L | R3 |
| E13-09 | Dev: get validation errors explained in plain language with a suggested fix | Explanations cover the ten most common errors | Could | M | R3 |
| E13-10 | Owner: edit a template with natural-language instructions | Each instruction produces a reversible change | Could | L | R3 |

## E14 Ecosystem, documentation and community

Goal: an open-source project people trust, can learn quickly, and can extend.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E14-01 | Dev: follow a 10-minute quickstart and an API reference | A new user reaches a generated PDF in the time stated | Must | M | MVP |
| E14-02 | Contributor: read a contributor guide, code of conduct, issue templates and the chosen contribution agreement | Files present at launch; licence file matches the decision | Must | S | MVP |
| E14-03 | Loc: view the public script test matrix as a page in the docs | Page rebuilt from the CI results | Must | S | MVP |
| E14-04 | Admin: use a UI built on an i18n framework from day one | No hard-coded strings in the interface | Must | S | MVP |
| E14-05 | Dev: try sample apps (invoice generator, multilingual certificate, scan-to-report) | Each app runs from the repository | Should | M | MVP |
| E14-06 | Dev: follow a public roadmap and changelog | Both updated with each release | Should | S | MVP |
| E14-07 | Dev: extend renderers, extractors and storage through a plug-in system | Two internal engines reimplemented as plug-ins | Should | XL | R2 |
| E14-08 | Dev: import templates from pdfme, Carbone and docxtemplater formats | Importers documented with known limits | Should | L | R2 |
| E14-09 | Dev: ask questions in a community forum or chat with maintainer office hours | Channel live and monitored | Could | S | R2 |
| E14-10 | Admin: use the interface in several languages | English plus at least two more shipped | Should | M | R4 |
| E14-11 | Dev: read documentation in the top five languages by usage | Translations reviewed by native speakers | Should | L | R4 |
| E14-12 | Owner: browse a community template marketplace with ratings and licence tags | Submission and moderation flow live | Could | XL | R4 |
| E14-13 | Dev: find certified partners and integrators | Programme criteria and directory published | Could | M | R4 |

## E15 Hosted cloud and billing

Goal: a managed service for teams that do not want to run the platform, funding the open-source core. The free-versus-paid line should be published before launch so buyers know what stays open.

| ID | Story | Done when | Priority | Size | Release |
| --- | --- | --- | --- | --- | --- |
| E15-01 | Admin: run each customer in an isolated tenant | Cross-tenant access tests all fail as intended | Must | XL | R4 |
| E15-02 | Admin: meter documents rendered and pages extracted per tenant | Meters reconcile with logs to the unit | Must | L | R4 |
| E15-03 | Owner: sign up and manage my organization and team without help | Signup to first render in one session | Must | L | R4 |
| E15-04 | Owner: pay through plans with invoices and tax handled by a payment provider | Upgrade, downgrade and cancel flows tested | Must | L | R4 |
| E15-05 | Admin: enforce quotas and prevent abuse | Limits, throttling and blocking documented | Must | M | R4 |
| E15-06 | Owner: start on a free tier | Free tier limits published; conversion tracked | Should | M | R4 |
| E15-07 | Admin: publish a status page and support tooling | Incidents visible; support can see tenant health | Should | M | R4 |
| E15-08 | Admin: apply the published open-core policy through licence keys for paid features | Only features listed as paid are gated | Should | M | R4 |
| E15-09 | Admin: choose a deployment region | At least two regions live | Should | XL | R4 |
| E15-10 | Admin: buy through cloud provider marketplaces | Listing live on at least one marketplace | Could | L | R4 |

## Release summary, MVP sequencing and quality bar

The backlog holds 218 stories, and the MVP as scoped is large: 91 stories, 24 of them sized L. A small team should split it into two internal milestones rather than treat it as one release.

| Release | Stories |
| --- | --- |
| MVP | 91 (81 Must, 10 Should) |
| R2 | 67 |
| R3 | 30 |
| R4 | 30 |

## Suggested internal MVP milestones

M1, generation with multi-language proof: E4-01 spike first, then E1, E2, E3, E4, E5, E6 and E7 stories, plus E11-02 to E11-05 and E12-01 to E12-02. Exit: a native reader approves the script matrix and a developer generates a PDF through the API.

M2, digitization and the closed loop: E8, E9 and E10 MVP stories, E5-08 and E7-05. Exit: a scanned invoice becomes reviewed JSON and then a generated PDF, and accuracy is reported on the labelled set.

If M1 alone is releasable, ship it as a public alpha to start collecting feedback on the multi-language edge while M2 is built.

## Quality bar for every release

| Area | Standard | Verified by |
| --- | --- | --- |
| Scripts | Every supported script approved by a native reader | Script test matrix with visual regression in CI (E4-08) |
| Extraction accuracy | Field-level accuracy reported per schema; target set after the first baseline | Benchmark harness (E9-09) |
| Accessibility | WCAG 2.2 AA for the editor and review screens | Automated checks plus a manual audit |
| Browsers | Latest two versions of Chrome, Firefox, Safari and Edge | Cross-browser test run |
| Licensing | Only MIT, Apache-2.0 and OFL components by default | Licence scan and SBOM in CI (E11-05) |
| Security | Sandboxed rendering with no network access from templates | Security test suite; independent test in R2 (E11-10) |
| Performance | Latency and throughput budgets set after the first benchmark | Load-test suite (E12-09) |

## Definition of done for a story

Acceptance criteria in the story pass in an automated test.

Documented in the user guide and, if relevant, the API reference.

No new dependency without a licence check.

Works in at least one right-to-left and one CJK sample.

Reviewed by a second engineer and, for UI work, checked for keyboard use.
