# Extraction review contract

`POST /api/ingestions/{id}/extract` persists a local extraction result and returns the source PageModel used for that result. `GET /api/extractions/{id}` returns its revision, status, fields, provenance, and correction history.

The browser review slice renders the returned PageModel as a coordinate-aware source preview. Selecting a field highlights its stored page/box provenance. Reviewers can navigate returned pages, drag a bounded rectangle over the active page, and add a missing field with that page/box source; the box is persisted in the revisioned extraction result and can be reversed through the correction undo route. Image uploads are shown beside that overlay through the authenticated source endpoint, and PDF uploads are shown in a same-origin native PDF frame above the coordinate overlay. PDF rasterization, exact pixel-to-box calibration, and rotation-aware calibration remain incomplete.

`GET /api/ingestions/{document_id}/source` reads the original upload through the configured object store and returns it inline with its recorded media type. The route requires the read authorization boundary. Image-backed review results display this source beside the coordinate overlay; PDF rasterization, multi-page navigation and rotation-aware calibration remain pending.

`GET /api/extractions/{result_id}` now includes `review_events`, an append-only list of `{from_status, to_status, actor, created_at}` entries. Explicit review actions and correction-driven transitions into `in_review` are recorded separately from value-level `corrections`; pre-migration records have no historical state events.

The review UI also exposes a keyboard queue ordered by failed validation rules, then low-confidence fields, then the remaining fields. Focusing a scalar review value or queue input selects its stored page/element overlay when provenance exists; displayed local line-item cells provide the same source-selection action. Each queue input saves on blur; Enter, ArrowDown and ArrowUp move focus without requiring a mouse. This is a keyboard workflow slice, not an accessibility certification; OCR table coverage, table-cell editing and PDF pixel scrolling remain incomplete.

Corrections use:

```json
PATCH /api/extractions/{result_id}/fields/total
{"expected_revision": 1, "value": "125.00", "actor": "local-reviewer"}
```

The expected revision prevents lost updates. A correction records the previous and new values, actor label, and timestamp, then moves the result to `in_review`. Review state can be changed to `new`, `in_review`, `approved`, or `rejected`; every transition is append-only in `review_events` with its prior state, new state, actor, and timestamp. Corrections are exportable through `/api/extractions/{result_id}/corrections.csv`. The browser workflow is a local review slice; authentication and role enforcement are documented separately, and native page-image overlays remain incomplete.

`POST /api/extractions/{result_id}/fields` adds a manually identified field. It requires `field` (or `field_name`) and `expected_revision`, and may include `value`, `absent`, and a provenance `source` object containing page/element/box data. `PATCH /api/extractions/{result_id}/fields/{field_name}` accepts `absent: true` and an optional replacement `source` for an explicitly corrected value. Both operations advance the revision and set the result to `in_review`. `POST /api/extractions/{result_id}/undo` reverses the latest correction using the persisted before-field snapshot, including source, absent flag, validation and review metadata; legacy correction rows without a snapshot retain the value-only fallback. Correction rows are retained rather than deleted.

Only approved results can be supplied to `POST /api/templates/{template_id}/render-approved`. Unapproved, rejected, or missing results are rejected by the API. The endpoint maps each extraction field name to the same top-level template data name and returns both the rendered artifact and the bound `data` object. The browser's **Send to template** action opens that template in the editor, replaces its sample data with the approved normalized values, and shows the returned server preview. The first listed template is the current one-click destination; template selection remains a follow-up UX improvement.
