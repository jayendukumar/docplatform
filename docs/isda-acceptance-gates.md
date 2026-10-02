# ISDA acceptance gate matrix

Updated: 2026-10-01

This matrix is a status record, not an approval. The locked source PDF remains comparison input only.

| Gate | Current evidence | Status | Remaining evidence |
| --- | --- | --- | --- |
| Semantic page ownership | Offline audit: 381 objects, pages 1-36, required Schedule/execution anchors | Pass | None for this bounded slice |
| Editor semantic discoverability | Structure-tree nodes expose stable semantic ID, kind and page metadata; focused Playwright selection check passes | Pass | None for this bounded slice |
| Governed schema/sample contract | Schema version 3, 147 bound scalar fields, non-empty local samples, two validated repeatable tables | Pass | None for this bounded slice |
| Safe local rendering | Declarative renderer, local CPU foreground baseline, zero missing fields | Pass | Broader product scope remains separate |
| Page geometry | Foreground candidate: 36 pages, all MediaBoxes match Letter | Pass | This is geometry, not visual fidelity |
| Locked-PDF boundary | Candidate manifest declares `locked_background: omitted`; comparison enforces it when supplied | Pass | None |
| Extracted-text comparison | Superseded by the E16 harness (DD-418): word F1 `0.333` (precision `0.925`, recall `0.203`), 0.3% of matched words within 3 mm, median size delta `1.71 pt`. The earlier `0.0136` similarity relied on pypdf extraction defects | Diagnostic only | Text and geometry diagnostics cannot prove visual equivalence |
| Visual page comparison | E16 PDFium raster diagnostic (DD-420): ink F1 `0.069` at 72 dpi / 1 mm tolerance, all 36 pages below 0.5, red/blue diff images under `artifacts/fidelity/` | Diagnostic only; fails | Approved source/candidate rasterization and review |
| Native-reader review | No Acrobat/Chrome/Preview approval evidence | Pending | Reader test matrix and recorded results |
| Second rendering engine | No independent engine review evidence | Pending | Independent engine output and comparison |
| Fonts/licensing | Candidate font object inventory only | Pending | Actual dependency/font licence review and glyph/shaping evidence |
| Accessibility | No certification or complete accessibility review claimed | Pending | Accessibility test evidence |
| Legal approval | Semantic text remains bounded implementation content, not legal approval | Pending | Qualified legal/domain review |

Current artifacts: [offline audit](../artifacts/isda-template-audit.json), [foreground manifest](../artifacts/isda-foreground-baseline/isda-foreground.json), and [comparison report](../artifacts/isda-editable-comparison.json). External-gate evidence must be collected using the [review evidence checklist](isda-review-evidence-checklist.md).
