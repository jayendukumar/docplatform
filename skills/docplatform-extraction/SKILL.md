---
name: docplatform-extraction
description: Implement or evaluate document ingestion, OCR adapters, structured extraction, confidence, source overlays, and human correction in this platform. Use for the scan-to-reviewed-data workflow.
---

# Extraction and provenance

Read affected E8/E9/E10 stories and E5-08/E7-05 where relevant in `docs/epics.md`; use DD-010 through DD-012 in `docs/design-decisions.md`. Resolve paths from the repository root.

Docling and PaddleOCR are named requirements; E8-08 also needs a third engine behind the contract. Tesseract is proposed, not yet integrated. Local CPU-only processing must remain usable without provider calls.

- Distinguish digital text from scans and preserve routing evidence. Engine adapters declare their capabilities; do not invent tables, scores or geometry to make dissimilar engines look equivalent.
- Version the PageModel and retain page dimensions, rotation, coordinate system, reading order, source IDs and geometry. Test overlays under rotation/zoom and different page sizes. Link Markdown elements back to the authoritative JSON model.
- Keep raw and normalized field values, schema/engine/model versions and source spans/boxes. Missing or unsupported fields stay explicit; every extracted value needs traceable provenance.
- Separate OCR confidence from calibrated field correctness. Use labelled, held-out evaluation documents; report field and line-item metrics by schema/language, calibration and failure examples. Do not select an accuracy target without a baseline or leak calibration examples into final evaluation.
- Use Decimal-aware normalization for monetary fields and explicit locale parsing rules. Validation failures require review even if an OCR score is high.
- Preserve correction history with actor/time and original/new values. Protect edits with concurrency checks. Approved snapshots feed generation; changed approved data creates a new revision requiring review.
- Treat source documents as untrusted input. Enforce parser/resource limits and keep secrets/network out of child execution. Do not export documents to a cloud model without configured authorization.

Record contract changes, scoring choices, normalization assumptions and review defaults in `docs/design-decisions.md`. Keep rendering language support distinct from extraction language/schema accuracy. AI-generated suggestions and future confidence-based auto-approval need their own explicit policy and release scope.
