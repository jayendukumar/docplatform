# E18 — Categorized template gallery and workspace organization (proposed scope addition)

Status: Proposed scope addition, first implementation slice accepted on 2026-10-07.

This epic extends the original 15-epic backlog. `docs/epics.md` remains generated from the supplied DOCX and is not rewritten. It complements E3 template management and E2 editor work.

## Outcome

The homepage helps users start quickly from industry-relevant document templates while keeping their own work organized. A user can browse category rows, reveal more templates within a category, create a blank canvas, and save it into a folder path in the workspace.

## Stories and acceptance criteria

| ID | Story | Acceptance |
| --- | --- | --- |
| E18-01 | Owner: browse template categories on the homepage | The gallery groups templates by category, displays four cards per category row on desktop, and remains responsive on smaller screens. |
| E18-02 | Owner: see more templates in a category | A category with more than four templates has a More templates action; activating it reveals the remaining templates without navigating away. |
| E18-03 | Owner: start a blank template | The homepage provides a name and folder form that creates a draft with an empty block list and opens it in the editor. |
| E18-04 | Owner: organize workspace templates into folders | Foldered templates are displayed under their logical folder on the homepage; existing templates without a folder remain in Workspace. |
| E18-05 | Product: provide broad industry coverage | The offline starter catalog includes at least two or three usable templates for investment banking, asset management, insurance, wealth management, finance operations, scheduling/calendars, HR, legal/compliance, sales/marketing, and general communications. |

## First implementation choices

- The catalog is local and deterministic. It does not call a marketplace, AI service, or external template repository.
- Categories are starter metadata, while folders belong to user-created workspace templates. They are intentionally separate concepts.
- Four cards are the desktop default so each row stays scannable. “More templates” reveals the rest of that category in place.
- Blank templates use the existing versioned template API and folder field; no new persistence model is needed for the first slice.

## Follow-up scope

Drag-and-drop folders, folder rename/delete, per-user folder authorization, category administration, pagination for very large catalogs, marketplace sharing, and localized catalog content remain follow-up work.
