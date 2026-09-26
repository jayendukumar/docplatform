# Template block contract

The current server renderer accepts a bounded declarative block tree. Text blocks may include `font_family`, `font_size`, `bold`, `italic`, `color` (six-digit hex), and `align` (`left`, `center`, or `right`). Unsupported style values are ignored rather than interpreted as CSS.

The editor exposes those same safe style fields for each text block. The local page preview applies them immediately, and saving a draft sends the values through the isolated server renderer; the saved artifact is the authoritative output preview. Text rows can be reordered with their drag handles, and the page surface accepts a dropped row as the final block position. This is the bounded E2-01 editor contract; it does not establish PDF/Word pagination, embedded-font coverage, or native-reader fidelity.

## Direction and mixed-script boundaries (E4-04/E4-05)

Rendered HTML sets the document `dir` from RTL locale families (`ar`, `fa`, `he`, `ur`) and marks paragraphs, table headers/cells, headers, and footers with `dir="auto"` plus bounded plaintext bidi styling. This preserves mixed-script text, numbers, and punctuation as explicit candidate-render input. It is not evidence of correct shaping, line breaking, PDF pagination, or native-reader bidi approval.

## Locale formatting (E4-09)

The offline formatter has an explicit, reviewable profile for the shipped preview locales: `en`, `en-GB`, `de`, `fr`, `hi`, `ar`, `th`, `zh`, `ja`, and `ko`, including grouping separators and currency symbols. Regional tags resolve to their language profile unless a regional profile is explicitly defined. Arabic output uses Arabic-Indic digits, Arabic decimal/group separators, and the Arabic percent sign; this is a bounded project profile, not a complete CLDR implementation. It does not claim every locale's numbering, calendar, numeral-system, accounting, or timezone behavior.

## Expression safety (E5-06)

Template expressions are data paths and a fixed formatter whitelist only. Attribute access, calls, imports, operators, filesystem names, and arbitrary Python/JavaScript are rejected before evaluation. Loops, nesting, and expanded blocks have explicit limits. Rendered data is HTML-escaped, and the renderer does not fetch network resources; external image URLs are rejected by default. These are evaluator and candidate-renderer contract guarantees, not a substitute for the separate isolated-worker and hostile-parser checks required by E11-04.

## Images and logos

An `image` block accepts a bounded `src`, `alt`, pixel `width`/`height`, and `align` value (`left`, `center`, or `right`). The offline renderer places the requested-width image inside a full-width figure with the corresponding `text-align` value, so the server preview and generated PDF use the same positioning primitive as centered text. The offline renderer accepts base64 PNG, JPEG, GIF, WebP, and sanitized SVG data URIs, uploaded `/api/assets/...` references, and can resolve a source from a `{{field.path}}` value. SVG markup is bounded and rejects scripts, event handlers, foreign objects, entity declarations, CSS `url(...)`, and external references. HTTP(S) sources are rendered only when the definition explicitly sets `allow_external_sources: true` and the host is present in the configured `image_allowed_hosts` list; the renderer never fetches them. `POST /api/assets?filename=...` stores signature-checked image bytes in the configured object store, applies the optional upload scanner, and returns a stable asset URL; the browser image block exposes this upload path and the saved server preview renders the returned asset reference. Before designer PDF rendering, stored local asset references are read by the API supervisor and converted to bounded data URIs in the worker input, so the network-disabled PDF engine can embed them. This closes the bounded E2-03 asset-to-PDF regression; broad image scanning and native-reader output evidence remain separate gates.

## QR and barcodes

A `code` block accepts `code_type` (`qr`, `code128`, or `ean13`), a fixed value or `{{field.path}}`, and a bounded width. The server generates SVG locally using the pinned offline libraries; EAN-13 values are validated as 12 digits (with the check digit generated) or 13 digits (with the supplied check digit verified), and all code values are bounded to 1–200 characters. The editor exposes all three choices and the browser contract verifies each value reaches the server preview. This proves SVG generation and editor/preview mapping, not scanner acceptance in every final PDF engine or reader.

## Font diagnostics

Each candidate render result includes `font_report` entries for detected script families. An entry records the requested fallback stack, embedded font list, missing-glyph list, and diagnostic status. The current deterministic HTML candidate reports requested stacks but embeds no fonts and therefore remains a diagnostic contract; it is not E4-02/E6-05 completion evidence.

The editor's server-preview panel exposes the same `engine`, `status`, detected scripts, requested stacks, and per-script `font_report` without rewriting the values. An empty `embedded_fonts` or `missing_glyphs` list is reported literally; it is not interpreted as proof of font coverage. A `warning` status with `U+....` entries is a deterministic unsupported-character diagnostic for characters outside the bounded script map (currently unassigned characters and emoji/symbols); it is not a claim that a specific installed font lacks a glyph. Actual cmap coverage, embedding, and native-reader review remain open rendering gates.

## Repeatable tables (E2-02)

A table block repeats its body rows from a JSON array:

```json
{
  "type": "table",
  "items": "lines",
  "columns": [
    {"header": "Description", "path": "description", "format": "text"},
    {"header": "Amount", "path": "amount", "format": "currency"}
  ]
}
```

`items` is a bounded dot path to an array. Each column requires a display `header` and a relative row `path`; supported formats are `text`, `number`, `currency`, `date`, and `percent`. The renderer escapes headers and values, limits tables to 50 columns and 1,000 rows, and applies the configured missing-value policy.

The HTML candidate renderer emits a semantic `<table>` with `<thead>` and `<tbody>`, `display: table-header-group` for printed header repetition, and `break-inside: avoid` for rows. This closes the bounded E2-02 row/header contract; it does not prove final PDF pagination or native-reader acceptance.

The editor's **Add repeatable table** action inserts a sample `rows` array and exposes the data path and column JSON for editing. Saving creates a draft template version and renders the draft through the isolated server renderer.

## Multilingual starters (E3-05)

`GET /api/starters` returns the four bundled starter families (`letter`, `invoice`, `certificate`, and `receipt`). Each entry includes at least three language definitions with bounded blocks, sample data, a locale, and a translation map. The workspace gallery launches a selected language by creating an ordinary draft through `POST /api/templates`; the starter catalog does not bypass template versioning. These definitions are deterministic contract fixtures and do not claim native-reader or final PDF acceptance.

## Repeating and conditional sections (E2-05)

The editor also creates the existing bounded logic nodes. This closes the bounded E2-05 visual-editor contract: adding, configuring, saving, and server-previewing these nodes is covered by the editor and evaluator tests. Nested composition, final pagination, and complete accessibility conformance remain separate.

Reusable components are stored in the `reusable_components` registry. A template references one with `{ "type": "component", "component_id": "..." }`; the editor preserves that reference while the isolated render path expands the current component definition. Updating a component therefore affects every referencing template on its next render. Component expansion rejects missing references and cycles, and component definitions remain bounded template blocks rather than executable code. The editor currently exposes create/add actions and the API supports version increments; a full component management screen and cross-template browser evidence remain open under E2-11.

```json
{"type":"loop","items":"rows","as":"row","blocks":[{"type":"text","text":"{{row.description}}"}]}
```

```json
{"type":"if","condition":{"path":"show_note","equals":true},"then":[{"type":"text","text":"Shown"}],"else":[{"type":"text","text":"Hidden"}]}
```

Loop sources must be arrays and are capped at 1,000 items. Conditions use the allow-listed comparison/boolean operators in the template evaluator; they cannot execute code or access networks. The editor seeds `rows` and `show_note` in its sample data so both branches can be previewed by changing the configured condition value. This verifies editor-to-render semantics, not pagination or complete accessibility conformance.

## Page settings (E2-06)

The bounded E2-06 editor/server-preview contract is implemented: draft settings are persisted and emitted as inspectable HTML page rules and document chrome. Final PDF page-flow fidelity remains a separate E4/E6 gate.

Definitions may include bounded page settings:

```json
{
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "margin_mm": 20,
    "header": "{{title}}",
    "footer": "Confidential",
    "show_page_numbers": true
  }
}
```

Supported sizes are `A3`, `A4`, `A5`, and `Letter`; margins are 0–100 mm. Header and footer values are escaped after bounded interpolation, and page numbers use the candidate renderer's CSS page counter. The server emits `@page`, fixed header/footer elements, and the selected orientation/margins. This is an HTML candidate contract; final PDF page-flow fidelity remains pending E4/E6 engine evidence.

Definitions may also include bounded `metadata.title` and `metadata.author` strings. The candidate emits escaped HTML `<title>`, author metadata, and the request locale as the document language; render results expose the same values. This is metadata input evidence for a future PDF engine, not proof that a final PDF contains or preserves the fields.

## Table of contents (E2-16)

TOC blocks link only to declared, validated anchor IDs. The Chromium PDF adapter preserves those named destinations. Because Chromium does not emit CSS `target-counter()` values, the PDF route performs a bounded post-render pass: it maps transparent, `aria-hidden` anchor markers to physical pages and overlays the resolved page number beside each matching TOC link. The output-level regression forces an anchor onto page 2 and verifies both the `2` page reference and the surviving `/intro` link annotation. Native-reader and accessibility review of the candidate overlay remain pending.

## Locale preview (E2-08)

The editor preview selector sends an explicit locale on the draft render request. The current offline choices are `en`, `en-GB`, `de-DE`, `ar`, `hi`, `th`, `zh-CN`, and `ja-JP`; the server returns that locale in the HTML `lang` attribute and applies the existing locale-aware date/number/currency functions. This is a preview contract, not evidence that every script has passed native-reader, shaping, font, or final-output review.

The editor stores multilingual text through native browser text controls and the server preserves it as escaped UTF-8 HTML. Direct-entry coverage currently exercises Arabic, Devanagari, Thai, Chinese, and Japanese in the browser; IME composition, caret movement, selection, and native-reader shaping remain unverified.

The bounded formatter profiles `en`/US-style, `en-GB`, `de`, `fr`, `hi`, `ar`, `th`, `zh`, `ja`, and `ko` families for deterministic number grouping, currency placement and date shape. Hindi uses Indian digit grouping; German/French use decimal comma; Arabic uses Arabic-Indic digits; Japanese/Chinese use year-first dates. These are explicit offline profiles with regression fixtures, not complete CLDR coverage or a claim of native numeral shaping.

## Per-template translations (E4-10)

Definitions may include a bounded `translations` map keyed by locale (or base language) and text blocks may set `translation_key`. The renderer checks the exact locale, then its base language, then `default`; if no value exists it retains the block's source text and reports `missing_translations` entries such as `de-DE:invoice.title`. Page headers and footers can use `header_translation_key` and `footer_translation_key`. This is an offline translation-file contract and missing-key diagnostic, not proof of script shaping, fonts, native-reader fidelity, or final PDF output.

## Extraction exports

Approved or in-review extraction results can be downloaded as JSON, CSV, or a dependency-free OOXML workbook. Each tabular export preserves field name, original value, normalized value, confidence, review status, source page/box, validation findings, and result status. The workbook deliberately uses string cells to avoid coercing locale-shaped originals. Webhook delivery remains pending an explicit outbound destination allow-list and SSRF-resistant delivery contract.

## Page flow controls (E2-07)

Text and table blocks may set `break_before: true` to request a page break before the block and `keep_together: true` to apply `break-inside: avoid`. Text paragraphs also request `orphans: 3` and `widows: 3`; table rows use keep-together and table headers use `table-header-group`. These rules are deterministic HTML hints and require a selected PDF engine plus fixed visual fixtures before orphan/split acceptance can be claimed.
