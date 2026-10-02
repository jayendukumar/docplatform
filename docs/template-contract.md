# Template block contract

## ISDA semantic authoring slice (E2/E4/E6)

ISDA objects retain the normal safe `text` or `table` block type and page ownership, with optional declarative metadata: `semantic_kind` (`clause`, `field`, `schedule`, or `signature`), a unique stable `semantic_id` within the definition, and for bound objects `field_path` plus human `field_role`. The editor uses these values for structure labels and exposes them on structure-tree buttons as non-rendering `data-semantic-id`, `data-semantic-kind` and `data-page-number` attributes; the renderer ignores the metadata and evaluates only the existing bounded field grammar. All pages have a semantic clause owner; pages 9–36 additionally use this contract for split agreement/Definitions clauses, measured Schedule elections, process agents, Offices, notices, payment netting, the documents table and signature fields. Source page 28 owns the separate `master_signatures` execution group; source page 36 owns Schedule other provisions and the `signatures` execution group. Every bound `field_path` is explicitly projected in the governed ISDA schema and exercised by non-empty local sample data; this is a schema-coverage invariant, not a legal completeness claim. Representative sample data must resolve every declared field in the local authoritative render; sample values are fixtures, not legal defaults. Selected measured fields may also use the existing bounded absolute-position contract in millimetres; those coordinates are provisional calibration data, not fidelity evidence. This is an incremental semantic decomposition, not a claim of exact source transcription, signature execution, source-box calibration or PDF fidelity.

The current server renderer accepts a bounded declarative block tree. Text blocks may include `font_family`, `font_size`, `bold`, `italic`, `color` (six-digit hex), `offset_x` (bounded horizontal nudge in pixels from -160 to 160), and `align` (`left`, `center`, or `right`). Unsupported style values are ignored rather than interpreted as CSS. The editor's contextual Move left/Move right actions adjust `offset_x` by 8 pixels per click; they do not reorder document blocks.

The ISDA authoring requirement extends this contract: text boxes must gain bounded `line_height`, `paragraph_spacing_before`, `paragraph_spacing_after`, `first_line_indent`, `left_indent`, `right_indent`, `tab_stops`, `keep_with_next`, and explicit page-break controls. These fields must be validated as data, rendered consistently by the local preview and server PDF path, and exposed through understandable text-box controls; adding them to this requirement does not claim they are implemented yet.

The editor exposes those same safe style fields for each text block. The local page preview applies them immediately, and saving a draft sends the values through the isolated server renderer; the saved artifact is the authoritative output preview. Text rows can be reordered with their drag handles, and the page surface accepts a dropped row as the final block position. This is the bounded E2-01 editor contract; it does not establish PDF/Word pagination, embedded-font coverage, or native-reader fidelity.

Since DD-441 an absolutely positioned text block spans from its left position to the content area's right edge (`right:0`), like a text box, so centred and right-aligned text aligns within that width. Text and rich-text blocks may additionally use `position_mode: "absolute"` with bounded `position_x` and `position_y` content-origin coordinates. `position_unit` may be `mm` for page-aware placement or `px` for legacy compatibility; `flow` remains the default. Absolute positioning is intentionally limited to the page content area and does not yet provide collision detection, resize handles or a complete form-field geometry model.

Editable text and rich-text blocks may set `page_number` from 1 through 1,000. The renderer emits a page break when the requested page advances beyond the previous block's page, allowing a multi-page agreement to be composed from page-owned components. The local canvas provides a bounded previous/next/page selector and hides foreground objects assigned to other pages; the locked source-PDF reference remains a visual comparison aid rather than editable content. Omitted blank pages, drag handles and collision detection remain open.

## Font size, justification and tab stops (DD-424 to DD-426)

- `font_size` on text blocks accepts 8-96 CSS px with up to two decimals (13.28 px is 9.96 pt), the same precision as rich-text runs. Larger precision is rounded.
- `align` on text blocks and rich-text paragraphs accepts `left`, `center`, `right` and `justify`. Justified paragraphs keep the last line left-aligned.
- `tab_stops` holds up to 16 stops. Each stop is a number (a left stop) or `{"position": px, "align": "left"|"right", "leader": "none"|"dot"|"underscore"|"hyphen"}`. Positions are 0-2000 px from the paragraph's left indent; 0 is the left indent itself, which is the implicit stop of a hanging indent.
- Each tab in the text moves to the next stop beyond the current boundary:
  - A left stop places the following text at the stop.
  - A right stop ends the following text at the stop.
  - A leader fills the gap with a dotted, solid or dashed rule drawn at the baseline. Leaders are not characters, so they add nothing to the text layer.
- Text after the last tab wraps normally with the paragraph's indents. Tabs beyond the last stop stay literal.
- Rich-text paragraphs use the paragraph's or block's stops; run styles carry across tab segments.
- The editor's tab-stop field takes a compact syntax, e.g. `48, 500r.`: a number is a position, `r` means right-aligned, and `.`, `_` or `-` choose the leader.
- The editor canvas approximates stops with the first stop's width. The server preview and PDF are authoritative.

## Direction and mixed-script boundaries (E4-04/E4-05)

Rendered HTML sets the document `dir` from RTL locale families (`ar`, `fa`, `he`, `ur`) and marks paragraphs, table headers/cells, headers, and footers with `dir="auto"` plus bounded plaintext bidi styling. This preserves mixed-script text, numbers, and punctuation as explicit candidate-render input. It is not evidence of correct shaping, line breaking, PDF pagination, or native-reader bidi approval.

## Locale formatting (E4-09)

The offline formatter has an explicit, reviewable profile for the shipped preview locales: `en`, `en-GB`, `de`, `fr`, `hi`, `ar`, `th`, `zh`, `ja`, and `ko`, including grouping separators and currency symbols. Regional tags resolve to their language profile unless a regional profile is explicitly defined. Arabic output uses Arabic-Indic digits, Arabic decimal/group separators, and the Arabic percent sign; this is a bounded project profile, not a complete CLDR implementation. It does not claim every locale's numbering, calendar, numeral-system, accounting, or timezone behavior.

## Expression safety (E5-06)

Template expressions are data paths and a fixed formatter whitelist only. Attribute access, calls, imports, operators, filesystem names, and arbitrary Python/JavaScript are rejected before evaluation. Loops, nesting, and expanded blocks have explicit limits. Rendered data is HTML-escaped, and the renderer does not fetch network resources; external image URLs are rejected by default. These are evaluator and candidate-renderer contract guarantees, not a substitute for the separate isolated-worker and hostile-parser checks required by E11-04.

## Images and logos

An `image` block accepts a bounded `src`, `alt`, pixel `width`/`height`, and `align` value (`left`, `center`, or `right`). The offline renderer places the requested-width image inside a full-width figure with the corresponding `text-align` value, so the server preview and generated PDF use the same positioning primitive as centered text. The offline renderer accepts base64 PNG, JPEG, GIF, WebP, and sanitized SVG data URIs, uploaded `/api/assets/...` references, and can resolve a source from a `{{field.path}}` value. SVG markup is bounded and rejects scripts, event handlers, foreign objects, entity declarations, CSS `url(...)`, and external references. HTTP(S) sources are rendered only when the definition explicitly sets `allow_external_sources: true` and the host is present in the configured `image_allowed_hosts` list; the renderer never fetches them. `POST /api/assets?filename=...` stores signature-checked image bytes in the configured object store, applies the optional upload scanner, and returns a stable asset URL; the browser image block exposes this upload path and the saved server preview renders the returned asset reference. Before designer PDF rendering, stored local asset references are read by the API supervisor and converted to bounded data URIs in the worker input, so the network-disabled PDF engine can embed them. This closes the bounded E2-03 asset-to-PDF regression; broad image scanning and native-reader output evidence remain separate gates.

## Charts (E2-14)

A `chart` block accepts `chart_type` (`bar`, `line`, or `pie`), `items`, `label_path`, and `value_path`. The default `data_mode` is `bound`: `items` is a bounded dot path to an array supplied with the render request, so the same template can render different data. `data_mode: static` may be used for a self-contained template with bounded `static_data` rows (maximum 100); the editor's sample rows are not silently treated as live input. An optional `series_path` groups rows into multiple series. Optional bounded authoring properties are `chart_title`, `chart_orientation` (`vertical` or `horizontal`, for bars), `show_grid`, `show_points` (for lines), `donut` (for pies), `show_legend`, `show_values`, `stacked` (for bars), `x_axis_label`, `y_axis_label`, `colors` (validated `#RRGGBB` palette), `background_color`, `grid_color`, and `axis_color`. Missing arrays/fields are reported through the normal render diagnostics and invalid numeric rows are skipped; arbitrary expressions, SVG, scripts, network resources, and chart-library configuration are not accepted. The editor exposes data-source, series, colour, and type-specific controls, while the saved server artifact remains the authoritative preview. The generated SVG is accompanied by a visually-hidden bounded data table for semantic fallback; this is an accessibility aid, not certification.

## Rich text blocks (E2-01, E5-01, E5-03, E5-04)

A `rich_text` block contains up to 100 paragraphs, each with up to 200 typed runs. A run is `text`, `binding`, or `condition`. Text and binding runs support bounded style properties (`font_family`, `font_size`, `color`, `bold`, `italic`, `underline`). Binding runs resolve a schema-compatible dot path and support `text`, `number`, `currency`, `date`, and `percent`; currency can specify a three-letter code such as `CNY`. Conditions use the existing bounded comparison operators (`equals`, `not_equals`, `truthy`, `greater_than`, `greater_or_equal`, `less_than`, `less_or_equal`) and contain explicit `then`/`else` runs. Conditions are data structures, not executable expressions. The renderer escapes literal and resolved values, applies the normal missing-field policy, limits nesting to four levels, and emits semantic paragraph markup for the same server-authoritative preview used by PDF generation. The editor exposes paragraph/run selection, styling, field insertion and a condition builder; arbitrary HTML, CSS, JavaScript and network references are not accepted.

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

`items` is a bounded dot path to an array. Each column requires a display `header` and a relative row `path`; supported formats are `text`, `number`, `currency`, `date`, and `percent`. An optional `width` is a percentage from 5 to 100 and is emitted as a bounded column width in local/server output. The renderer escapes headers and values, limits tables to 50 columns and 1,000 rows, and applies the configured missing-value policy.

Tables may also set `row_condition: {"path": "status", "equals": "active"}` to include only rows whose bounded relative field equals the declared scalar value. This is a data-only filter; templates cannot execute expressions or code.

The HTML candidate renderer emits a semantic `<table>` with `<thead>` and `<tbody>`, `display: table-header-group` for printed header repetition, and `break-inside: avoid` for rows. This closes the bounded E2-02 row/header contract; it does not prove final PDF pagination or native-reader acceptance.

The editor's **Add repeatable table** action inserts a sample `rows` array and exposes the data path and column JSON for editing. Saving creates a draft template version and renders the draft through the isolated server renderer.

### Static rows, typography and rules (DD-431)

Tables accept `data_mode: "static"` with `static_rows`:
- Up to 1000 rows, each an array of cell strings (at most one per column, up to 500 characters each).
- `{{path}}` interpolation is allowed inside cells.
- In static mode, columns need only a `header`.

Further table properties:
- **Columns:** each column may set `align` (`left`/`center`/`right`).
- **Header:** `show_header`, `header_bold` and `header_background` (#RRGGBB).
- **Typography:** `font_family` and `font_size` (8-96 px, two decimals).
- **Borders:** `borders` (`grid`/`horizontal`/`none`), `border_color` and `border_width` (0-4 px).
- **Spacing:** `cell_padding_x` and `cell_padding_y` (0-48 px), `row_height` (1-400 px), and `paragraph_spacing_before` and `paragraph_spacing_after` (0-240 px).

`header_row_height` (1-400 px) gives the header row its own height. `header_spacing_after` (0-240 px) leaves unshaded, borderless space between the header row and the first body row; it is part of the repeated header (DD-445). `row_styles` (at most 50 entries) styles individual body rows: each entry is `{row, bold?, italic?, background?, color?}`, where `row` is a 0-based body-row index and a negative index counts from the end (-1 is the last row, e.g. a totals row). The styles apply to every cell in the row and never to the header; invalid entries and rows outside the table are ignored, and a later entry for the same row overrides an earlier one per property (DD-447). Row heights are border-box: they include the cell's borders and padding (DD-441). Cell styles are emitted only for properties a template sets, so tables without them keep the stylesheet defaults and their HTML unchanged. The editor exposes these properties in the table-columns panel: rows source, fixed rows (one per line, cells separated by `|`), header, font, borders, padding, row height, spacing, per-column alignment and row styles.

## Shapes (DD-433)

A `shape` block draws a decorative `line` (`orientation` `horizontal`/`vertical`) or a `rectangle`:
- **Size:** `width_mm` and `height_mm` (0.1-500).
- **Stroke:** `stroke_color`, `stroke_width` (0-10 px) and `stroke_style` (`solid`/`dashed`/`dotted`).
- **Fill:** `fill_color`, rectangles only.
- **Layer:** `layer` (`front`/`behind`).
- **Placement:** `position_mode: "absolute"` with `position_x`/`position_y` in mm from the page content area (`position_unit` is `mm`). Otherwise the shape sits in the flow with `paragraph_spacing_before`/`paragraph_spacing_after`.

Behind-layer shapes paint under text because each page-owned surface is a stacking context. Shapes carry no text and are `aria-hidden`. Shapes in page-margin areas are clipped by page-owned surfaces. The editor inserts shapes with "Add line or rectangle" and edits them in the Shape panel.

## Header and footer zones, distances and rules (DD-437)

Page properties `header_left`, `header_center`, `header_right` and `footer_left`, `footer_center`, `footer_right` (up to 500 characters, `{{path}}` interpolation) place text in each zone of the band. The legacy `header`/`footer` text still goes to its `*_align` zone, and a zone-specific text takes precedence in the same zone. A page number sharing a zone follows the zone text.

`header_distance_mm` and `footer_distance_mm` (0-100) pin text to a distance from the page's top or bottom edge. Without them, text is vertically centred in the margin.

`header_rule` and `footer_rule` draw a full-width rule:
- `header_rule_offset_mm` sets the gap above the content area, and `footer_rule_offset_mm` the gap below it.
- `furniture_rule_color` and `furniture_rule_width` (0-4 px) style both rules.
- The rule is the border of all three margin boxes in the band.

All zones share `header_footer_font_size` unless `zone_styles` overrides it. `zone_styles` is keyed by zone name (`header_left` ... `footer_right`); each entry may set `font_size` (6-48 px), `bold` and `italic`. A page number in a zone takes that zone's style. Invalid zones and values are ignored. The editor edits zones, distances, rules and per-zone size, bold and italic in the "Header and footer zones" group of Page settings.

## Column sections (DD-435)

A `columns` block opens a column section with these properties:
- `count` (1-4) and `gap_mm` (0-50).
- `widths`: one percentage of the content width per column. Widths plus the gap should total at most 100%.
- `rule_color` and `rule_width` (0-4 px) for a rule between columns.
- `paragraph_spacing_before`/`paragraph_spacing_after`.

Blocks that follow belong to the section until a `columns_end` block. A `column_break` block starts the next column. When breaks are used the columns are explicit (a grid). Without breaks the content flows and balances across the columns.

An open section closes at the end of its page group or at the next `columns` block, and stray markers outside a section are ignored. Sections are flat markers rather than nested containers, so the block list, components and bindings stay flat.

The editor inserts "Start columns", "Column break" and "End columns" from the insert panels, shows them as markers on the canvas, and edits a section in the Columns panel.

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
    "margin_top_mm": 20,
    "margin_right_mm": 20,
    "margin_bottom_mm": 20,
    "margin_left_mm": 20,
    "header": "{{title}}",
    "footer": "Confidential",
    "show_page_numbers": true
  }
}
```

Supported sizes are `A3`, `A4`, `A5`, and `Letter`; margins are 0–100 mm. Header and footer values are escaped after bounded interpolation, and page numbers use the candidate renderer's CSS page counter. The server emits `@page`, fixed header/footer elements, and the selected orientation/margins. This is an HTML candidate contract; final PDF page-flow fidelity remains pending E4/E6 engine evidence.

Since DD-429 the printed header, footer and page numbers are `@page` margin boxes, not fixed-position elements or a PDF overlay:
- `header_align` and `footer_align` (`left`/`center`/`right`, default `left`) choose the margin box for each band.
- `page_number_position` (`header-` or `footer-` plus `left`/`center`/`right`, default `footer-right`) and `page_number_format` (up to 40 characters with `{page}` and `{pages}`, default `{page}`) place and format the live page counter.
- `header_footer_font_size` (6-48 px, default 12) sets the size. The font is the theme font, or the document's script stack.
- Text and number in the same box are joined with a space. All text is hex-escaped as CSS strings.
- The HTML header and footer elements remain for screen preview only, showing page 1, and are hidden in print.

Definitions may also include bounded `metadata.title` and `metadata.author` strings. The candidate emits escaped HTML `<title>`, author metadata, and the request locale as the document language; render results expose the same values. This is metadata input evidence for a future PDF engine, not proof that a final PDF contains or preserves the fields.

The legacy `margin_mm` value remains accepted and supplies all four sides when side-specific values are absent. `header_component_id` and `footer_component_id` may reference text-only reusable components; component references are expanded at render time while existing plain header/footer strings remain supported.

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
