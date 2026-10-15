# E22 PDF extraction corpus

This is a bounded corpus for E22 PDF ingestion, layout, extraction, and intake-screen work. The checked-in synthetic set contains 12 PDFs covering reports, invoices, contracts, legal-style documents, scanned pages, mixed digital/scanned content, two-column layouts, and complex or multi-page tables. None is a real customer record or operative legal document.

The local `additionaldocs/` folder contains 9 user-provided bank statement PDFs. They are part of local extraction testing, bringing the current total to 21 of the 30-document limit. A metadata-only inspection found six with extractable digital text and three image-only PDFs. Keep these documents local: the folder is excluded from Git because the files may contain private financial information. Do not print extracted document text or include the files in CI artifacts. Use the synthetic fixtures for reproducible CI checks; use `additionaldocs/` only for explicitly run local evaluations and report aggregate outcomes.

`generated/manifest.json` records each synthetic document's family, layout features, scan status, and text anchors. These are fixture labels and initial extraction anchors, not complete gold annotations or accuracy results. The user-provided documents remain unindexed by filename in this checked-in manifest. Add manually reviewed page geometry and logical-structure expectations before using either subset to claim extraction precision, recall, F1, or bounding-box agreement. Keep calibration documents separate from the final held-out evaluation set.

Regenerate the PDFs from the repository root with:

```powershell
node scripts/build_e22_corpus.mjs
```

The generator uses the repository's pinned Playwright package. It enforces the 30-document limit for its 12 synthetic fixtures. Count local `additionaldocs/` PDFs toward the same overall cap before adding fixtures. Grow the corpus only when a new document adds a distinct layout, document family, or regression case; do not add near-duplicates just to increase its size.
