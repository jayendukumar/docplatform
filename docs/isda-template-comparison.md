# ISDA Template source comparison

Date: 2026-09-30  
Template: `ISDA Template`  
Source: [`2002-ISDA-Master-Agreement.pdf`](../2002-ISDA-Master-Agreement.pdf)  
Generated artifact: [`generated-isda-aligned.pdf`](../generated-isda-aligned.pdf)  
Template version rendered: `isda-template-v4` (draft)

Latest live foreground-only verification (DD-415, 2026-10-01): the rebuilt Compose API serves 381 ISDA blocks with no `page.background_pdf`; the generated artifact is [`artifacts/isda-foreground-only.pdf`](../artifacts/isda-foreground-only.pdf), 96,538 bytes, and reports `locked_background: omitted`. It has 36/36 Letter pages, normalized extracted-text similarity `0.0136`, mean page similarity `0.0358`, and no visual comparison because no local rasterizer is available. The low similarity is intentionally recorded as evidence that the editable foreground is not yet close to the source.

Current semantic foreground baseline (DD-387): 308 objects, 36 pages, PDF SHA-256 `d4c6dd144cc4f8b029f9e5f65a0c3f68929e53f729cf840ef82fc5fcb19dd797`, PNG SHA-256 `0bd12a383a0f3234733bec0932051a2651fd5cee6da8b1d01d8fb026fb050c80`. The page-29 Schedule agreement-date field is bound to the existing `agreement_date` path. Comparison remains diagnostic: page count and Letter geometry match, normalized extracted-text similarity is `0.0029`, and visual comparison is unavailable.

DD-390 comparison runs now supply [`isda-foreground.json`](../artifacts/isda-foreground-baseline/isda-foreground.json), which declares `locked_background: omitted`; the comparison report records this as `candidate_manifest.status: foreground-only`.

Current DD-392 comparison artifact: 312 foreground objects, 36 pages, PDF SHA-256 `d0f8e049814242c762ccd7d50b5e3b4132e23dc9437af0d1dd89e7823c9a7f1c`, PNG SHA-256 `628517a2565ea6d2ae95086c98b1afd710cabbe31e786052fb0f2dafddf4e99d`, normalized extracted-text similarity `0.0030`, matching Letter geometry, and visual comparison unavailable.

Current DD-393 comparison artifact: 316 foreground objects, 36 pages, PDF SHA-256 `d29ebc22961d514fdf249513b3f193c2b9be47c171fc97b9c50e9f58266c9e3c`, PNG SHA-256 `594a33986291a3ab893da15aa6aba79bf086cb6bc63fca1544e28f862d65b2f7`, normalized extracted-text similarity `0.0030`, matching Letter geometry, foreground-only manifest status, and visual comparison unavailable.

Current DD-394 comparison artifact: 318 foreground objects, 36 pages, PDF SHA-256 `47b63b646cef6d67a7a905458b4d41a604cc5cb5fddcb6f96aa2083c46d02e83`, PNG SHA-256 `50291263a55070ccb5d9e9778c8e6bdb798c5c64c8c49c4c886a8b38126ae276`, normalized extracted-text similarity `0.0032`, matching Letter geometry, foreground-only manifest status, and visual comparison unavailable.

Editable candidate artifact: [`artifacts/isda-editable-candidate.pdf`](../artifacts/isda-editable-candidate.pdf)  
Candidate API report: [`artifacts/isda-editable-candidate-response.json`](../artifacts/isda-editable-candidate-response.json)

## What was built

The current comparison fixture is represented as an application-owned legacy-form template in the `Legal Agreements` folder using the validated locked-PDF background contract. This is a temporary visual baseline only. The foreground now contains source-aligned editable content for all 36 pages, including semantic Schedule and execution objects on pages 29–36 and a bound Schedule table on page 33, but it does not yet satisfy the product requirement for complete clause-level reconstruction and exact editable source reproduction.

The template contains a 36-page locked source background, Letter portrait page settings, zero foreground margins, and a bounded JSON Schema retained for future overlay fields:

```json
{
  "agreement_date": "31 December 2002",
  "party_x": "Party X",
  "party_y": "Party Y"
}
```

## Source and generated evidence

| Measure | Source | Generated | Result |
| --- | ---: | ---: | --- |
| Pages | 36 | 36 | Page count preserved |
| Page size | 612 x 792 pt | 612 x 792 pt | Letter geometry preserved |
| Normalized text similarity | — | 0.9989 | Source text layer preserved through background merge |
| Source font resources | Times New Roman / Times variants | Preserved from source background | Foreground overlay fonts remain a future concern |
| Images | 0 | 0 | No rasterization introduced |
| Page-number text | Source footer numbering | Source footer numbering | No duplicate foreground numbering |

SHA-256:

- Source: `19b1443c9a46d213df12461548d49bbd457f5bafeee6df3cdc6605285b22d925`
- Generated aligned artifact: `ed06d7f16f2b1eb80f6d38d2f4dafee6ca2f5ee534ebeb0ce53bd72ef866734a`

## Fidelity result

The previous fixture converted each page into a normal flowing text block. That approach started content at the top-left and lost the source’s positioned typography, whitespace, dotted rules and page-specific composition.

The revised fixture uses the original PDF as a locked page background and generates a bounded blank foreground with the same 36 Letter pages. This preserves the supplied sample’s page geometry, selectable text, typography and legal-form composition instead of approximating them with reflowed paragraphs. It is comparison evidence, not the intended end-state authoring workflow.

## Remaining limitations

- This is source-backed rather than an editable arbitrary-PDF reconstruction.
- All pages now have semantic ownership; pages 17-36 expose split clause objects and a bounded first set of separate Schedule, field and signature objects. Pages 9-16 still contain mostly page-owned source-aligned summaries.
- Process-agent, Office, notice, tax, payment-netting and measured Schedule election paths are represented in the version-three schema; complete option semantics and coordinate-bound field mapping remain incomplete.
- Page 33 retains the editable repeatable table, while exact clause segmentation, complete Schedule table coverage and source geometry remain open.
- Editable overlay fonts remain subject to the existing E4-06 font/licence gate.
- Representative Schedule, notice, netting and signature fields now carry provisional millimetre coordinates derived from source text positions; image-level calibration remains open.
- Native-reader, second-engine, accessibility and legal-document approval remain open.

## Validation performed

- Deployed API render of `isda-template-v4` passed through the Chromium candidate and locked-background merge path.
- `pypdf` comparison passed for 36 pages, Letter geometry and source text-layer preservation.
- Normalized text similarity improved from 0.9505 to 0.9989.
- `generated-isda-aligned.pdf` is 863,700 bytes.

The supplied PDF was also inspected with local text extraction for pages 25–36. That inspection confirms the observed Schedule regions for counterparty details, termination elections, tax representations, document delivery, notices, Process Agent, Offices, Calculation Agent, netting and signatures. Text extraction is source-location evidence only; it does not establish exact coordinates, legal interpretation or reader fidelity.

## Historical editable candidate comparison

The current editable definition contains 230 declarative objects. The live PDF endpoint correctly rejects this definition at the configured 128-block synchronous limit; that safety guard was preserved. The corrected local CPU Chromium foreground baseline, rendered without the locked background, measures 36 pages at `612 × 792 pt`, `154049` bytes and normalized extracted-text similarity `0.0015`. The page-aligned diagnostic compares all 36 pages, with mean similarity `0.0253`, minimum `0.0009` and maximum `0.0856`. These metrics are not editable-fidelity approval. Native-reader, visual and glyph correctness remain unapproved. See [DD-352](design-decisions.md#dd-352), [DD-353](design-decisions.md#dd-353), [DD-354](design-decisions.md#dd-354), [DD-355](design-decisions.md#dd-355), [DD-356](design-decisions.md#dd-356), [DD-357](design-decisions.md#dd-357), [DD-358](design-decisions.md#dd-358), [DD-359](design-decisions.md#dd-359), [DD-360](design-decisions.md#dd-360), [DD-361](design-decisions.md#dd-361) and [DD-362](design-decisions.md#dd-362).

These measurements are reproducible with [`scripts/compare_isda_candidate.py`](../scripts/compare_isda_candidate.py). The current report records source SHA-256 `19b1443c9a46d213df12461548d49bbd457f5bafeee6df3cdc6605285b22d925`, candidate SHA-256 `c2c76d1c981479834ab3a7a4692e8ef8c80970663011a48b68e8419a657fab38`, 36 pages each and Letter `612 × 792 pt`. It now includes page-aligned text lengths/similarities and a page-count invariant; it deliberately leaves `visual_comparison: null`, `native_reader_review: pending` and `second_engine_review: pending`. See [DD-329](design-decisions.md#dd-329) through [DD-361](design-decisions.md#dd-361).

Provisional source-region evidence is recorded by [`scripts/measure_isda_source.py`](../scripts/measure_isda_source.py) in [`artifacts/isda-source-measurements.json`](../artifacts/isda-source-measurements.json). It covers all 36 Letter pages, extracted text density and first text origins. Those origins are calibration inputs only; they do not establish final glyph geometry or visual equivalence. See [DD-332](design-decisions.md#dd-332).

The foreground baseline now wraps page-owned blocks in relative page surfaces so provisional absolute Schedule/signature coordinates cannot escape their page. The regenerated baseline has 179 objects, zero missing field bindings and deterministic HTML/PDF/PNG hashes; it preserves the 36-page page-owned grouping and proves renderer containment, not source fidelity. See [DD-333](design-decisions.md#dd-333), [DD-336](design-decisions.md#dd-336), [DD-344](design-decisions.md#dd-344), [DD-345](design-decisions.md#dd-345), [DD-346](design-decisions.md#dd-346), [DD-347](design-decisions.md#dd-347), [DD-348](design-decisions.md#dd-348), [DD-349](design-decisions.md#dd-349), [DD-350](design-decisions.md#dd-350), [DD-351](design-decisions.md#dd-351) and [DD-352](design-decisions.md#dd-352).

The fixed-corpus comparison harness also ran locally with browser network disabled. Its report records deterministic HTML, Chromium PDF and full-page PNG SHA-256 values for multilingual and pagination fixtures, plus Python `3.13.7`, Node `22.23.1`, Playwright `1.63.0`, Chromium `153.0.8010.12`, PDF metadata and bounded font-object inventories. These are reproducibility and inspection artifacts only: the report intentionally leaves `visual_comparison` and `native_reader_scores` as `null`, and does not establish glyph coverage, visual equivalence, native-reader behavior or second-engine agreement. See [`artifacts/render-candidate-comparison.json`](../artifacts/render-candidate-comparison.json) and [DD-322](design-decisions.md#dd-322).

## Historical bounded-slice evidence

The current editable definition contains 242 declarative objects after the page-1–4 clause split. The local CPU Chromium foreground baseline is 36 pages and `154601` bytes, with candidate SHA-256 `cfa5012a5425082ec0ff30edf1855bf4359b36eea6a3edafbfabb8b5246db706`, normalized extracted-text similarity `0.0014`, page mean `0.0260`, minimum `0.0009` and maximum `0.0764`. This remains locked-source diagnostic evidence only; visual comparison, native-reader review and second-engine review remain pending. See [DD-363](design-decisions.md#dd-363).

Latest page-5–8 foreground evidence: the current editable definition contains 265 declarative objects. The local CPU Chromium baseline is 36 pages and `155672` bytes, candidate SHA-256 `6c7fc21ed77203025c9a007f000d3b4cd21863fb50bb74954d2d1234a62aa362`, normalized extracted-text similarity `0.0014`, page mean `0.0271`, minimum `0.0032` and maximum `0.0764`. This remains locked-source diagnostic evidence only; visual comparison, native-reader review and second-engine review remain pending. See [DD-364](design-decisions.md#dd-364).

Latest page-9–16 foreground evidence: the current editable definition contains 276 declarative objects. The local CPU Chromium baseline is 36 pages and `156269` bytes, candidate SHA-256 `bd4eea22961d03865b8b623684df03c5ae3dcb4c5a95818f66ae80b2138e3f03`, normalized extracted-text similarity `0.0014`, page mean `0.0275`, minimum `0.0032` and maximum `0.0764`. This remains locked-source diagnostic evidence only; visual comparison, native-reader review and second-engine review remain pending. See [DD-365](design-decisions.md#dd-365).

Latest corrected pages-9–27 foreground evidence: the current editable definition contains 293 declarative objects. The local CPU Chromium baseline is 36 pages and `157156` bytes, candidate SHA-256 `e8227518df43be8c1a1ab21e7d50c71a1b33b678736b8c09d2efa4ee99158b84`, normalized extracted-text similarity `0.0014`, page mean `0.0284`, minimum `0.0032` and maximum `0.0764`. This remains locked-source diagnostic evidence only; visual comparison, native-reader review and second-engine review remain pending. See [DD-366](design-decisions.md#dd-366).

Latest Schedule/execution foreground evidence: the current editable definition contains 301 declarative objects. The local CPU Chromium baseline is 36 pages and `157918` bytes, candidate SHA-256 `e4af46cc5d84092abeb4592dc3ac1432fcb74994e78459639b4374f3dba7bb8e`, normalized extracted-text similarity `0.0015`, page mean `0.0282`, minimum `0.0032` and maximum `0.0764`. This remains locked-source diagnostic evidence only; visual comparison, native-reader review and second-engine review remain pending. See [DD-367](design-decisions.md#dd-367).

Latest opening-page binding evidence: the editable definition contains 305 declarative objects, including explicit agreement-date, Party A legal-name and Party B legal-name fields on source page 1. The local CPU Chromium baseline is 36 pages and `157950` bytes, candidate SHA-256 `2a906cb925d2a05ba8e9adcf29d074dc894c919de29b39f03e5d783c65023566`, normalized extracted-text similarity `0.0015`, page mean `0.0278`, minimum `0.0032` and maximum `0.0604`. This remains locked-source diagnostic evidence only; visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-369](design-decisions.md#dd-369).

Latest Master Agreement execution evidence: the editable definition contains 307 declarative objects. Page 28 now has separate execution statement and authorisation-attestation signature objects. The local CPU Chromium baseline is 36 pages and `158005` bytes, candidate SHA-256 `b53c34b59eee7004cf82519ad0bbfa88944a1f116a21ff92757c451803b7fcbf`, normalized extracted-text similarity `0.0015`, page mean `0.0277`, minimum `0.0032` and maximum `0.0604`. This remains locked-source diagnostic evidence only; visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-370](design-decisions.md#dd-370).

Latest early-page semantic cleanup evidence: the 307-object foreground candidate remains 36 pages and `157816` bytes with candidate SHA-256 `b65aea0f8967e735c28ff90d65647ad6cdbae04b53ad6f790fae972afab9790e`, normalized extracted-text similarity `0.0015`, page mean `0.0289`, minimum `0.0023` and maximum `0.1155`. Page 1’s diagnostic similarity increased to `0.1155` after removing duplicated container prose; this does not establish visual fidelity. Visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-371](design-decisions.md#dd-371).

Latest definition-container cleanup evidence: the 307-object foreground candidate remains 36 pages and `157091` bytes with candidate SHA-256 `52d64c34fc03a63d5d87c2e3ee3875ecb156822cd87cac589098848e32b1bbd2`, normalized extracted-text similarity `0.0015`, page mean `0.0281`, minimum `0.0023` and maximum `0.1155`. Pages 21-27 now avoid duplicated container prose while preserving child definition fields and clauses. This remains diagnostic only: visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-372](design-decisions.md#dd-372).

Latest termination-container cleanup evidence: the 307-object foreground candidate remains 36 pages and `157001` bytes with candidate SHA-256 `ce031f8e4a417e3aa58cfef7ee0a0fdd23df04e672f9cb37a9011ae0fee6cbf7`, normalized extracted-text similarity `0.0015`, page mean `0.0278`, minimum `0.0023` and maximum `0.1155`. Pages 11-15 now avoid duplicated termination/designation/transfer container prose while preserving child clauses. This remains diagnostic only: visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-373](design-decisions.md#dd-373).

Latest geometry diagnostic: the comparison harness checks all aligned page MediaBoxes. The current candidate reports `page_count_match: true`, `page_size_match: true`, and `page_size_mismatches: []` across 36 Letter pages. This does not establish visual fidelity; visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-374](design-decisions.md#dd-374).

Latest calibration metadata evidence: the 307-object candidate has 27 absolute semantic objects, all marked as provisional source-region coordinates from `isda-source-measurements`. Geometry remains 36/36 Letter pages with no MediaBox mismatches. This remains calibration metadata and geometry evidence only; visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-375](design-decisions.md#dd-375).

Latest Schedule-continuation evidence: the 307-object candidate remains 36 pages and `156841` bytes with candidate SHA-256 `7e02d78df1446582b0554be6f3c9f379e888878928eeabdbb27bdb7d35d2d891`, normalized extracted-text similarity `0.0015`, page mean `0.0267`, minimum `0.0023` and maximum `0.1155`. Page 30’s parent now contains only its continuation heading; child Schedule objects remain editable. This is diagnostic only: visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-376](design-decisions.md#dd-376).

Latest representation/interest cleanup evidence: the 307-object candidate remains 36 pages and `156690` bytes with candidate SHA-256 `f6af24b07c4baa5d1960faddd4b1b6aa9fdb9c43473dc226123f18c700bc2850`, normalized extracted-text similarity `0.0026`, page mean `0.0271`, minimum `0.0023` and maximum `0.1155`. Pages 4 and 17 now avoid duplicated parent prose while preserving child clauses. This remains diagnostic only: visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-377](design-decisions.md#dd-377).

Latest Office-container evidence: the 307-object candidate remains 36 pages and `156609` bytes with candidate SHA-256 `1a1f671849aeeb4035c1d36f79900d27f94be7f4acf28db3146e91b5b20af8f0`, normalized extracted-text similarity `0.0026`, page mean `0.0271`, minimum `0.0023` and maximum `0.1155`. Page 19 now avoids duplicated Office parent prose while preserving child Office clauses. This remains diagnostic only: visual comparison is `null`, native-reader review is pending and second-engine review is pending. See [DD-378](design-decisions.md#dd-378).

## Historical recommended next step

Continue by replacing the remaining page-owned summaries with source-measured clause and field objects, expanding the governed ISDA schema, and calibrating positions and typography against the source. Then add reviewed visual comparison and an approved second engine or native-reader evidence if those tools and licences become available. The locked-background shortcut remains a comparison baseline only; the final result must be editable through the tool and validated against this source without relying on the source PDF as document content.

## Current authoritative comparison — DD-412

The current editable definition contains 381 semantic objects across 36 page-owned surfaces, with 147 bound scalar fields and zero missing sample bindings. The foreground-only candidate is `artifacts/isda-foreground-baseline/isda-foreground.pdf` with SHA-256 `c2ff1a32121aaac3f70cae93a413e49aca55251fd41bd7aaafb4998d97954911`; its manifest declares `locked_background: omitted`. The current comparison report records source SHA-256 `19b1443c9a46d213df12461548d49bbd457f5bafeee6df3cdc6605285b22d925`, 36/36 pages, matching Letter MediaBoxes, normalized extracted-text similarity `0.0136`, mean page similarity `0.0358`, `visual_comparison: null` and `visual_comparison_status: unavailable-no-local-rasterizer`. These are structural and text-layer diagnostics only. Native-reader, visual, second-engine, font/licensing, accessibility and legal review remain pending; collect them using [`docs/isda-review-evidence-checklist.md`](isda-review-evidence-checklist.md).

## Historical bounded-slice evidence
Latest DD-379 foreground regeneration: the local CPU Chromium candidate contains 307 semantic objects with zero missing fields. The deterministic hashes are `html 5ed072c6d6ab7ed45e9bc02005f6a07912d9ce319eebf24916bceec7f6153ce7`, `pdf 047657595d8deedbc0d4699f0dea2d5a2f13d209b14c9fb13a2c5e44f5132e79` and `png 56c167150072b9d8761b6e5888aef2cbdf975e687b3831de868aedf1bf33b9e3`. The locked-source comparison remains diagnostic: 36 pages, matching 612x792-point Letter geometry, no page-size mismatches, normalized extracted-text similarity `0.0015`, mean page similarity `0.0250`, `visual_comparison: null`, `native_reader_review: pending` and `second_engine_review: pending`. The locked source PDF remains comparison input only and is not candidate document content.
Latest DD-382 foreground comparison: the local CPU Chromium candidate contains 307 semantic objects with zero missing fields and 36 physical Letter pages. Candidate hashes are `html 5f1d7acc...`, `pdf fcb511e8...`, `png 7cdcc2f2...`; current comparison reports `page_count_match: true`, `page_size_match: true`, no MediaBox mismatches, normalized extracted-text similarity `0.0026`, page mean `0.0265`, `visual_comparison: null`, `native_reader_review: pending` and `second_engine_review: pending`. The locked source PDF remains comparison input only and is not candidate document content.
Latest DD-383 comparison: the 307-object local CPU Chromium candidate remains 36 Letter pages with zero missing fields. The current deterministic hashes are `html 5f1d7acc6b21024a86ec6fc63f9a8c0bb04a5781479a70e9d2428265ca06707f`, `pdf ebdf6df9dac5b12505155ac858e26c9c75740c669dd89e48d29b21ec6e3ab6dc` and `png 7cdcc2f298f8b30f44d898d4678e5688038ae0a892599e07f8532a550351ca81`. Page count and MediaBoxes match (`normalized_text_similarity 0.0026`, page mean `0.0265`); `visual_comparison: null`, `native_reader_review: pending`, and `second_engine_review: pending`. The source PDF remains comparison input only.
The available offline Chromium instance cannot rasterize the locked source PDF for page-image comparison: navigating to the local PDF starts a download. This is an environment/tooling limitation, not visual-fidelity evidence; `visual_comparison` remains `null` and native-reader/second-engine review remain pending. See [DD-384](design-decisions.md#dd-384).
## Historical comparison boundary — DD-385

The comparison report now records `visual_comparison_status` separately from the intentionally null `visual_comparison` value. In the current environment the status is `unavailable-no-local-rasterizer`: the allow-listed local rasterizer tools are absent, and offline Chromium treats both local `file://` and locally served HTTP PDF navigation as a download (`Download is starting`). This is a tooling limitation, not visual-fidelity evidence. Native-reader and second-engine review remain pending.

Historical diagnostic artifact: 36/36 pages, matching Letter MediaBox geometry, normalized extracted-text similarity `0.0026`, page mean `0.0265`, `visual_comparison: null`, and `visual_comparison_status: unavailable-no-local-rasterizer`. The current authoritative comparison is recorded above.
