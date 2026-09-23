---
name: docplatform-rendering
description: Design or verify this platform's multilingual editor, fonts, template logic, pagination, and PDF or Word output. Use when rendering correctness or preview parity can change.
---

# Multilingual document rendering

Read E2, E4, E5 and the affected E6 stories in `docs/epics.md`, plus DD-003 and DD-007 through DD-009 in `docs/design-decisions.md`. Paths are relative to the repository root.

The default renderer has not been selected. E4-01 requires empirical comparison and native-reader grading. Chromium is only a candidate; use the same fixtures for WeasyPrint or another proposed alternative.

- Capture template/data/locale, renderer version, exact font files/hashes, page settings and environment with each fixture. Noto CJK is a separate font set; do not assume a generic Noto download covers it.
- Exercise Arabic, Hebrew, Hindi, Tamil, Thai, Chinese and Japanese; add Korean for E4-05. Cover mixed-direction numbers/punctuation, combining marks, font fallback, table headers, long rows, keep-together behavior and missing translations.
- Verify editing separately: caret movement, selection, copy/paste, IME composition, undo and keyboard access. Correct rendered glyphs do not prove correct text entry.
- Use the server-generated artifact as final preview truth. Fast editor previews may be approximate but must not silently promise final pagination.
- Combine visual comparisons with font/glyph reports, text/layout checks and native-reader review. Font cmap coverage alone does not prove shaping correctness. Do not approve a changed baseline just to make tests pass.
- Treat Word-template merging and Word-to-PDF conversion separately from designer PDF generation. Record tested constructs and fidelity failures; do not imply arbitrary cross-format round trips.
- Bound template expressions and staged assets. Arbitrary code, network fetches and credentials do not belong inside renderer execution.

Record the engine comparison, evidence, accepted limitations and any changed behavior in `docs/design-decisions.md`, including an explicit pending status when native review or licence evidence is absent. PDF/A and accessible tagged PDF are later release requirements, not properties inferred from a PDF opening successfully.
