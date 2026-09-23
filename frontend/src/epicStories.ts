export type EpicStory = { id: string; story: string; priority: 'Must' | 'Should' | 'Could'; size: 'S' | 'M' | 'L' | 'XL' }

// Generated from docs/epics.md. Keep the source backlog unchanged.
export const epicStories: Record<string, EpicStory[]> = {
  "E1": [
    {
      "id": "E1-01",
      "story": "Dev: start the whole platform with one docker compose up",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E1-02",
      "story": "Admin: configure everything through environment variables and one config file",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E1-03",
      "story": "Admin: store templates, uploads and outputs on local disk or S3-compatible storage",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E1-04",
      "story": "Admin: keep metadata in PostgreSQL with automatic migrations",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E1-05",
      "story": "Admin: see health and readiness endpoints for each service",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E1-06",
      "story": "Admin: run on CPU only, with a documented minimum hardware guide",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E1-07",
      "story": "Admin: upgrade between versions without data loss",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E1-08",
      "story": "Admin: deploy on Kubernetes with a Helm chart",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E1-09",
      "story": "Admin: install offline with fonts and models bundled",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E1-10",
      "story": "Admin: back up and restore data with one command",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E1-11",
      "story": "Admin: set retention periods for uploads and outputs",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E1-12",
      "story": "Contributor: run the stack locally without Docker",
      "priority": "Could",
      "size": "M"
    }
  ],
  "E2": [
    {
      "id": "E2-01",
      "story": "Owner: drag text blocks onto a page and format them (font, size, weight, colour, alignment)",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E2-02",
      "story": "Owner: add tables whose rows repeat from a data array",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E2-03",
      "story": "Owner: place images and logos, fixed or bound to a data field",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E2-04",
      "story": "Owner: add QR codes and barcodes bound to fields",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E2-05",
      "story": "Owner: add repeating sections and conditional blocks visually",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E2-06",
      "story": "Owner: set page size, orientation, margins, headers, footers and page numbers",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E2-07",
      "story": "Owner: control page flow with automatic breaks and keep-together rules",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E2-08",
      "story": "Owner: preview with sample data and switch preview language and locale",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E2-09",
      "story": "Loc: type and edit Arabic, Hebrew, Indic, Thai and CJK text directly on the canvas",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E2-10",
      "story": "Owner: undo and redo, copy and paste, snapping and alignment guides, keyboard shortcuts",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E2-11",
      "story": "Owner: reuse components such as header, footer and address block across templates",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E2-12",
      "story": "Owner: apply brand themes with colour, font and spacing tokens",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E2-13",
      "story": "Owner: use the editor with keyboard and screen reader",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E2-14",
      "story": "Owner: add charts (bar, line, pie) bound to data",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E2-15",
      "story": "Owner: use an existing PDF page as a locked background layer",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E2-16",
      "story": "Owner: add tables of contents and page cross-references",
      "priority": "Could",
      "size": "M"
    }
  ],
  "E3": [
    {
      "id": "E3-01",
      "story": "Owner: organize templates in folders and tags and search them by name, tag and content",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-02",
      "story": "Owner: keep drafts separate from published versions",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-03",
      "story": "Owner: see version history with a change summary and restore any version",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-04",
      "story": "Owner: duplicate a template with save-as",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E3-05",
      "story": "Owner: start from a gallery of starters (invoice, letter, certificate, receipt) in at least three languages",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-06",
      "story": "Dev: attach sample data and see the expected JSON schema derived from the template",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-07",
      "story": "Dev: export and import a template as a portable file",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E3-08",
      "story": "Dev: sync templates with a git repository as plain files",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E3-09",
      "story": "Owner: submit a template for review, and reviewers approve before publishing",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E3-10",
      "story": "Admin: promote templates across dev, staging and production environments",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E3-11",
      "story": "Owner: comment on templates and request changes",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E3-12",
      "story": "Admin: restrict template access per team or folder",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E3-13",
      "story": "Owner: see usage analytics per template (renders, errors, latency)",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E3-14",
      "story": "Owner: archive templates, with a warning when API keys still use them",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E3-15",
      "story": "Owner: move, tag and export many templates at once",
      "priority": "Could",
      "size": "S"
    }
  ],
  "E4": [
    {
      "id": "E4-01",
      "story": "Loc: run a rendering spike that compares candidate engines on Arabic, Hebrew, Hindi, Tamil, Thai, Chinese and Japanese",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-02",
      "story": "Loc: get a bundled Noto font set with script-specific fallback stacks",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-03",
      "story": "Loc: have complex-script shaping on by default for Arabic, Indic and Thai",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E4-04",
      "story": "Loc: render mixed right-to-left and left-to-right text, numbers and punctuation correctly",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E4-05",
      "story": "Loc: get correct line breaking for Chinese, Japanese, Korean and Thai",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-06",
      "story": "Owner: upload custom fonts, with subsetting and a reminder to check the font licence",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-07",
      "story": "Dev: get an automatic per-character font fallback with a warning when no font has the glyph",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-08",
      "story": "Loc: see a public script test matrix rebuilt in CI with visual regression",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E4-09",
      "story": "Loc: format dates, numbers and currencies by locale",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E4-10",
      "story": "Owner: render one template in many languages using per-template translation files",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E4-11",
      "story": "Loc: mirror layouts for right-to-left languages (alignment, column order, page numbers)",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E4-12",
      "story": "Loc: use language-specific hyphenation and justification",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E4-13",
      "story": "Loc: choose numeral systems such as Arabic-Indic and Devanagari digits",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E4-14",
      "story": "Loc: format non-Gregorian calendars (Hijri, Buddhist)",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E4-15",
      "story": "Dev: swap the rendering engine per template behind one interface",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E4-16",
      "story": "Dev: pin the engine version per template so output stays stable across upgrades",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E4-17",
      "story": "Dev: keep file sizes low through font subsetting and image compression",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E4-18",
      "story": "Loc: render vertical Japanese text and ruby annotations",
      "priority": "Could",
      "size": "L"
    }
  ],
  "E5": [
    {
      "id": "E5-01",
      "story": "Dev: bind fields to JSON with dot paths and array indexes",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-02",
      "story": "Owner: loop over arrays, including nested ones, with an empty-state message",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-03",
      "story": "Owner: show or hide blocks with conditions and if-else",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-04",
      "story": "Owner: format values with number, currency, date, percent and text functions",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-05",
      "story": "Dev: validate render requests against the template's JSON schema with clear errors",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-06",
      "story": "Admin: run template expressions in a sandbox with no code execution or network access",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-07",
      "story": "Owner: choose what happens when a field is missing (error, blank, placeholder)",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E5-08",
      "story": "Ops: use approved extraction results as a template's data source in one click",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E5-09",
      "story": "Owner: generate sample data automatically for previews",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E5-10",
      "story": "Owner: compute totals, counts and averages in tables",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E5-11",
      "story": "Owner: sort, filter and group arrays inside the template",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E5-12",
      "story": "Ops: generate one document per row from a CSV or Excel upload",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E5-13",
      "story": "Owner: compose templates from sub-templates",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E5-14",
      "story": "Dev: fetch data from an allow-listed REST endpoint at render time",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E5-15",
      "story": "Loc: apply currency rounding rules by locale",
      "priority": "Could",
      "size": "M"
    }
  ],
  "E6": [
    {
      "id": "E6-01",
      "story": "Dev: generate PDF from a designer template",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E6-02",
      "story": "Dev: upload a Word template with placeholders and loops and merge JSON into it",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E6-03",
      "story": "Dev: convert merged Word output to PDF",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E6-04",
      "story": "Dev: set PDF metadata (title, author, language)",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E6-05",
      "story": "Dev: get a report of fonts and glyph coverage with each render",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E6-06",
      "story": "Owner: get image thumbnails of the first page for previews",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E6-07",
      "story": "Dev: protect PDFs with passwords and permissions",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E6-08",
      "story": "Dev: bundle several documents into one PDF and add watermarks or stamps",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E6-09",
      "story": "Dev: generate Excel files with formats and formulas",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E6-10",
      "story": "Dev: generate PowerPoint files with slides repeated per record",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E6-11",
      "story": "Dev: generate email-safe HTML",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E6-12",
      "story": "Dev: render Markdown into a styled document",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E6-13",
      "story": "Admin: produce PDF/A archival files",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E6-14",
      "story": "Admin: produce tagged, accessible PDFs",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E6-15",
      "story": "Dev: leave signature fields or hand off to an e-signature service",
      "priority": "Could",
      "size": "L"
    }
  ],
  "E7": [
    {
      "id": "E7-01",
      "story": "Dev: manage templates and render documents through a REST API",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E7-02",
      "story": "Dev: authenticate with scoped API keys that can be rotated",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E7-03",
      "story": "Dev: read an OpenAPI spec and try calls in a built-in explorer",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E7-04",
      "story": "Dev: render small documents synchronously and larger ones as async jobs with status polling",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E7-05",
      "story": "Dev: submit scans and read extraction results through the API",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E7-06",
      "story": "Dev: receive signed webhooks when a job finishes or fails, with retries",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E7-07",
      "story": "Dev: use official SDKs for JavaScript or TypeScript and Python",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E7-08",
      "story": "Dev: push and pull templates and render locally with a CLI",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E7-09",
      "story": "Dev: embed the template editor in my own product",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E7-10",
      "story": "Dev: retry render requests safely with idempotency keys",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E7-11",
      "story": "Dev: download outputs through expiring pre-signed links",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E7-12",
      "story": "Admin: set rate limits and quotas per API key",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E7-13",
      "story": "Ops: connect through Zapier, Make and n8n",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E7-14",
      "story": "Dev: submit many render or extraction jobs in one batch call",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E7-15",
      "story": "Ops: ingest files from an email inbox, cloud drive or bucket automatically",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E7-16",
      "story": "Admin: connect to CRM and ERP systems such as Salesforce and SAP",
      "priority": "Could",
      "size": "XL"
    }
  ],
  "E8": [
    {
      "id": "E8-01",
      "story": "Ops: upload PDF and image files (PNG, JPEG, TIFF) in the UI or by API",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E8-02",
      "story": "Ops: have digital and scanned pages detected and routed automatically",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E8-03",
      "story": "Ops: get layout analysis with reading order, headings, lists and tables",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E8-04",
      "story": "Ops: get OCR for scans with a chosen language",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E8-05",
      "story": "Ops: handle long and multi-page files with page limits and progress",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E8-06",
      "story": "Dev: receive a page model as JSON and Markdown with bounding boxes on every element",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E8-07",
      "story": "Ops: click any extracted value and see its source region highlighted",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E8-08",
      "story": "Admin: swap or add extraction engines through a plug-in interface",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E8-09",
      "story": "Ops: get scans cleaned up by deskew, rotation and contrast fixes",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E8-10",
      "story": "Ops: have the script and language of each page detected automatically",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E8-11",
      "story": "Ops: parse Word, Excel, PowerPoint and HTML files with the same pipeline",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E8-12",
      "story": "Admin: use a GPU when available and fall back to CPU",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E8-13",
      "story": "Ops: have documents routed to the best engine by type and measured accuracy",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E8-14",
      "story": "Ops: recover tables without borders and tables spanning pages",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E8-15",
      "story": "Ops: classify documents (invoice, receipt, contract, form) and choose a schema automatically",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E8-16",
      "story": "Ops: read handwriting through a vision-language engine",
      "priority": "Could",
      "size": "XL"
    },
    {
      "id": "E8-17",
      "story": "Ops: split multi-document scans into separate documents",
      "priority": "Could",
      "size": "XL"
    },
    {
      "id": "E8-18",
      "story": "Ops: read barcodes and QR codes on pages",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E8-19",
      "story": "Ops: parse email files and their attachments",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E8-20",
      "story": "Admin: redact sensitive fields before results are stored",
      "priority": "Could",
      "size": "L"
    }
  ],
  "E9": [
    {
      "id": "E9-01",
      "story": "Ops: define an extraction schema with fields, types, required flags and repeating tables",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-02",
      "story": "Ops: start from bundled schemas for invoice, receipt and purchase order",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E9-03",
      "story": "Dev: fill schema fields through a pluggable extractor with a bundled local option and optional cloud or LLM plug-ins",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-04",
      "story": "Ops: see a confidence score on every field",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-05",
      "story": "Ops: apply validation rules (patterns, ranges, checksums, totals that must add up)",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-06",
      "story": "Ops: get dates, currencies and numbers normalized by locale",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E9-07",
      "story": "Ops: extract line items into arrays",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-08",
      "story": "Ops: export results as JSON, CSV or Excel and by webhook",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E9-09",
      "story": "Dev: run an extraction benchmark on labelled documents and get an accuracy report per schema",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E9-10",
      "story": "Loc: match field labels in Arabic, Hindi, Thai, Chinese and other scripts",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E9-11",
      "story": "Admin: version schemas and migrate stored results",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E9-12",
      "story": "Ops: auto-approve documents whose fields all clear a confidence threshold",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E9-13",
      "story": "Ops: detect duplicate documents by file hash and fuzzy field match",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E9-14",
      "story": "Ops: check values against reference data such as vendor lists and code tables",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E9-15",
      "story": "Dev: supply a few example documents per schema to improve extraction",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E9-16",
      "story": "Ops: cross-check related documents such as invoice against purchase order",
      "priority": "Could",
      "size": "XL"
    }
  ],
  "E10": [
    {
      "id": "E10-01",
      "story": "Ops: review side by side, with the page image on one side and fields on the other",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E10-02",
      "story": "Ops: edit values, draw a box to add a missing field, or mark a field as absent",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E10-03",
      "story": "Ops: see low-confidence and failed-rule fields first and move between them by keyboard",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E10-04",
      "story": "Ops: approve or reject a document, with states new, in review, approved and rejected",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E10-05",
      "story": "Ops: send approved data to a template in one click",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E10-06",
      "story": "Admin: keep a log of every correction with original value, new value, user and time",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E10-07",
      "story": "Ops: work from a queue with filters and assign documents to reviewers",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E10-08",
      "story": "Ops: use the review screen in right-to-left languages and with non-Latin field labels",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E10-09",
      "story": "Admin: turn the correction log into evaluation sets and fine-tuning exports",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E10-10",
      "story": "Admin: see reviewer metrics such as time per document and correction rate",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E10-11",
      "story": "Ops: approve many documents at once when confidence is above a threshold",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E10-12",
      "story": "Admin: adjust rules or examples automatically from repeated corrections",
      "priority": "Could",
      "size": "XL"
    },
    {
      "id": "E10-13",
      "story": "Admin: require a second reviewer for high-value fields",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E10-14",
      "story": "Ops: comment on a document or field and mention colleagues",
      "priority": "Could",
      "size": "M"
    }
  ],
  "E11": [
    {
      "id": "E11-01",
      "story": "Admin: create local users with admin, editor and viewer roles",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E11-02",
      "story": "Admin: get secure password storage, session handling, CSRF protection and login rate limits",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E11-03",
      "story": "Admin: run behind TLS with documented configuration",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E11-04",
      "story": "Admin: have uploads checked by size and type limits, an optional virus-scan hook, and rendering in a sandbox with no network access",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E11-05",
      "story": "Admin: scan dependencies and licences in CI against an allow-list of MIT, Apache-2.0 and OFL",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E11-06",
      "story": "Admin: sign in with an identity provider through OIDC or SAML",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-07",
      "story": "Admin: set fine-grained permissions per folder, template or schema",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-08",
      "story": "Admin: read an exportable audit log of admin, template and API events",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E11-09",
      "story": "Admin: encrypt stored files and manage keys",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-10",
      "story": "Admin: publish a security policy and commission an independent penetration test",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E11-11",
      "story": "Admin: detect and mask personal data in logs and outputs",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-12",
      "story": "Admin: sync users and groups from the identity provider (SCIM)",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E11-13",
      "story": "Admin: pin data to a region in the hosted service",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-14",
      "story": "Admin: set retention and deletion policies with deletion evidence",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E11-15",
      "story": "Admin: fulfil data-subject export and deletion requests",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E11-16",
      "story": "Admin: prepare for SOC 2 or ISO 27001 for the hosted service",
      "priority": "Could",
      "size": "XL"
    }
  ],
  "E12": [
    {
      "id": "E12-01",
      "story": "Dev: rely on a durable job queue so async jobs survive restarts",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E12-02",
      "story": "Admin: cap memory, CPU and run time per render or extraction job",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E12-03",
      "story": "Admin: scale render workers and extraction workers separately",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E12-04",
      "story": "Ops: run large batches with progress and partial-failure handling",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E12-05",
      "story": "Admin: get retries with backoff and a dead-letter queue",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E12-06",
      "story": "Admin: scrape a metrics endpoint and use ready-made dashboards",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E12-07",
      "story": "Admin: get structured logs with correlation IDs and OpenTelemetry traces",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E12-08",
      "story": "Dev: get faster repeat renders through caching of fonts and compiled templates",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E12-09",
      "story": "Admin: use a published load-test suite and benchmark results",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E12-10",
      "story": "Admin: set latency objectives and alerts",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E12-11",
      "story": "Admin: schedule GPU jobs and control cost for model-based extraction",
      "priority": "Could",
      "size": "L"
    },
    {
      "id": "E12-12",
      "story": "Admin: upgrade with rolling deploys and no downtime",
      "priority": "Could",
      "size": "L"
    }
  ],
  "E13": [
    {
      "id": "E13-01",
      "story": "Admin: connect my own model, local or through an API, with prompt and log controls",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E13-02",
      "story": "Admin: see AI output always presented as a suggestion, never published automatically",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E13-03",
      "story": "Dev: run an evaluation suite for every AI feature, with regression and hallucination checks",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E13-04",
      "story": "Dev: let agents list templates, render documents and digitize files through an MCP server",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E13-05",
      "story": "Owner: turn a sample PDF or Word file into a draft template by detecting fixed and variable regions",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E13-06",
      "story": "Owner: draft a template from a plain-language description",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E13-07",
      "story": "Loc: translate template text with a glossary and human approval",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E13-08",
      "story": "Ops: get suggested schema fields from a sample document",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E13-09",
      "story": "Dev: get validation errors explained in plain language with a suggested fix",
      "priority": "Could",
      "size": "M"
    },
    {
      "id": "E13-10",
      "story": "Owner: edit a template with natural-language instructions",
      "priority": "Could",
      "size": "L"
    }
  ],
  "E14": [
    {
      "id": "E14-01",
      "story": "Dev: follow a 10-minute quickstart and an API reference",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E14-02",
      "story": "Contributor: read a contributor guide, code of conduct, issue templates and the chosen contribution agreement",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E14-03",
      "story": "Loc: view the public script test matrix as a page in the docs",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E14-04",
      "story": "Admin: use a UI built on an i18n framework from day one",
      "priority": "Must",
      "size": "S"
    },
    {
      "id": "E14-05",
      "story": "Dev: try sample apps (invoice generator, multilingual certificate, scan-to-report)",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E14-06",
      "story": "Dev: follow a public roadmap and changelog",
      "priority": "Should",
      "size": "S"
    },
    {
      "id": "E14-07",
      "story": "Dev: extend renderers, extractors and storage through a plug-in system",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E14-08",
      "story": "Dev: import templates from pdfme, Carbone and docxtemplater formats",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E14-09",
      "story": "Dev: ask questions in a community forum or chat with maintainer office hours",
      "priority": "Could",
      "size": "S"
    },
    {
      "id": "E14-10",
      "story": "Admin: use the interface in several languages",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E14-11",
      "story": "Dev: read documentation in the top five languages by usage",
      "priority": "Should",
      "size": "L"
    },
    {
      "id": "E14-12",
      "story": "Owner: browse a community template marketplace with ratings and licence tags",
      "priority": "Could",
      "size": "XL"
    },
    {
      "id": "E14-13",
      "story": "Dev: find certified partners and integrators",
      "priority": "Could",
      "size": "M"
    }
  ],
  "E15": [
    {
      "id": "E15-01",
      "story": "Admin: run each customer in an isolated tenant",
      "priority": "Must",
      "size": "XL"
    },
    {
      "id": "E15-02",
      "story": "Admin: meter documents rendered and pages extracted per tenant",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E15-03",
      "story": "Owner: sign up and manage my organization and team without help",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E15-04",
      "story": "Owner: pay through plans with invoices and tax handled by a payment provider",
      "priority": "Must",
      "size": "L"
    },
    {
      "id": "E15-05",
      "story": "Admin: enforce quotas and prevent abuse",
      "priority": "Must",
      "size": "M"
    },
    {
      "id": "E15-06",
      "story": "Owner: start on a free tier",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E15-07",
      "story": "Admin: publish a status page and support tooling",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E15-08",
      "story": "Admin: apply the published open-core policy through licence keys for paid features",
      "priority": "Should",
      "size": "M"
    },
    {
      "id": "E15-09",
      "story": "Admin: choose a deployment region",
      "priority": "Should",
      "size": "XL"
    },
    {
      "id": "E15-10",
      "story": "Admin: buy through cloud provider marketplaces",
      "priority": "Could",
      "size": "L"
    }
  ]
}
