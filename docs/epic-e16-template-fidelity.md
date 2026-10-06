# E16 Template fidelity tuning (proposed epic)

Date: 2026-10-01
Status: **Accepted by the project owner, Phase A in progress** ([DD-417](design-decisions.md#dd-417), [DD-418](design-decisions.md#dd-418)). This epic is a project-owner addition. It is not in the source backlog, and `docs/epics.md` is not changed. It has no source release or priority. The release column below is a proposed sequence only.

## Goal

Measure how well the template editor can reproduce real documents, and turn the shortfalls into ranked, evidence-backed refinements to editor components. A harness takes a reference PDF, builds a template using only the public template contract (what a user can build in the editor), renders it through the normal PDF path, compares the result with the original, and says which component or property causes each difference.

The goal is a general template tool, not any single document. The 2002 ISDA Master Agreement is the first corpus item and is the one that prompted this epic. It is not the acceptance target.

## Boundaries

- The harness is an internal product-evaluation tool. It is not a user-facing "import PDF as template" feature. That feature is E13-05 (R3, XL). E16 produces the measurement and gap evidence that E13-05 would later need, but it does not schedule or deliver E13-05.
- Reconstruction may use only template definitions accepted by the public template API that are reachable from the editor UI. Private Python builders, locked source backgrounds (`page.background_pdf`) and renderer-only properties are excluded, because they hide editor limitations.
- Analysis, comparison and attribution run offline on CPU with no external calls. Any AI-assisted reconstruction mode is optional, configured deliberately, and must report gaps using the same fixed taxonomy.
- The harness never treats source PDF content as template content. A source document stays comparison input only.
- Scores are diagnostics. They do not count as native-reader, accessibility, legal or second-engine approval.

## Stories

| ID | Story | Done when | Size | Proposed sequence |
| --- | --- | --- | --- | --- |
| E16-01 | Dev: maintain a reference corpus of diverse PDFs with recorded provenance and redistribution status | Manifest lists each document's category, source, licence or redistribution status, page count and expected features. Local-only documents are git-ignored. At least one document covers each category: letter, invoice, clause-numbered contract, form with leaders and boxes, table-heavy statement, multi-column report, RTL or CJK document, image/chart document | M | Phase C |
| E16-02 | Dev: analyse a digital source PDF into a versioned SourceModel | Positioned text spans (font, size, weight, style, colour, bounding box), lines and rules, filled rectangles, images and page geometry are extracted offline. Regression fixtures cover each primitive. No new dependency is added without licence review | M | Phase A |
| E16-03 | Dev: detect document features against a fixed, versioned feature taxonomy | Taxonomy covers at least paragraph and typography features, list and numbering, indentation and tabs (including dot leaders), columns, tables (including merged cells), rules and boxes, headers and footers, page furniture, form fields, signature blocks, images and charts. Each detection records the source region and evidence | L | Phase B |
| E16-04 | Dev: reconstruct a template using only the editor-reachable template contract | Output passes template validation, is accepted by `POST /api/templates`, and opens in the editor. Each detected feature is either mapped to a component and properties, or recorded as a gap with a taxonomy reason code: `missing-component`, `missing-property`, `value-out-of-range`, `ui-unreachable`, `workaround-used` | L | Phase B |
| E16-05 | Dev: publish a machine-readable editor capability manifest | Manifest lists every component, property, allowed range and UI exposure, and is generated from the validator and renderer. A test fails when the UI and manifest disagree | M | Phase A |
| E16-06 | Dev: compare the generated PDF with the source by page and region | The report covers page count and geometry, per-page text content F1 and reading order, matched-span position delta (mm), typography match rate, rules/boxes/images match. A visual raster difference is added only after a reviewed rasterizer dependency is accepted | L | Phase A (raster: Phase C) |
| E16-07 | Dev: attribute each difference to a component, property or cause | Each difference above tolerance is linked to its source region, the template block that produced it (via renderer anchors), and one cause: unsupported feature, renderer fidelity defect, reconstruction error, or font unavailability. Unattributed differences are reported as unattributed | L | Phase B |
| E16-08 | Owner: receive a ranked gap report of editor refinements across the corpus | Gaps are aggregated across documents and ranked by affected area or text share × number of documents. Each gap names candidate source stories (E2/E4/E5/E6) and becomes a proposed refinement, not an accepted story, until the owner adopts it | M | Phase C |
| E16-09 | Dev: track fidelity scores per document over time and fail on regressions | Scores are stored per corpus document and run. A command or CI job fails on a regression beyond a recorded tolerance, and changes to baselines require a recorded decision | M | Phase C |
| E16-10 | Owner: measure authoring effort and flexibility of a reconstruction | The report counts blocks, absolute-positioned blocks, properties set and workarounds for each detected feature. A feature that needs many emulating objects is flagged as a usability gap even when output matches | S | Phase B |

## Phase A status (2026-10-01, DD-418)

| Story | Status | Evidence |
| --- | --- | --- |
| E16-02 SourceModel | Implemented (`source-model-v2`) | [`backend/fidelity/source_model.py`](../backend/fidelity/source_model.py): its own content-stream interpreter for text state, glyph widths, rules, boxes, images, form XObjects, off-page and invisible text. Regression tests in [`test_fidelity.py`](../backend/tests/test_fidelity.py) |
| E16-05 Capability manifest | Implemented, UI check partial | [`backend/app/capabilities.py`](../backend/app/capabilities.py), `GET /api/editor/capabilities`. Tests check that every property the renderer reads is declared and every `control` property is referenced by the editor source. Verifying visible controls with Playwright is still pending |
| E16-06 Comparison | Implemented, including raster | [`backend/fidelity/compare.py`](../backend/fidelity/compare.py): document-level word alignment, text F1, reading order, position and typography deltas, rule/box/image matching, localised differences. [`backend/fidelity/visual.py`](../backend/fidelity/visual.py) (DD-420): PDFium raster ink comparison with 1 mm tolerance, worst 10 mm cells per page, and optional red/blue diff PNGs |
| Runner | Implemented | [`scripts/fidelity_run.py`](../scripts/fidelity_run.py) `analyse`, `compare`, `run` (renders through the public API) and `capabilities` |

First calibration on the local-only ISDA document: visual ink F1 `0.069` (recall `0.041`, precision `0.208`, candidate ink `0.19x` of source, all 36 pages below 0.5), word F1 `0.333` (precision `0.925`, recall `0.203`), reading order `0.086`, 0.3% of matched words within 3 mm, median font-size delta `1.71 pt`, 379 renderer anchor-marker words in the PDF text layer. DD-418 lists the component findings.

## Phase B status (2026-10-01, DD-421)

| Story | Status | Evidence |
| --- | --- | --- |
| E16-03 Feature taxonomy | Implemented (`fidelity-taxonomy-v1`) | [`backend/fidelity/taxonomy.py`](../backend/fidelity/taxonomy.py): 23 features. Paragraph segmentation is shared with the mapper; running furniture is excluded from body flow |
| E16-04 Reconstruction | Implemented: rule-based mapper plus agent intake | [`backend/fidelity/reconstruct.py`](../backend/fidelity/reconstruct.py): `reconstruction-v1` (definition, provenance, coded gaps, effort). `validate_reconstruction` rejects anything outside the capability manifest, `ui=none` properties, out-of-range values, `background_pdf`, and unknown reason or feature codes. An agent-produced file goes through the same path with `fidelity_run.py reconstruct --reconstruction file.json` |
| E16-07 Attribution | Implemented (`fidelity-attribution-v2`) | [`backend/fidelity/attribute.py`](../backend/fidelity/attribute.py): global checks (pagination, running furniture); per-gap word evidence from the word alignment against a no-gap control group, with exclusive evidence to separate overlapping gaps; region findings with causes and possible contributors |
| E16-08 Gap report | Single-document ranking implemented; cross-corpus aggregation is Phase C | `gap-report.json` ranks editor gaps by words x excess horizontal displacement over control, plus lost words |
| E16-10 Effort | Implemented | Blocks by type, properties per block, workarounds, rich-text runs, absolute blocks |

Gap reason codes: `missing-component`, `missing-property`, `value-out-of-range`, `value-precision-loss`, `ui-unreachable` and `workaround-used` are editor findings. `harness-limitation` marks something the mapper does not attempt yet and is not an editor finding.

## Phase C status (2026-10-01, DD-423)

| Story | Status | Evidence |
| --- | --- | --- |
| E16-01 Corpus | Partial: 6 of 8 categories | [`fidelity-corpus/manifest.json`](../fidelity-corpus/manifest.json) lists project-authored fixtures (letter, invoice, form, two-column report, multi-page statement, numbered contract) produced by [`scripts/build_fidelity_corpus.py`](../scripts/build_fidelity_corpus.py) with exact embedded font widths, plus the local-only ISDA document. RTL/CJK and image/chart documents are still pending |
| E16-08 Gap report | Implemented across the corpus | `fidelity_run.py corpus` ranks editor gaps by the mean, over documents, of each gap's share of that document's impact (text share and visual share averaged). Output is `corpus-report.json` and `corpus-report.md` |
| E16-09 Regression tracking | Implemented | [`fidelity-corpus/baselines.json`](../fidelity-corpus/baselines.json) holds shared scores, and `fidelity-corpus/local/baselines.json` (git-ignored) holds local-only ones. `corpus --check` exits 1 on a regression beyond tolerance. `--update-baseline` requires `--decision DD-nnn`, and the decision must be in the register |
| E16-03 accuracy | Ground-truth test | Every expected feature in the manifest is detected on the generated corpus. Two-column gutters are found, and tables are not mistaken for columns |

Still open: RTL/CJK and image/chart corpus documents, an agent-driven reconstruction run, the Playwright check of the capability manifest's UI exposure (E16-05), and CI wiring of `corpus --check`.

## First refinement loop (2026-10-01, DD-424 to DD-427)

The three top-ranked editor gaps from DD-423 were implemented and re-measured with `corpus --check` (0 regressions; the baseline was re-approved by DD-427):

| Document | Visual F1 before -> after | Words within 3 mm before -> after |
| --- | --- | --- |
| contract | 0.774 -> 0.972 | 0.189 -> 0.824 |
| form | 0.959 -> 0.980 | 0.909 -> 1.000 |
| invoice | 0.342 -> 0.388 | 0.070 -> 0.042 |
| report | 0.446 -> 0.474 | 0.041 -> 0.018 |
| letter | 0.650 -> 0.621 | 0.312 -> 1.000 |
| statement | 0.416 -> 0.416 | 0.000 -> 0.000 |
| isda-2002 (local) | 0.709 -> 0.709 | 0.064 -> 0.260 |

On ISDA, the median horizontal error for words in justified paragraphs fell from 14.3 mm to 0.23 mm, and for numbered-clause labels from 8.6 mm to 0.36 mm. Vertical drift (median 6.7 mm) and about 7% clipped words now dominate ISDA's remaining error.

DD-428 then fixed the cause of that drift: rich-text paragraphs computed line height against the 16 px page default, and layout was applied twice. ISDA visual F1 rose from 0.709 to 0.960, text F1 from 0.959 to 0.996, and median |dy| fell from 6.7 to 0.30 mm. Words within 3 mm rose from 0.26 to 0.78. Pages 29, 33 and 36 (tables and side-by-side signatures) remain below 0.5.

DD-429 and DD-430 fixed the running-furniture renderer defect. Headers, footers and page numbers are now `@page` margin boxes with alignment, number position and format, and size, so the corpus global finding count fell from 2 to 0. Residual gaps: vertical offset inside the margin, a different first page, and multi-zone bands.

DD-431 and DD-432 closed the table gaps (static rows, typography, alignment, rules, header shading) and fixed vertical placement around tables and at page edges. Visual F1 against the DD-430 baseline:
- invoice 0.388 -> 0.792
- statement 0.418 -> 0.916
- letter 0.621 -> 0.974
- ISDA 0.960 -> 0.979 (no page below 0.5; Schedule pages 29/33/36: 0.29/0.43/0.16 -> 0.89/0.71/0.52)

Table gaps left the corpus ranking, which is now led by line/rule (0.280) and box (0.181) components and columns (0.132).

DD-433 and DD-434 added the `shape` component (lines and rectangles) and mapped source rules and boxes to it:
- **Form:** visual F1 0.980 -> 1.000.
- **Letter:** 0.974 -> 0.998.
- **Ranking:** rules and boxes left it, except for those in page-margin areas.

The ranking is now led by columns (0.132), then header/footer residuals.

DD-435 and DD-436 added column sections and mapped detected two-column pages to them:
- **Report:** visual F1 0.514 -> 0.983, reading order 0.984 -> 0.996.
- **Ranking:** columns left it, which is now led by the multi-zone header (0.149), the footer offset, and rules in page margins.

DD-437 and DD-438 closed those header and footer gaps with zones, distances from the page edge, and header/footer rules:
- **Report:** visual F1 0.983 -> 1.000 (text F1 1.000).
- **Statement:** 0.916 -> 0.985.
- **Remaining gaps:** the statement's mixed-size header zones, ISDA's leader and tab-stop edge cases, and ISDA's different first page.

DD-439 and DD-440 added per-zone size, bold and italic. The statement rose from 0.985 to 0.994 visual F1, and the remaining ranked gaps are ISDA-only and small (shares of 0.067 or less).

An investigation of the invoice's 0.79 found two renderer defects (rows growing by a rounded border pixel each, and absolutely positioned text shrinking to its content), plus a missing header-row height. DD-441 and DD-442 fixed these and the invoice rose to 0.946. The rest is the side-by-side letterhead (title left, details right), which the mapper renders as one rich-text paragraph, and a bold totals row (`row_styles` gap).

DD-443 rebuilds side-by-side blocks as a two-column section, which placed the letterhead within 0.3 mm. It also exposed a compensating error: the old letterhead's 1.3 mm downward drift had hidden a 1.4 mm gap between the invoice's header shading and its first body row. DD-444 extends the header row over that gap and records `table.header_spacing_after` as a missing property. The invoice rose to 0.973.

DD-445 added `header_spacing_after` to tables (renderer, manifest and table panel). DD-446 maps the gap to it, so the shading again matches the bar. Every invoice row is now within 0.5 mm of the source, and the invoice is at 0.975. Its remaining ranked gap is per-row styling (`table.row_styles`).

DD-447 added per-row styles to tables (`row_styles`: bold, italic, shading and text colour by body-row index, with negative indexes counting from the end). DD-448 maps wholly bold body rows to it, so the invoice's "Total due" renders bold and the invoice is at 0.9748. The invoice has no ranked gaps left; the ranking is now ISDA-only (tab stops, leaders and the first-page footer).

DD-449 closed the ISDA positioned-gap case. A wrapped four-column form header on page 33 had been merged into one paragraph with a 166 mm indent. Single lines beyond the 63.5 mm indent range now start with a tab to a left stop rather than a silently clamped indent (three page-30 elections). Table cells within a third of an em share a row. ISDA rose from 0.979 to 0.982 (page 33 0.71 -> 0.97). The ranking is now led by rich-text dot leaders and the different first-page footer.

DD-450 expresses leaders in rich-text first rows as leader tab stops, with each word keeping its run style. It also splits closing brackets off a leader word ("......]"). ISDA rich-text leader gaps fell from 32 to 2; the two left are fused to preceding text. ISDA visual F1 is 0.9821, with 0 regressions. The ranking is now led by the different first-page footer.

## Loop

1. Run the harness on the corpus and produce the gap report.
2. The project owner selects gaps. Each selected gap becomes a refinement mapped to source stories in [backlog refinements](backlog-refinements.md), with a DD entry.
3. Implement the component or property change in the editor, validator and renderer together, and update the capability manifest.
4. Rerun the corpus. Accept the change when the targeted gap closes and no document regresses beyond tolerance.

## Owner decisions (2026-10-01)

- Reconstruction strategy: both a deterministic rule-based mapper and agent-driven reconstruction through the API, reporting gaps with the same taxonomy.
- The ISDA source and generated ISDA PDFs are local-only (git-ignored). Redistributable corpus documents are still to be chosen.
- `backend/app/isda_template.py` is frozen and is retired once the harness reproduces the document.

## Still open

- Raster comparison uses `pypdfium2==5.13.0` as fidelity tooling only (DD-419, DD-420). It is a single engine, so it is not second-engine or native-reader evidence.
