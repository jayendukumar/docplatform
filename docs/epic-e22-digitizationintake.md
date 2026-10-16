# Epic: PDF Document Intelligence & Structured Extraction Engine

Epic E22


## 1. Epic definition

Epic statement

For good docs, I want to ingest PDF documents and extract their content, formatting, layout, and structural hierarchy into a consistent JSON representation, so that the information can be searched, analyzed, reconstructed, transformed, or consumed programmatically without using Large Language Models.

Business objectives

- Extract native text, embedded images, vector graphics, tables, annotations, and document metadata.
- Preserve physical layout information, including coordinates, fonts, styles, colors, and reading order.
- Infer logical structure, such as headings, paragraphs, lists, columns, headers, and footers.
- Support native, scanned, and mixed-content PDFs.
- Produce validated, versioned JSON with complete traceability to the source document.
- Provide visual inspection and diagnostic tools to improve extraction accuracy.
- Support extensibility, performance optimization, security, and automated testing.

Architectural principles

1. Extraction and structural interpretation must be separate stages.
2. Raw extracted information must never be discarded during normalization.
3. All inferred classifications should retain evidence and confidence or heuristic scores.
4. Every logical element must be traceable to its source page and bounding box.
5. Each processing stage must be independently testable and replaceable.
6. No LLM services, prompts, or generative AI dependencies are permitted.
7. Machine-learning-based OCR or layout analysis must be optional and disabled when operating in strict deterministic mode.

## 2. Proposed solution architecture

Ingestion & validation
  - File checks
  - PDF metadata
  - Page classification

Native PDF extraction
  - PyMuPDF
  - pdfplumber

OCR fallback
  - Tesseract
  - OpenCV

Canonical physical document model
   - Pages 
   - Text spans 
   - Fonts 
   - Bounding boxes
   - Images
   - Drawings

Layout & reading order
Style & heading analysis
Paragraph & list detection
Tables & cross-page analysis


Logical document model
    - Section hierarchy 
    - Content blocks
    - Relationships
    - Provenance

JSON export & validation

Visual inspector & diagnostics

## 3. Story backlog and priority

The following backlog contains 34 user stories grouped under 10 implementation features.

Backlog navigator

34 stories

All 10 features

01

Project foundation & ingestion

E22-101 · E22-102 · E22-103 · E22-104

4 stories

02

Physical content extraction

E22-201 · E22-202 · E22-203 · E22-204

4 stories

03

OCR & mixed-content processing

E22-301 · E22-302 · E22-303

3 stories

04

Layout & reading order

E22-401 · E22-402 · E22-403 · E22-404

4 stories

05

Logical document interpretation

E22-501 · E22-502 · E22-503 · E22-504 · E22-505

5 stories

06

Tables & complex document objects

E22-601 · E22-602 · E22-603

3 stories

07

Schema, export & provenance

E22-701 · E22-702 · E22-703

3 stories

08

Inspection & diagnostics

E22-801 · E22-802 · E22-803

3 stories

09

Quality, security & performance

E22-901 · E22-902 · E22-903

3 stories

10

Delivery & integration

E22-1001 · E22-1002

2 stories

Each story below includes intent, acceptance criteria, and implementation guidance. Priorities are P0 (core), P1 (production capability), and P2 (enhancement).

## 4. Detailed user stories

Prework
Establish a corpus of test pdfs  covering reports, invoices, contracts, scanned documents, multi-column layouts, and complex tables. Extend the corpus to legal documents etc but not more than 30 documents in total.

Initial corpus: [E22 PDF extraction corpus](../e22-corpus/README.md). It currently contains 12 synthetic fixtures plus 9 local user-provided statement PDFs (21 total), including legal-style, image-only scan, mixed-content, two-column, multi-page and complex-table examples. Manifest labels and text anchors are not complete gold annotations; see DD-494 and DD-495 for selection rationale and validation boundaries.

Initial Digitization Intake UI: the user selects one PDF, the app queues the chosen extraction schema and opens a processing screen with job/page progress, the uploaded PDF on the left and the current parser model as JSON on the right. The right pane shows `physical_content` when available and otherwise the current PageModel; it refreshes when durable processing/page state changes. The screen presents nine operational tasks in extraction order: PDF validation; page inspection and metadata capture; page classification; native content extraction; conditional OCR; content/provenance merge; layout and reading-order analysis; logical structure and complex-content reconstruction; and versioned JSON assembly and validation. The first three steps complete during upload. Later step status is not yet exposed; aggregate job/page progress remains separate. The addressable screen resumes status polling after refresh. The displayed parser model is interim output, not the final schema extraction result; review actions remain deferred. This UI does not imply OCR availability for scans or complete PDF layout support.

### Feature 01 — Project foundation & PDF ingestion

E22-101 — Establish modular Python architecture

P0

User story: As a developer, I want independent processing components with well-defined contracts, so that extraction algorithms can evolve without affecting the entire system.

Acceptance criteria

- Python package uses typed models and well-defined processing interfaces.
- Ingestion, extraction, normalization, classification, and export can execute independently.
- Every stage has unit tests, structured logging, and consistent error handling.
- Replacing a processing implementation does not require changes to downstream consumers.

Implementation advice: Use Python 3.12+, Pydantic for data contracts, `Protocol` or abstract base classes for processors, and `pytest`. Implement a pipeline orchestrator rather than building all logic inside a single extractor class. Pin dependency versions.

E22-102 — Validate and inspect incoming PDF files

P0

User story: As a processing service, I want to validate incoming PDFs before processing so that invalid, corrupted, encrypted, or unsupported files are handled safely.

Acceptance criteria

- Verify file type, file size, PDF validity, and page count.
- Detect encryption, password requirements, and malformed documents.
- Capture file hash and document metadata.
- Report a structured rejection reason rather than crashing.
- Enforce configurable page, size, and execution limits.

Implementation advice: Use PyMuPDF for document opening, encryption checks, page inspection, and metadata. Use SHA-256 to create document identifiers. Open untrusted PDFs within a resource-constrained worker.

E22-103 — Classify individual page types

P0

User story: As a document processor, I want to determine whether each page is native-text, scanned, or mixed-content so that the appropriate extraction strategy is selected.

Acceptance criteria

- Classification occurs per page, not only per document.
- Detects pages with image coverage but little or no extractable text.
- Distinguishes an ordinary image embedded in a text page from a scanned page.
- Stores the page classification and supporting metrics.
- Supports configurable classification thresholds.

Implementation advice: Combine text character counts, text bounding-box coverage, image coverage, and page dimensions. Do not assume a full-page image always means OCR is necessary; some PDFs have an OCR text layer behind a scanned image.

E22-104 — Normalize PDF coordinate systems

P0

User story: As a downstream consumer, I want a consistent coordinate system across every extracted object so that positions can be reliably interpreted and visualized.

Acceptance criteria

- Bounding boxes use a documented page coordinate convention.
- Page width, height, rotation, and original geometry are retained.
- Coordinates are transformed correctly for rotated and cropped pages.
- Original source coordinates remain available when needed.
- Tests cover 0°, 90°, 180°, and 270° page rotations.

Implementation advice: Use a canonical, top-left-origin system in PDF points with the y-axis increasing downward. Centralize transformations in one utility. Avoid mixing pdfplumber and PyMuPDF coordinates without explicit conversion.

### Feature 02 — Physical content extraction

E22-201 — Extract text at block, line, span, and character levels · `P0`

User story: As a document consumer, I want text extracted at multiple levels of granularity so that I can reconstruct paragraphs and preserve inline formatting.

Acceptance criteria

- Extract blocks, lines, spans, and optionally individual characters.
- Preserve text content, bounding boxes, source page, and source order.
- Detect missing or corrupted text encoding and emit diagnostics.
- Generate stable unique identifiers for every extracted object.
- Preserve whitespace and special characters wherever recoverable.

Implementation advice: Use PyMuPDF `page.get_text("rawdict")` for detailed character extraction and `"dict"` for a lighter representation. Make character-level extraction configurable to limit JSON size.

E22-202 — Extract typography and formatting · `P0`

User story: As a document processor, I want font and visual style metadata for every text span so that I can reconstruct formatting and identify semantic roles.

Acceptance criteria

- Extract font family, actual font name, size, color, and rendering flags.
- Detect bold, italic, and superscript where source information allows.
- Support underline and strikethrough detection using graphical evidence.
- Preserve mixed formatting within the same paragraph.
- Represent unknown or unsupported styles explicitly.

Implementation advice: Extract span attributes from PyMuPDF. Use font descriptors and drawing geometry for style inference. Underlines and text highlights may be graphical elements or annotations rather than text properties.

E22-203 — Extract images and vector graphics · `P0`

User story: As a document consumer, I want embedded visual objects extracted with their positions so that the complete page can be reconstructed.

Acceptance criteria

- Extract embedded raster images and image placement metadata.
- Detect multiple placements of the same image.
- Extract vector paths, shapes, colors, strokes, and geometry.
- Associate extracted assets with their source page.
- Export binaries separately with JSON references.

Implementation advice: Use PyMuPDF image APIs, `get_image_info()`, and `get_drawings()`. Preserve image hashes for deduplication. Keep vector paths in the physical model, but provide a simplified bounding-box representation for ordinary consumers.

E22-204 — Extract document metadata, links, and annotations · `P1`

User story: As a downstream application, I want metadata, hyperlinks, bookmarks, and annotations represented in JSON so that document navigation and supplementary information remain available.

Acceptance criteria

- Extract PDF metadata and the document outline.
- Capture clickable links and their target destinations.
- Record supported annotations, comments, and attachment metadata.
- Associate annotations with page regions.
- Clearly identify unsupported element types.

Implementation advice: Use PyMuPDF and pypdf where their APIs are complementary. Sanitize external URIs; extraction must never automatically execute embedded actions or open referenced URLs.

### Current implementation status and remaining evidence gaps (2026-10-15)

The E22-201–204 acceptance criteria above remain the source scope. This status note records current implementation and verification gaps; it does not change story priority or acceptance criteria. All four stories remain `partial` in the [status overlay](../frontend/src/storyStatus.ts). The focused regression run passed 46 tests across `backend/tests/test_pdf_physical.py`, `test_pdf_validation.py`, and `test_ingestion.py`. These tests are contract regressions, not corpus accuracy results. The corpus contains 12 checked-in synthetic PDFs and 9 local PDFs; the available text anchors are not complete gold labels ([corpus guidance](../e22-corpus/README.md)).

#### E22-201 — Text hierarchy and geometry

- **Verified slice:** Optional PyMuPDF extraction supplies block/line/span/character records, parent-child links, deterministic IDs for a fixed parser version, source order, character boxes, and canonical span/line/block boxes. Tests cover repeatable IDs, hierarchy links, whitespace, parser observations, crop boxes, page rotation, and character opt-in. The pypdf fallback remains structurally linked.
- **Remaining gaps:** The fallback has no span, line, block, or character bounding boxes. Its span origin is only a baseline point, not a text rectangle; blocks and lines are grouped from text visitor chunks/newlines rather than recovered page layout. There is no corrupted-encoding fixture, nor manually reviewed expected hierarchy/geometry across representative corpus pages. Parser-version changes can change IDs; stability is within a fixed parser/version and source, not a permanent cross-version identifier.
- **Impact:** Consumers using the fallback can read extracted text and its approximate order, but cannot reliably place words or characters over the source page, select text by region, compare geometric reading order, or reconstruct paragraph extents. Geometry-dependent highlighting/review must show unavailable geometry instead of drawing guessed boxes. The PyMuPDF path provides these coordinates when installed and successful.
- **Closure evidence:** Add a fixture with malformed/unmapped text bytes and assert diagnostics; add manually checked block/line/span/character expectations and boxes for representative single-column, multi-column, rotated/cropped, and mixed-font pages; retain the simulated optional-parser-absent test and explicitly assert null geometry in fallback output. Keep source order separate from validated reading order.

#### E22-202 — Typography and formatting

- **Verified slice:** Font name, size, color, bold/italic flags, superscript flag source, parser character-style flags, explicit unknown values, and separate graphical decoration candidates are represented on the optional PyMuPDF path. Current regressions check underline evidence and vector command/style evidence; the base text fixture checks font metadata.
- **Remaining gaps:** There is no affirmative superscript or strikeout fixture, and graphical underline/strike candidates lack tests across varied positions, widths, text rotations, and neighboring rules. The pypdf fallback reports underline, strikethrough, and superscript as unknown and does not expose color; geometric candidates do not turn unknown into a confirmed style.
- **Core-functionality impact:** Text content can still be extracted, but consumers cannot reliably reconstruct those runs' visual appearance or semantics when style evidence is unavailable. Superscripts used for exponents, footnote markers, or ordinal suffixes may render at the baseline; strike-through used to indicate deletion may be lost and deleted text may appear current; underline emphasis or link styling may disappear. This gap does not prevent basic text extraction, but it prevents faithful formatting reconstruction and can obscure meaning conveyed by those styles. Unknown must remain unknown rather than being inferred as false.
- **Closure evidence:** Add separate fixtures for true superscript and ordinary raised text, parser-reported underline and strikeout, and graphic-only underline/strike rules. Include close-by table rules and rotated/dashed examples to assert candidate behavior and avoid false certainty. Assert both positive evidence and explicit unknown/fallback behavior. Review the output against manually labeled source images.

#### E22-203 — Raster images and vector graphics

- **Verified slice:** Repeated placements can point to a deduplicated image asset; asset bytes use separate routes. PyMuPDF paths retain command items and style/geometry metadata. Current tests check repeated placement of a simple image, separate image delivery, and one stroked line path. The pypdf path remains a lower-fidelity fallback.
- **Remaining gaps:** Fixtures do not yet cover a range of image encodings, masks, transforms, or complex path commands and styles. In particular, there is not a reviewed set for JPEG/JPX/TIFF/PNG, image masks/soft masks, page rotation/crop, curves/quadratics, closed and compound paths, fill rules, dashed strokes, joins/caps, opacity, clipping, and optional-content/layer cases. There are no expected-object/geometry checks for those combinations or broad corpus visual review. Parser output is not a guarantee that every clipped or hidden visual object can be reconstructed.
- **Fixture plan (independent of the licensing decision):**
  1. Build small deterministic PDFs by feature, with an explicit expected manifest: page number, object kind, placement/path count, source and canonical bounds, transform, dimensions, media type, hash/dedup relation, commands, fill/stroke, width, dash, cap/join, opacity, and any mask/layer/clipping metadata expected.
  2. Cover PNG, JPEG, TIFF, and JPX where the chosen fixture tooling can produce them; add a repeated image at two sizes/rotations, an image with a soft mask, and one with a hard mask. Check separate asset retrieval, hash deduplication, page association, and that every placement points to the expected asset/mask.
  3. Use distinct vector fixtures for line/rectangle, cubic curve, quadratic curve, closed/compound path, fill-only, stroke-only, fill-and-stroke, even-odd fill, dashed stroke, non-default caps/joins, and transparency. Add crop/rotation and clipping/layer cases with clear expected limitations where the parser intentionally omits visibility semantics.
  4. Add resource-limit fixtures for placement, path-command, path-count, and asset-size caps; assert diagnostics and whole-record omission without dangling asset references. Include malformed or unsupported visual data and assert explicit missing references/diagnostics.
  5. Review each fixture's rendered page against its manifest, then add a small manually annotated set of the existing corpus pages with raster and vector content. Keep expected labels separate from extraction output; report coverage by feature and document family, not a single unsupported accuracy claim.
- **Closure evidence:** The fixture matrix above passes in CI; annotations have been manually checked against the source/render; unsupported visibility/clipping cases are listed; and the story overlay can cite that evidence. This establishes test coverage for stated capabilities, not exhaustive PDF rendering equivalence.

#### E22-204 — Metadata, navigation, annotations, and attachments

- **Verified slice:** Metadata, outlines, safe external links, internal page targets, comments, annotation regions, unsupported-link reasons, and bounded attachment metadata from both FileAttachment annotations and the catalog EmbeddedFiles tree are retained. A normal-ingestion test verifies attachment metadata and confirms the attachment payload is absent from physical JSON and separate image assets. An OpenAction rejection test remains in place.
- **Remaining gaps:** Annotation subtypes and action types do not have a systematic supported/unsupported fixture matrix. The active-content preflight is a bounded lexical gate, not comprehensive action detection or malware scanning. Additional-action combinations, obfuscated/compressed actions, malformed name trees, and broader attachment metadata cases need dedicated regressions and review.
- **Closure evidence:** Add parameterized accepted/rejected cases for supported annotation types, unsupported annotation diagnostics, URI schemes, internal destinations, populated/empty additional actions, JavaScript and launch/open actions, plus malformed and over-limit attachment name trees. Verify unsupported cases never execute or fetch anything and that limits produce diagnostics. Security review must remain a separate gate from story-level extraction tests.

### Feature 03 — OCR & mixed-content processing

E22-301 — Integrate optional OCR fallback · `P1`

User story: As a user, I want text recovered from scanned pages so that image-only PDFs can produce the same JSON structure as native PDFs.

Acceptance criteria

- OCR runs only when required or explicitly requested.
- Recognized text includes bounding boxes and OCR confidence scores.
- Output is normalized to the canonical physical document model.
- Language configuration and OCR enablement are supported.
- Strict no-ML mode can disable OCR entirely.

Implementation advice: Render pages using PyMuPDF, preprocess them with OpenCV, and invoke Tesseract via `pytesseract` or subprocess. Transform OCR pixel coordinates back to canonical PDF page coordinates. Retain the original image and extracted text separately.

E22-302 — Recognize and merge mixed-content regions · `P1`

User story: As a document consumer, I want text from native and scanned regions combined without duplication so that mixed-content pages remain accurate.

Acceptance criteria

- OCR can target individual page regions.
- Existing native text is not duplicated by OCR.
- Overlapping results are reconciled using geometry and text similarity.
- Every merged element records its original extraction method.
- Conflicting results are retained as alternatives or diagnostics.

Implementation advice: Represent extraction candidates independently, then apply spatial overlap and text comparison rules. Avoid silently replacing native text with OCR output.

E22-303 — Support OCR preprocessing and recovery · `P2`

User story: As a processing administrator, I want configurable image preprocessing so that difficult scanned pages can be recovered.

Acceptance criteria

- Supports deskewing, noise reduction, contrast improvement, and rotation detection.
- Retains the original unmodified page image.
- Reports OCR failures and low-confidence regions.
- Allows extraction retries with alternative preprocessing settings.
- Includes benchmarks on low-quality scans.

Implementation advice: Implement OpenCV preprocessing strategies as interchangeable components. Avoid applying aggressive image filters by default because they can damage small characters or thin table lines.

### Feature 04 — Layout analysis & reading order

E22-401 — Segment pages into logical visual regions · `P0`

User story: As a document processor, I want to identify visual regions so that text and graphical elements can be grouped according to their layout.

Acceptance criteria

- Detects text regions, whitespace separators, and potential table regions.
- Groups adjacent blocks using geometric proximity and alignment.
- Detects regions separated by rules or graphical borders.
- Stores region boundaries and their child elements.
- Handles full-width and nested regions.

Implementation advice: Use interval clustering, bounding-box overlap, whitespace projection profiles, and graphical lines. Implement geometry algorithms independently from logical classification.

E22-402 — Detect multi-column document layouts · `P0`

User story: As a downstream application, I want text columns identified so that content from adjacent columns is not incorrectly interleaved.

Acceptance criteria

- Supports one-column and multi-column layouts.
- Identifies full-width text spanning multiple columns.
- Assigns text blocks to their corresponding columns or regions.
- Preserves correct ordering when the number of columns changes.
- Includes tests for two- and three-column documents.

Implementation advice: Use x-axis projections, vertical whitespace corridors, and clustering of block edges. Prefer region-local column detection rather than assuming a single layout for the whole document.

E22-403 — Reconstruct reading order · `P0`

User story: As a document consumer, I want a reliable reading sequence so that extracted content matches the sequence a human reader would follow.

Acceptance criteria

- Assigns an explicit reading-order index to content objects.
- Orders content within each detected region and column.
- Correctly positions spanning headings and full-width tables.
- Handles ambiguous ordering using configurable rules.
- Retains original PDF extraction order alongside inferred order.

Implementation advice: Build an ordering graph from spatial precedence relationships. Resolve graph conflicts deterministically and log ambiguous decisions. Never rely exclusively on PDF internal content order.

E22-404 — Associate captions and nearby elements · `P1`

User story: As a document consumer, I want captions associated with images, diagrams, and tables so that related content can be interpreted together.

Acceptance criteria

- Recognizes caption patterns such as Figure 1 and Table 2.
- Associates captions with nearby visual objects.
- Preserves the location and text of the caption.
- Supports captions appearing above or below their object.
- Represents uncertain associations without silently forcing a match.

Implementation advice: Use numbered-pattern recognition, proximity, font attributes, and geometric containment. Store associations as references between objects rather than embedding duplicated text.

### Feature 05 — Logical document interpretation

E22-501 — Detect document titles and heading levels · `P0`

User story: As a downstream application, I want headings and hierarchy identified so that the document can be navigated by sections.

Acceptance criteria

- Distinguishes document title, section heading, subsection heading, and body text.
- Uses font statistics, alignment, numbering, and whitespace evidence.
- Supports configurable style-based rules.
- Assigns heading levels consistently within a document.
- Stores classification scores and supporting evidence.

Implementation advice: First determine the dominant body font and size. Build a document-wide typography profile. Then classify heading candidates using font prominence, boldness, indentation, whitespace, and numbering patterns such as `1.2.3`.

E22-502 — Reconstruct paragraphs · `P0`

User story: As a consumer, I want individual text lines joined into meaningful paragraphs while preserving their original formatting.

Acceptance criteria

- Joins continuation lines into paragraphs.
- Detects paragraph boundaries from spacing and indentation.
- Preserves inline bold, italic, and other span-level formatting.
- Supports configurable hyphenation handling.
- Prevents joining content across unrelated regions or columns.

Implementation advice: Combine line spacing, left-edge alignment, font continuity, line length, and indentation. Keep paragraph-to-source-line relationships so reconstructed text can be traced back.

E22-503 — Identify lists and hierarchy · `P1`

User story: As a document consumer, I want bullet and numbered lists recognized so that list nesting and sequence are preserved.

Acceptance criteria

- Detects bullets, numeric lists, alphabetic lists, and Roman numeral lists.
- Identifies list item boundaries.
- Infers nested levels from indentation and marker patterns.
- Preserves original numbering text.
- Handles wrapped list items.

Implementation advice: Use marker-pattern recognition and indentation clustering. Do not assume every line beginning with a number is a list; contextual validation is needed.

E22-504 — Detect repeated headers, footers, and page numbers · `P0`

User story: As a document consumer, I want repeated page decorations separated from main content so that downstream systems can process the body independently.

Acceptance criteria

- Detects repeated top and bottom elements across pages.
- Recognizes variable page numbering in otherwise consistent footers.
- Does not misclassify section titles or footnotes solely based on location.
- Separates header, footer, page number, and main content.
- Preserves all detected elements rather than deleting them.

Implementation advice: Normalize candidate text and cluster by location across pages. Use recurring patterns, font metadata, and positional consistency. Handle first-page and odd/even-page variations.

E22-505 — Reconstruct cross-page logical sections · `P1`

User story: As a document consumer, I want content continuing across page boundaries to remain connected so that the JSON represents a coherent document.

Acceptance criteria

- Identifies paragraphs continued on the next page.
- Connects headings with the following content across page boundaries.
- Maintains a document-wide section tree.
- Separates recurring headers and footers before continuation detection.
- Retains page-specific segments for source traceability.

Implementation advice: Build logical relationships after individual pages have been classified. Preserve page-local objects, but introduce document-level section and paragraph references.

### Feature 06 — Tables and complex document objects

E22-601 — Detect and extract tables · `P0`

User story: As a downstream consumer, I want tables recognized and extracted into structured rows and cells so that tabular information is usable programmatically.

Acceptance criteria

- Detects ruled and borderless tables.
- Extracts rows, columns, and cell text.
- Preserves individual cell bounding boxes.
- Associates table regions with original text elements.
- Supports multiple tables on one page.
- Avoids duplicating table text as ordinary body paragraphs.

Implementation advice: Start with PyMuPDF `find_tables()` and pdfplumber table extraction. Compare candidate regions and use geometric validation to select results. Store table cell references to original text spans.

E22-602 — Handle merged cells and multi-page tables · `P1`

User story: As a consumer of financial and business reports, I want complex tables reconstructed without losing row and column relationships.

Acceptance criteria

- Supports row spans and column spans.
- Recognizes repeated header rows.
- Detects likely continuations of tables across pages.
- Preserves page-specific table segments.
- Distinguishes empty cells from merged regions where possible.

Implementation advice: Model the table as a logical grid with explicit cell coordinates, row spans, and column spans. Match table continuations using column alignment, header similarity, and proximity to page boundaries.

E22-603 — Preserve diagrams, charts, forms, and unsupported objects · `P2`

User story: As a document consumer, I want complex visual objects preserved even when their full meaning cannot be extracted, so that information is not silently lost.

Acceptance criteria

- Captures image or vector regions representing charts and diagrams.
- Preserves extracted form fields and widget values where supported.
- Includes asset references and bounding boxes.
- Explicitly marks objects whose semantics are unknown.
- Does not fabricate chart values or diagram relationships.

Implementation advice: Implement explicit object types such as `chart_candidate`, `diagram_candidate`, `form_field`, and `unknown_region`. Full chart-data reconstruction should be considered a separate future epic.

### Feature 07 — JSON schema, export & provenance

E22-701 — Define versioned canonical JSON schemas · `P0`

User story: As an API consumer, I want predictable, documented JSON structures so that extracted documents can be processed reliably.

Acceptance criteria

- Defines both physical and logical document models.
- Supports nested pages, regions, blocks, spans, and tables.
- Contains schema version, extraction engine version, and processing metadata.
- Validates required and optional attributes.
- Publishes machine-readable JSON Schema.
- Clearly defines handling of unavailable information.

Implementation advice: Use Pydantic models and JSON Schema generation. Prefer strongly typed element variants with explicit `type` identifiers. Define coordinate units, reading-order semantics, and ID rules centrally.

E22-702 — Implement JSON and asset export · `P0`

User story: As a developer, I want extracted results exported consistently so that they can be persisted, transferred, or consumed by other applications.

Acceptance criteria

- Exports valid UTF-8 JSON.
- Supports physical-only, logical-only, and combined views.
- Exports images and other assets with stable references.
- Supports document-level and page-level output.
- Can reserialize results without loss of required fields.
- Writes large outputs safely without producing partial final artifacts.

Implementation advice: Use Pydantic serialization and atomic file replacement. For large documents, optionally use JSON Lines for page-level outputs. Keep binary images outside JSON unless inline encoding is specifically requested.

E22-703 — Implement traceability and extraction evidence · `P0`

User story: As a reviewer or downstream application, I want to trace every inferred element back to its extracted source so that classification decisions can be verified.

Acceptance criteria

- Every logical element references its source physical elements.
- Classification records contain rule identifiers and scores.
- Extraction methods are recorded per element.
- Ambiguous decisions and fallbacks are logged.
- Includes original and inferred reading order.
- Supports locating any logical element on the original PDF page.

Implementation advice: Use immutable source IDs and logical-to-physical references. Make rule execution deterministic, with identifiable versions. Store candidate classifications when useful for diagnostics.

### Feature 08 — Inspection, debugging & diagnostics

E22-801 — Build a visual page-layout inspector · `P1`

User story: As a developer or reviewer, I want to view extracted elements overlaid on their source PDF pages so that I can visually validate document interpretation.

Acceptance criteria

- Displays rendered pages with extraction overlays.
- Uses distinguishable visual styles for headings, paragraphs, tables, images, and page decorations.
- Clicking an element displays its JSON attributes.
- Allows toggling logical and physical representations.
- Highlights the source region when a JSON element is selected.
- Supports page navigation and zooming.

Implementation advice: Use a local FastAPI backend with a lightweight HTML/JavaScript interface. Render page images with PyMuPDF. Use SVG overlays and coordinate transformations for element selection.

E22-802 — Produce extraction diagnostics · `P1`

User story: As an operator, I want processing metrics and warnings so that extraction failures and unusual documents can be diagnosed.

Acceptance criteria

- Reports document and page processing time.
- Counts extracted objects by type.
- Records OCR usage, failed regions, and warnings.
- Identifies pages with suspiciously little extractable content.
- Exposes ambiguous classification and ordering decisions.
- Produces machine-readable diagnostic output.

Implementation advice: Use structured Python logging and stage-level metrics. Provide a document-quality report without claiming probabilistic confidence where only heuristic scores exist.

E22-803 — Support rule configuration and visual tuning · `P2`

User story: As a developer, I want to adjust extraction heuristics without changing source code so that document-specific problems can be resolved efficiently.

Acceptance criteria

- Rules and thresholds can be configured outside code.
- Supports document-family-specific profiles.
- Records the configuration version used for extraction.
- Shows how configuration changes affect classification.
- Allows reprocessing from cached physical extraction results.

Implementation advice: Store rules in validated YAML configuration files. Keep initial configurations read-only through the inspector; interactive editing can be introduced later.

### Feature 09 — Quality, security & performance

E22-901 — Build an automated regression and accuracy suite · `P0`

User story: As a developer, I want measurable extraction quality so that algorithm changes can be evaluated without introducing regressions.

Acceptance criteria

- Maintains a representative sample corpus and expected outputs.
- Tests headings, paragraphs, headers, footers, reading order, and tables.
- Measures detection precision, recall, and F1 where applicable.
- Evaluates bounding-box agreement using intersection-over-union.
- Runs regression tests in CI.
- Tracks results by document family.

Implementation advice: Create a small manually labeled golden dataset before investing heavily in classification heuristics. Compare logical structure rather than performing only exact JSON string comparisons. Use configurable acceptance thresholds based on document types.

E22-902 — Implement safe resource handling and isolation · `P0`

User story: As a system operator, I want untrusted PDF files processed within defined security boundaries so that malformed or hostile documents cannot disrupt the platform.

Acceptance criteria

- Enforces document size, page count, memory, and execution limits.
- Prevents arbitrary code execution through document content.
- Does not automatically access embedded URLs or execute PDF actions.
- Sanitizes asset names and output paths.
- Cleans temporary files after processing.
- Prevents sensitive document text from leaking into routine logs.

Implementation advice: Use isolated worker processes or containers with minimal permissions. Disable network access in extraction workers where possible. Keep dependencies patched and run security scanning in CI.

E22-903 — Optimize processing and memory usage · `P1`

User story: As a system operator, I want predictable processing performance so that large PDFs can be handled efficiently.

Acceptance criteria

- Processes pages incrementally where feasible.
- Avoids holding all rendered page images in memory simultaneously.
- Supports configurable parallelism.
- Reports throughput and memory usage.
- Handles page-level errors without losing successfully processed pages.
- Produces deterministic results across supported worker counts.

Implementation advice: Prefer multiprocessing for independent page extraction. Avoid sharing PyMuPDF document objects across workers. Some reconstruction stages, such as cross-page headers and section detection, must execute after page-level extraction.

### Feature 10 — Delivery & integration

E22-1001 — Provide command-line execution · `P0`

User story: As a developer, I want a CLI to process PDFs without custom Python scripts so that the extractor can be automated.

Acceptance criteria

- Provides commands to extract, validate, inspect, and evaluate documents.
- Supports input/output paths and configuration files.
- Supports selected page ranges and output modes.
- Returns predictable exit codes.
- Displays concise progress and meaningful failure messages.
- Produces consistent output across CLI and library invocation.

Implementation advice: Use Typer or argparse. Keep the CLI as a thin adapter over the application service, never as the location of extraction logic.

E22-1002 — Expose a programmatic API · `P1`

User story: As an application developer, I want to invoke document extraction through a Python API and optionally an HTTP service so that the engine can be integrated with other systems.

Acceptance criteria

- Exposes a stable Python function or service interface.
- Allows consumers to select processing profiles.
- Returns structured results and error information.
- Supports asynchronous job execution for large PDFs in server mode.
- Documents schema compatibility and API versioning.
- Separates HTTP concerns from the extraction engine.

Implementation advice: Start with a Python package interface; wrap it using FastAPI only when remote access is required. Add queues, persistent job storage, and worker scaling when operational requirements justify them.

## 5. Implementation sequence and dependencies

Not all stories should be developed in parallel. For example, heading detection depends on having font information, while reading-order reconstruction depends on page segmentation.

FOUNDATION

E22-101–104

Architecture, ingestion, coordinates

PHYSICAL EXTRACTION

E22-201–203

Text, typography, images, vectors

E22-401–403

Page layout and ordering

E22-301–302

OCR and mixed pages

E22-501–505

Logical structure

E22-601–602

Table reconstruction

E22-701–703 — Validated structured JSON

The schema is designed early and populated incrementally.

E22-801–803 / E22-901–903 / E22-1001–1002

Inspection, testing, security, optimization, interfaces

Testing, security, and schema validation should begin during the first iteration rather than being deferred until all extraction features are complete.

## 6. Suggested delivery plan

| Iteration           | Key deliverables                                                           | Exit milestone                             |
| ------------------- | -------------------------------------------------------------------------- | ------------------------------------------ |
| 1 — Foundation      | Project skeleton, PDF validation, coordinate model, JSON schema foundation | Valid PDFs can be ingested                 |
| 2 — Extraction      | Text, spans, fonts, images, vectors, initial JSON export                   | Physical extraction works                  |
| 3 — Layout          | Page regions, columns, reading order                                       | Content follows plausible reading sequence |
| 4 — Structure       | Headings, paragraphs, lists, headers, footers                              | Logical text documents work                |
| 5 — Complex content | Tables, mixed pages, OCR, cross-page relationships                         | Broader document coverage                  |
| 6 — Productization  | Visual inspector, diagnostics, performance, CLI/API                        | Production readiness assessment            |

The iterations are dependency-based planning units, not fixed-duration sprint commitments.



## 7. Cross-cutting engineering requirements

These requirements apply to all stories.

| Dimension         | Requirement                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Determinism       | Same PDF, configuration, and library versions should produce equivalent canonical results |
| Provenance        | Each logical object links back to source elements and page coordinates                    |
| Reliability       | Page-level failures must be recorded without silently discarding content                  |
| Extensibility     | Extraction and classification algorithms are replaceable                                  |
| Validation        | All final JSON conforms to the published schema                                           |
| Observability     | Each processing stage reports warnings, metrics, and execution details                    |
| Security          | Untrusted documents are processed with restricted permissions and resources               |
| Model restriction | No LLM usage; optional ML components must be controlled by policy                         |
| Performance       | Resource consumption is bounded and measured using a representative PDF corpus            |

## 8. Definition of Done

Story completion checklist

0/10

Acceptance criteria are implemented and demonstrated on sample PDFs.

Unit and integration tests pass.

Regression results are recorded for affected document types.

Every emitted JSON object passes schema validation.

Source coordinates and element provenance are preserved.

Failure cases produce structured diagnostics.

No prohibited LLM or ML dependencies are introduced.

Documentation and configuration examples are updated.

Security and resource handling requirements are satisfied.

Visual output has been reviewed for layout-sensitive stories.


## E22-301 through E22-703 implementation status — 2026-10-16

The current implementation adds a geometry-backed analysis model and explicit export surfaces while preserving the original PageModel and physical-content v2 contracts. `pdf-inspect` now derives layout, logical paragraphs/sections/lists, tables, captions, form candidates, visual-object candidates and diagnostics. Ingestion stores this as `logical_content`; `GET /api/ingestions/{id}/result` includes a validated `canonical_document` where both typed models validate. Schema routes publish physical v2, logical v1 and canonical v1 JSON Schema. `GET /api/ingestions/{id}/export` accepts `view=physical|logical|combined`, `scope=document|page`, `format=json|jsonl|zip`; it assembles the complete output before enforcing the size limit. ZIP output carries referenced stored image assets separately from JSON. The intake processing view displays the canonical JSON beside the source PDF and links to exports.

OCR now supports `ocr_mode=auto|disabled|force`, explicit local commands for PaddleOCR and Tesseract, optional caller-supplied preprocessing JSON and `strict_no_ml_mode`. Auto mode targets scanned and mixed pages; mixed pages retain native text and OCR candidates. Candidate overlaps are labeled likely duplicate/conflict/unique, and native observations are not replaced. PDF pages are rendered locally for OCR, adapter pixel boxes are transformed into page-point coordinates, and preprocessing retries try contrast/denoise variants when OCR fails or reports a mean engine score below 0.55. Per-attempt failures and regions below 0.55 are reported; scores are not calibrated correctness. The API also accepts bounded page-numbered PDF point rectangles for page-region OCR, with at most 100 regions and 25 per page. The original upload remains the stored source. Tesseract 5.4.0.20240606 with `eng`/`osd` data is installed locally and its isolated worker path returned 13 scan-invoice observations. PaddleOCR 3.7.0 and PaddlePaddle 3.3.1 are installed and CPU-checked, but no Paddle model files are present; the adapter requires explicit local detection/recognition model directories and does not download them.

All requested stories remain **Partial**. OCR gaps include: Paddle model files and language packs are not installed; only Tesseract English/orientation data is installed; low-quality scan benchmark fixtures with human-reviewed ground truth and accuracy metrics are absent; mixed-content reconciliation remains a text/box heuristic and OCR candidates are not promoted into canonical logical paragraphs. The exact optional runtime/native licenses and distribution notices remain under DD-013 review. Other gaps include region nesting and changing multi-column fixture coverage; style-rule configurability and calibrated scores; list grouping/nesting and reviewed repeated-furniture variants; merged cells and cross-page tables; chart semantics; complete canonical cross-reference validation; JSONL/ZIP/export-boundary integration fixtures; and broad gold-labeled corpus/native-reader review. The scan-invoice smoke run and compilation checks are contract regression evidence, not OCR accuracy evidence.

| Stories | Implemented slice | Remaining closure evidence |
| --- | --- | --- |
| E22-301 through E22-303 | Engine-specific local adapter commands, CPU Paddle runtime and Tesseract binary installed, strict no-ML switch, PDF rendering/coordinate mapping, bounded page-region OCR, candidate provenance, preprocessing retries and low-confidence/failure reporting | Paddle model/language files; Tesseract/Paddle full licence and notice review; labeled low-quality scan corpus and accuracy/latency measurements; broader engine/language regression fixtures |
| E22-401–404 | Deterministic region/column/order, table boundaries, visual candidates and caption proximity | Two/three-column and changing-layout fixtures; nested region model; caption precision review |
| E22-501–505 | Title/heading, paragraph/style runs, list markers, repeated furniture and cross-page continuation candidates | List grouping/nesting, configurable styles, variant headers/page numbers and reviewed document labels |
| E22-601–603 | PyMuPDF tables with cell/source-span references, continuation candidates, visual/form candidates | Borderless/merged/multipage tables, charts/forms/object fixture matrix and optional-engine availability |
| E22-701–703 | Typed versioned models, schema routes, canonical result, selected JSON/JSONL/ZIP exports and source-linked records | Exhaustive reference validation, export limits/asset fixture coverage, full schema/corpus validation |

Source acceptance criteria and release assignments are unchanged in this E22-specific epic document; generated `docs/epics.md` is untouched. The status overlay marks all requested E22 stories Partial.
