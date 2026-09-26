# Rendering candidate evidence

The service currently returns `deterministic-html-0.1` as a bounded server-preview candidate. A separate evidence command can print that HTML through the locally installed, pinned Playwright Chromium package:

```powershell
node scripts/render_chromium_candidate.mjs artifacts/candidate.html artifacts/chromium-candidate.pdf artifacts/chromium-candidate.json artifacts/chromium-candidate.png
```

The command reads only a local HTML file, aborts browser requests, emits a PDF and optional full-page PNG, and writes a manifest containing the browser version, source metadata, metadata observed in the PDF Info/catalog, and a bounded PDF-object font inventory. The inventory lists unique `/BaseFont`/`/FontName` values, embedded-font-file markers and `/ToUnicode` map counts; it deliberately does not infer glyph coverage or native-reader support. Chromium's native print output omitted author and language in the fixture; the harness now applies a dependency-free incremental metadata patch and labels that transformation explicitly. The PNG SHA-256 is a reproducible visual baseline, not human visual approval. This is candidate evidence, not native-reader or production-engine acceptance. The harness is not wired into the production API and does not establish the default renderer. E4-01/E6-01 remain open until the same fixed corpus is rendered by the candidates, exact font/environment manifests are captured, visual comparisons are reviewed, and Acrobat, Chrome and Preview/native-reader evidence confirms embedded fonts and output behavior.

## Fixed-corpus comparison

After the pinned frontend dependencies and Chromium browser are available, compare the two current candidates with:

```powershell
backend\.venv\Scripts\python.exe scripts/compare_render_candidates.py --output artifacts/render-candidate-comparison.json
```

The report records per-fixture SHA-256 hashes for HTML, PDF and Chromium full-page PNG baselines, detected scripts, source metadata, observed PDF metadata, and Python/Node/browser versions. The script fixture contains explicit Unicode code points for Arabic, Hebrew, Devanagari, Tamil, Thai, Chinese, Japanese and Korean; its detected-script list is a source-integrity check, not a shaping result. `visual_comparison` and `native_reader_scores` intentionally remain null; hashes establish reproducibility, not visual equivalence or reader approval.

## Production adapter configuration

The API selects Chromium by default through `pdf_renderer = "chromium"`. The adapter accepts a JSON-array command through `chromium_renderer_command`; the legacy `pdf_renderer_command` remains a compatibility fallback. Prince is opt-in with `pdf_renderer = "prince"` and `prince_renderer_command`. The Prince adapter adds `--no-local-files`, `--no-network`, the optional `--license-file` value, and Prince's `input.html -o output.pdf` output form without exposing template-controlled arguments.

Prince can be installed for permitted testing before a production commercial license is obtained. The free/non-commercial terms add watermark and attribution conditions; commercial customer output or redistribution requires the appropriate YesLogic license. No production Prince license is bundled or claimed by this repository.
