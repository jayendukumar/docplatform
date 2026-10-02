# API reference

The authoritative API description is generated from the FastAPI application:

- Interactive explorer: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

The generated specification covers the current template, ingestion, extraction/review, authentication, API-key, rendering and job routes. Use the explorer against a local instance to inspect request schemas and try calls. The normal Compose deployment binds to loopback; configure a TLS reverse proxy before exposing it beyond the local host.

## Small render flow

1. `GET /api/templates` to find a template ID.
2. `POST /api/templates/{template_id}/render` with a JSON body such as `{"data": {"name": "Ada"}}` for a synchronous candidate render.

`POST /api/templates/{template_id}/sample-data` returns deterministic preview data inferred from the template's `data_schema` or bounded field/table/condition bindings. Pass `locale` and `draft` to select the preview locale/version. This is preview data only; it is not persisted or treated as approved business data.
3. For a durable job, `POST /api/jobs` with `{"kind":"render","template_id":"...","data":{"name":"Ada"}}`, then poll `GET /api/jobs/{job_id}` and run it through the configured worker trigger.

The current synchronous designer render is deterministic HTML. `POST /api/templates/{template_id}/render-pdf` sends that HTML to the packaged pinned Chromium adapter by default, or to an explicitly configured Prince/renderer adapter, inside the credential-free document worker and returns a candidate PDF with metadata. It returns 503 when the selected renderer is unavailable. Python-based configured engines receive a generated network-denial `sitecustomize` guard; arbitrary native executables still require deployment-level network policy. `POST /api/word/merge` accepts a bounded base64 DOCX template plus JSON data and returns a merged base64 DOCX for the supported scalar/table contract. `POST /api/word/convert` accepts that DOCX and invokes the explicitly configured shell-free converter. PDF layout fidelity, native-reader approval and output-format acceptance remain separate stories and are not implied by the OpenAPI explorer.

`GET /api/editor/capabilities` returns the versioned editor capability manifest (`editor-capabilities-v1`, E16-05). It lists every component and page property the renderer applies, its bounds and units, whether the editor exposes it (`control`, `json` or `none`), and known component limitations. The E16 fidelity harness reads it to confine reconstructions to editor-reachable properties. It describes capabilities and grants none.

`GET /api/starters` returns the launchable multilingual starter catalog. Each item includes its available language codes and the bounded definition used by the workspace gallery; clients can create a draft with `POST /api/templates` using the selected definition.

## Scan submission and extraction flow

1. `POST /api/ingestions?filename=...` with a PDF, PNG, JPEG, or TIFF body to receive the ingestion ID, route, page count, and initial status.
2. Poll `GET /api/ingestions/{document_id}` for routing/status metadata, or `GET /api/ingestions/{document_id}/result` for the versioned PageModel and Markdown derivative.
3. `POST /api/ingestions/{document_id}/extract` with `{"schema_id":"invoice"}` or an inline schema to receive and persist an extraction result.
4. Poll/read `GET /api/extractions/{result_id}` for fields, confidence, provenance, revision, validation, and review state.

This documents the local API contract for scan submission and result retrieval. Scanned-page OCR can use the optional `ocr_command` adapter, whose JSON output is validated for page numbers, text boxes and confidence values; without that deliberately configured local command, scan OCR remains unavailable. PaddleOCR model execution and accuracy evidence remain separate incomplete story gates.

## Browser action coverage

The current workspace actions have REST equivalents in the generated specification:

| UI action | API contract |
| --- | --- |
| List/open templates | `GET /api/templates`, `GET /api/templates/{template_id}` |
| Launch a multilingual starter | `GET /api/starters`, `POST /api/templates` |
| Save an editor draft | `POST /api/templates/{template_id}/versions` |
| Render a draft preview | `POST /api/templates/{template_id}/render` |
| Render a designer template as PDF | `POST /api/templates/{template_id}/render-pdf` (configured renderer adapter; Chromium default, Prince opt-in) |
| Upload an editor asset | `POST /api/assets` |
| Upload and poll an ingestion | `POST /api/ingestions`, `GET /api/ingestions/{document_id}`, `GET /api/ingestions/{document_id}/result` |
| Select, inspect, and validate an extraction schema | `GET /api/extraction-schemas`, `GET /api/extraction-schemas/{schema_id}`, `POST /api/extraction-schemas/validate` |
| Extract and poll schema data | `POST /api/ingestions/{document_id}/extract`, `GET /api/jobs/{job_id}`, `GET /api/extractions/{result_id}` |
| Correct/review extracted fields | `PATCH /api/extractions/{result_id}/fields/{field_name}`, `POST /api/extractions/{result_id}/fields`, `POST /api/extractions/{result_id}/undo`, `POST /api/extractions/{result_id}/review` |
| Export or explicitly deliver extraction data | `GET /api/extractions/{result_id}/export.json`, `GET /api/extractions/{result_id}/export.csv`, `GET /api/extractions/{result_id}/export.xlsx`, `POST /api/extractions/{result_id}/webhook` |
| Generate from approved data | `POST /api/templates/{template_id}/render-approved` |

The route-presence test checks this matrix against generated OpenAPI. It does not mean every other story is complete: PDF output, webhook delivery behavior, SDKs, and final format fidelity remain separate.

The template editor's **Generate PDF** action saves the current draft, calls the PDF route with the selected preview locale and sample data, and displays the returned Base64 PDF in the browser. The action also provides a direct download link. The browser flow does not change the API's candidate status or its renderer/native-reader limitations.

## Verification

`backend/tests/test_epic34.py` checks that `/docs` and `/openapi.json` are reachable and that the explicit browser-action matrix remains present in generated OpenAPI. This closes the current E7-01 REST-equivalence and E7-03 explorer/spec-drift criteria; it is not a complete endpoint behavior or client compatibility suite.
