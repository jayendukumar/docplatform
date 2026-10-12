# E21 — Source-document template creation and comparison (proposed)

Status: Proposed scope addition. This document does not change the generated backlog in `docs/epics.md`.

Related baseline stories: E13-05, E13-08, E2-08, E5-08, E6-01 and E7-01.

## Goal

Let a template owner start from a source PDF or Word document, understand what the system could and could not reproduce, upload the source, review the system's interpretation, generate an editable draft template, and compare the generated output against the original source before saving or publishing.

The workflow must be source-truthful rather than fidelity-promising. It should preserve the source's observable structure and content where the platform has supported equivalents, while clearly identifying likely differences caused by unavailable fonts, styling features, images, unsupported layout constructs or renderer limitations.

## Customer workflow

1. The owner chooses **Create from source document**.
2. The application presents a required limitation disclosure:
   - the result is an automatically generated draft;
   - exact visual reproduction is not guaranteed;
   - missing fonts, styling, images, unsupported document features and renderer differences may change the result;
   - the owner must review, edit and approve the draft before it becomes publishable.
3. The owner uploads one PDF or Word source document. The application validates type, size and safety limits, stores the original immutably, and shows ingestion progress.
4. The system extracts a bounded PageModel containing pages, text, tables, images, layout regions, candidate fixed regions, candidate variable regions, source coordinates, extraction versions and confidence/provenance.
5. The owner is shown the system's interpretation beside the source: detected pages, regions, likely fields, tables, repeated content, images, fonts and unsupported features. Each suggestion can be accepted, corrected or rejected.
6. The system generates an editable draft template from the approved interpretation. It uses declarative template blocks and approved extraction values as sample data; it does not embed arbitrary source code or grant network access.
7. The draft opens in the existing editor. The owner can edit the document tree, bindings, components, page settings, styles, assets and sample data.
8. The owner clicks **Compare with original**. The application opens a new browser tab in the same browser window with the original source PDF on the left and the generated PDF on the right. Each pane has independent page navigation, zoom and vertical/horizontal scrolling; the panes are not forced to scroll together.
9. The comparison view reports page-count differences, render failures and available visual/text comparison evidence. It does not label a draft as identical without evidence.
10. The owner returns to the editor, makes corrections, repeats the comparison, and saves the result as a draft version. Publication remains subject to the existing review/approval policy.

## Proposed stories

| ID | Story | Priority | Size | Acceptance outcome |
| --- | --- | --- | --- | --- |
| E21-01 | Owner: understand source-to-template limitations before upload | Must | S | Disclosure is shown before file selection and must be acknowledged before processing; missing fonts, styling, images and unsupported features are named plainly. |
| E21-02 | Owner: upload a PDF or Word source document safely | Must | M | One source is validated, stored immutably, linked to a creation session, and processed through the existing ingestion/security limits. |
| E21-03 | Owner: inspect the system's source interpretation | Must | L | Pages, text, tables, images, fixed regions, candidate variable regions, unsupported features, confidence and source coordinates are visible and reviewable. |
| E21-04 | Owner: accept, correct or reject detected regions and fields | Must | L | Corrections retain original values, normalized values, provenance, versions and correction history; only approved interpretation data feeds generation. |
| E21-05 | Owner: generate an editable draft template from an approved interpretation | Must | XL | The system creates a versioned declarative template with editable blocks, bindings, sample data, assets and page settings; no arbitrary code or network access is introduced. |
| E21-06 | Owner: edit the generated draft in the existing template editor | Must | L | The draft opens in the editor and supports the existing component, document-tree, preview, save and version workflows. |
| E21-07 | Owner: compare the generated document with the original source | Must | L | Compare opens a new browser tab containing two PDF panes with independent page navigation, zoom and scroll controls. |
| E21-08 | Owner: understand comparison differences and limitations | Must | M | The comparison view identifies page-count/render failures and available text/visual differences without claiming native-reader or pixel-perfect fidelity. |
| E21-09 | Admin: govern source-document generation | Must | L | Processing is local by default, optional external AI is explicit, source access is authorized, processing is bounded and isolated, and audit/version links are retained. |
| E21-10 | Dev: evaluate source-to-template generation | Must | XL | A labelled corpus measures structural preservation, field/region accuracy, page count, text overlap and visual differences; releases do not claim accuracy beyond recorded evidence. |

## Product and technical boundaries

- The original source is immutable and remains available for comparison.
- The generated template is a draft suggestion, never an automatic publication.
- Extraction values, source locations, model/engine versions and corrections are retained.
- Approved interpretation snapshots, not raw model output, feed template generation.
- Templates remain declarative and cannot execute arbitrary code or access networks.
- CPU-only local processing is supported; external AI providers are optional and configured deliberately.
- Fonts and images are reused only when safely available and licence-approved. Missing assets produce visible warnings rather than silent substitution claims.
- PDF and Word are separate input paths where their structure and fidelity limits differ.
- The comparison UI compares available generated PDF evidence. It does not establish native-reader approval, accessibility certification, final renderer selection or pixel-perfect equality.
- The new-tab comparison is a browser interaction; it must not discard unsaved editor changes and should identify which draft version produced the generated PDF.

## Delivery plan

### Phase 1 — disclosure, upload and source session

Reuse ingestion storage, validation, authorization, provenance and job status. Add a source-to-template session that links the immutable source, extraction version, interpretation status and draft template.

### Phase 2 — interpretation review

Expose PageModel regions, candidate fields, tables, images, fonts and unsupported features. Add accept/correct/reject actions with correction history and an approved snapshot boundary.

### Phase 3 — draft generation

Map approved regions to the existing declarative template contract. Generate bindings and sample data, preserve source locations, surface unsupported constructs, and open the result in the existing editor.

### Phase 4 — comparison workspace

Render the current draft to PDF, open a new browser tab, display original/generated PDFs side by side, and give each pane independent page, zoom and scroll controls. Add text/page-count comparison first; add visual diff evidence only after a repeatable rendering baseline exists.

### Phase 5 — evaluation and governance

Run the labelled source corpus, record structural and visual evidence, test malicious files and oversized assets, verify authorization and isolation, and update the status only from observed results.

## Dependencies and open decisions

- E4-01 renderer comparison and font/complex-script evidence remain prerequisites for any stronger fidelity claim.
- E9 extraction confidence/provenance and E5-08 approved-data binding provide the review and data boundary.
- E6-01 PDF generation is required for comparison output.
- E7-01 API parity is required for source sessions, interpretation review, generation and comparison metadata.
- The PDF/Word parsing engine, image extraction fidelity, font identification strategy, visual-diff method, and external-AI policy require separate design decisions and licence review.
- The product must decide whether comparison is available to guest users and how long source files and generated comparisons are retained.
