# ISDA review evidence checklist

Updated: 2026-10-01

This checklist defines the evidence required to close the external acceptance gates. It is a collection template, not a review result or approval. A row is not complete because a command ran; it requires the named artifact and an attributable reviewer or tool record.

## Candidate under review

- Locked source: `2002-ISDA-Master-Agreement.pdf`
- Locked source SHA-256: `19b1443c9a46d213df12461548d49bbd457f5bafeee6df3cdc6605285b22d925`
- Foreground candidate: `artifacts/isda-foreground-baseline/isda-foreground.pdf`
- Foreground candidate SHA-256: `c2ff1a32121aaac3f70cae93a413e49aca55251fd41bd7aaafb4998d97954911`
- Candidate manifest: `artifacts/isda-foreground-baseline/isda-foreground.json` (`locked_background: omitted`)
- Comparison report: `artifacts/isda-editable-comparison.json`
- Current structural invariant: 36 pages, matching Letter MediaBox geometry

## Native-reader review — pending

Record one row per reader/version/OS. Attach the opened candidate, screenshots or review notes, and the exact result.

| Reader/version/OS | Pages exercised | Opened | Page count/size | Text selection | Clipping/wrapping | Signature regions | Reviewer/date | Artifact | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | 1, 29, 33, 34, 36 | pending | pending | pending | pending | pending | pending | pending | pending |

Required result: a named reader/version and attributable review evidence. Chromium download behavior is not native-reader approval.

## Visual page comparison — pending

Record the approved rasterizer, version, dependency/license source, rendering command, output hashes, and a page-aligned visual review. The locked source and candidate must be rasterized separately; the source must not be merged into candidate content.

| Rasterizer/version | Source image set | Candidate image set | Diff artifact | Pages reviewed | Reviewer/date | Result |
| --- | --- | --- | --- | --- | --- | --- |
| — | pending | pending | pending | 1–36 | pending | pending |

Extracted-text similarity and MediaBox equality remain diagnostics and cannot fill this row.

## Independent second-engine review — pending

Record an independently maintained rendering engine, version, environment, command, candidate output hash and comparison result. An alternate invocation of the same Chromium engine does not satisfy this gate.

| Engine/version | Environment | Candidate output SHA-256 | Comparison artifact | Reviewer/date | Result |
| --- | --- | --- | --- | --- | --- |
| — | pending | pending | pending | pending | pending |

## Fonts and licensing — pending

Attach the dependency lock, font object inventory, actual font/dependency licence texts and a review decision against the project allow-list. Font names extracted from a PDF are not licence evidence.

| Dependency/font | Version | Source | Licence artifact | Allow-list decision | Reviewer/date | Result |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | pending | pending | pending | pending |

## Accessibility — pending

Attach the accessibility test method and results for reading order, text selection, keyboard navigation where applicable, contrast, headings/structure and assistive-technology behavior. Do not infer certification from semantic HTML or a passing browser test.

| Method/tool/version | Scope | Artifact | Reviewer/date | Result |
| --- | --- | --- | --- | --- |
| — | candidate PDF and editor | pending | pending | pending |

## Legal/domain review — pending

Attach the bounded review scope, reviewer qualification, source/candidate versions, identified deviations and disposition. Semantic decomposition and local fixtures are implementation evidence, not legal approval.

| Reviewer/qualification | Scope/pages | Source/candidate versions | Findings artifact | Date | Result |
| --- | --- | --- | --- | --- | --- |
| — | pending | pending | pending | pending | pending |

## Closure rule

Update [`docs/isda-acceptance-gates.md`](isda-acceptance-gates.md) only when the corresponding artifact exists and the evidence can be independently inspected. Until then, retain `pending`; do not convert diagnostic comparison metrics into approval.
