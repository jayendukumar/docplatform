# E20 — Source-faithful document composition and component fidelity (proposed scope addition)

Status: Proposed scope addition. This epic supplements E2 Template editor, E3 Template management, E4 Rendering, E6 Output formats and E18 template examples. It does not rewrite the generated backlog in `docs/epics.md`.

## Outcome

A template owner can reconstruct a branded source document such as the Northbridge Business Memo using editable platform components, without using a locked PDF background. The server-rendered PDF preserves the source document's content, hierarchy, branding, tables, callouts, pagination and footer behavior closely enough to pass a documented visual comparison.

The source-faithful target is not arbitrary DOCX round-tripping. It is a bounded, inspectable composition model with explicit components, deterministic rendering and evidence-backed limits.

## Findings that motivate E20

The Business Memo comparison showed a two-page branded source versus a one-page simplified output. The output omitted the logo/header, subtitle, metadata styling, numbered and bulleted lists, the four-column five-row implementation table, all second-page sections, KPI band, callouts, footer and page numbers. Most omissions were template-construction errors; the remaining gaps are component and pagination capabilities.

## Stories and requirements

| ID | Story | Requirement and acceptance evidence |
| --- | --- | --- |
| E20-01 | Owner: compose reusable branded headers and footers | A reusable document-furniture component supports logo/image, left/center/right zones, document type, rules, colors, confidentiality labels, page numbers and first-page variants. A Business Memo fixture renders the Northbridge mark at top-left, “BUSINESS MEMO” at top-right, a header rule, footer label and page number on both pages. Verify from the server PDF and its page geometry; no locked background is permitted. Builds on E2-03, E2-06 and E2-11. |
| E20-02 | Owner: create semantic numbered and bulleted lists | A list component supports ordered/unordered lists, nesting level, marker style, indentation, spacing, binding runs and keep-with-next behavior. The Business Memo's four numbered changes and three “Why now” bullets remain semantic list items in HTML/PDF extraction, not manually typed marker characters. Verify structure and visual output. |
| E20-03 | Owner: style structured metadata tables | A metadata/table component supports label/value rows, column widths, header visibility, cell padding, vertical alignment, per-cell or per-row background, borders, wrapping and emphasis. It supports both the five-row memo metadata table and a four-column implementation table with a repeating header. Verify long subject wrapping, row count, column count and page continuation. Builds on E2-02. |
| E20-04 | Owner: create branded callouts and KPI bands | A callout component supports title, body, accent rule, fill, padding and keep-together behavior. A metric-band component supports two-to-six KPI cells with label/value hierarchy, background, alignment and responsive fallback. The Business Memo decision/communication callouts and four-cell “Measures we will use” band render without absolute-position hacks. |
| E20-05 | Owner: apply a document brand kit | A reusable brand kit stores approved colors, font stack, logo assets, spacing scale, heading levels, table defaults and footer defaults. Applying the kit updates a template consistently and reports unavailable fonts/assets. Font files and licenses are explicit inputs; no generic font substitution may be presented as fidelity approval. Builds on E2-12 and E4-06/E4-07. |
| E20-06 | Owner: control long-document pagination | Page-flow controls support explicit page breaks, keep heading with following content, keep callout/table rows together, repeating table headers, widow/orphan constraints and first-page versus following-page furniture. The Business Memo remains two pages with the implementation plan starting on page two and no orphaned section headings. Verify with page count, layout boxes and visual comparison. Builds on E2-07 and E6-01. |
| E20-07 | Owner: use source-aware document sections | A section/group component gives a heading, body, list/table/callout children and optional local spacing/theme overrides. It preserves reading order and lets a template creator reconstruct Purpose, Decision, What is changing, Why now, Execution plan, Non-negotiables, Measures, Required action and Communication principle without flattening the document into unrelated paragraphs. |
| E20-08 | Dev: run source-versus-output fidelity checks | A fixture harness records source PDF, template definition, sample data, renderer/version, fonts, page settings and output PDF. It reports page-count differences, text omissions, bounding-box shifts, font/glyph issues and visual overlays. Intentional differences require a reviewed baseline decision. This extends E4-08 and E6-05; it does not claim native-reader approval automatically. |

## Business Memo acceptance fixture

The first conformance fixture is `sampledocs/Northbridge_Business_Memo.pdf` and its editable template equivalent. Acceptance requires:

1. Two A4 pages at the declared page settings, with no locked PDF or page-image background.
2. The header logo, document label, rule, title, subtitle, footer and page number are represented by editable furniture/assets.
3. All source sections and source text are present; omitted source content is a failure, not an acceptable simplification.
4. The metadata table, numbered list, bullet list, four-column implementation table, KPI band and callouts retain their roles and visible hierarchy.
5. The server-generated PDF is the final comparison artifact. Editor preview alone is insufficient.
6. Visual, text/layout and font/glyph reports are captured. Native-reader review and cross-engine approval remain separate gates under E4.

## Explicit non-goals and boundaries

- Reconstructing arbitrary DOCX layout automatically is not part of E20; E6-02/E6-03 remain the Word merge/conversion path.
- A source PDF is not embedded as a visual shortcut. The target remains editable components and approved local assets.
- Exact visual equivalence is not claimed from one Chromium render. The fixture must be reviewed with the rendering evidence required by E4.
- Templates remain declarative and cannot execute code, fetch networks or access credentials.

## Dependencies

E2-01 through E2-08, E2-11/E2-12, E3 template persistence/assets, E4-01/E4-06/E4-08, E5 binding, E6-01/E6-04/E6-05 and E11 sandbox/authorization controls. E20-08 should begin before component implementation so every visual change has a reproducible baseline.

