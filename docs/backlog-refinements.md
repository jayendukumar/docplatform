# Backlog refinements: template workspace and editor

Date: 2026-09-27

The generated `docs/epics.md` remains the source transcription of the supplied backlog and is not rewritten here. This document records the product refinements requested for implementation and maps them to the original story IDs.

## Refined requirements

| Requirement | Source stories | Treatment |
| --- | --- | --- |
| Contextual actions for the selected object, including image alignment and move-left/move-right; irrelevant actions remain visible but disabled | E2-01, E2-03, E2-10 | Implemented as the editor-shell slice. Composite-child selection is the next bounded component slice. |
| Top command bar for undo, redo and save status; left insertion/structure/layers panel; centre canvas; right selected-object properties; bottom diagnostics | E2-01, E2-10, E2-13, E14-01 | Implemented as the editor information-architecture slice. Full WCAG 2.2 AA remains an acceptance gate. |
| Save templates by workspace name and organize them in application-owned folders, never filesystem folders | E3-01, E3-04 | Planned next. Template IDs remain API-owned identifiers; folder IDs must be separate and stable. |
| Select a schema while creating a template; generate and edit a draft schema when none exists | E3-06, E9-01 | Planned next. The editor must bind a template draft to an explicit schema version. |
| Save template versions and schema versions with a one-to-one compatibility relation | E3-02, E3-03, E9-11 | Planned next. A template version may reference exactly one immutable schema version; incompatible changes require a new template version or migration. |
| Submit a template ID and conforming JSON data through an API, including batches | E7-01, E12-04 | Remains backlog-only by request. No new public API, batch route, or completion claim is added in this change. |

## ISDA source-comparison refinement

The 2002 ISDA Master Agreement comparison adds an implementation refinement to the existing PDF-generation stories without rewriting the generated source transcription in `docs/epics.md`:

| Requirement | Source stories | Treatment |
| --- | --- | --- |
| Preserve PDF metadata and emit stable physical page numbers when page numbering is enabled | E6-01, E6-04 | Implemented as a renderer post-processing capability; Chromium CSS page counters are not relied on. Superseded by DD-429: page numbers now come from `@page` margin-box counters, which Chromium resolves; the overlay was also mis-placed by a leaked transform. |
| Allow ordinary text blocks to flow across pages unless `keep_together` is explicitly requested | E2-05, E6-01 | Implemented as a pagination correction; tables, figures and explicit keep-together blocks retain their bounded behavior. |
| Compare a source PDF against a generated template fixture using page geometry, metadata, text similarity and font/resource evidence | E4-01, E6-01, E6-04, E6-05 | Implemented as a repeatable ISDA comparison report; native-reader and second-engine approval remain open. |

## ISDA authoring and output requirement

The supplied [`2002-ISDA-Master-Agreement.pdf`](../2002-ISDA-Master-Agreement.pdf) is the acceptance target for a user-authored template, not an asset to be used as the template's locked output shortcut. A user must be able to construct the agreement through the platform's declarative text, rich-text, component, binding, table, condition, page-layout and document-structure features, then generate a PDF whose page geometry, typography, spacing, clauses, fields and legal-form composition are aligned with the supplied `ISDA*.pdf` source.

The current locked-source ISDA fixture is therefore a temporary visual baseline and must not be treated as completion of this requirement. It is useful for comparison and regression evidence only; the final workflow must keep the content editable and represented by meaningful structure nodes.

Required editor capability refinements include:

- Word-like text-box controls, including line spacing, paragraph spacing, indentation, tabs, alignment, keep-with-next/keep-together and page-break behavior, with the same bounded values applied to local preview and server PDF rendering.
- Rich text runs and reusable components that visibly expose their content and bindings in Document Structure, rather than generic or empty labels.
- Straightforward schema binding: users should insert a field from available schema properties, see its human-readable label and format, and preview representative data without authoring template expressions manually.
- A document-structure tree that represents the agreement's sections, clauses, tables, signature areas and bound fields as selectable editable objects.
- Repeatable comparison validation against the source PDF for page count, page geometry, extracted text, typography/font evidence, spacing and visual composition. Native-reader, accessibility and second-engine approval remain explicit gates.

Source stories: E2-01, E2-02, E2-05, E2-06, E2-10, E2-11, E2-15, E3-06, E4-01, E4-02, E4-04, E4-05, E5-01, E5-03, E5-04, E6-01, E6-04, E6-05.

## Execution boundary

This change executes the editor information architecture and top-level contextual action contract. It does not claim completion of folders, schema persistence/version migration, composite child editing, batch submission, API authentication, or WCAG certification. Those remain separately deliverable slices under the mapped source stories.

## Proposed sequence

1. Complete the editor shell and contextual selection contract.
2. Add application-owned folder records and template list filtering without changing template IDs.
3. Add schema draft/editor persistence and immutable schema versions.
4. Add the template-version-to-schema-version compatibility check and version history UI.
5. Implement the API and batch submission story only when explicitly taken from backlog.
