# Editor usability audit

Date: 2026-10-07

This is the first interaction audit of the current editor surface. It follows the human workflow of inserting an object, selecting it, changing its properties, undoing the change, deleting it and inspecting the local preview. It is a usability record, not an accessibility certification or a native-reader rendering approval.

## Findings fixed in this slice

| Area | Human scenario | Failure | Correction | Evidence |
| --- | --- | --- | --- | --- |
| Text block insertion | Start a new template, add the first text block and continue editing | The first rich-text contextual panel changed the grid height and browser scroll position, moving focus toward the lower preview area | Preserve the page scroll position across the insertion reflow while leaving the insertion control focused | `editor text controls preserve focus...` browser test |
| Rich text fields and conditions | Insert a data field or condition, then remove it | A single non-text run could not be removed because deletion was blocked whenever a paragraph had one run | Replace the final removable run with an empty editable text run; the whole text block remains deletable separately | Same browser test; existing rich-text generation test |
| Rich-text paragraphs | Add a second paragraph | Newline characters were collapsed by normal HTML whitespace, making paragraphs appear adjacent | Preserve line breaks in the editor preview with `white-space: pre-line` | Same browser test |
| Table column data path | Add a column and type a path one character at a time | The controlled input was remounted because its React key included the edited path, losing caret focus | Capture the path input caret during input and restore focus/selection after the editor state update | `table column data paths remain editable while typing` browser test |
| Insert history and selection | Insert repeat, image, code, column, shape, conditional, chart or TOC objects, then undo or edit | Several insert handlers bypassed `updateEditorBlocks`, so undo history and selected-block state were inconsistent | Route all insertions through the shared history helper and select the inserted block | Existing insertion/undo coverage plus focused browser tests |
| Rich-text block switching | Edit a multi-paragraph block, then select another text block | The contextual panel’s stale paragraph/run selection could point outside the newly selected document | Clamp paragraph and run selection whenever the document changes | Component-level defensive effect; covered through the rich-text interaction workflow |

## Reviewed interaction surfaces

| Component | Insert | Edit/configure | Remove/reorder | Current status |
| --- | --- | --- | --- | --- |
| Text and rich text | Text block, paragraph, text run, data field, condition | Text, alignment, font, size, colour, condition branches | Run removal and whole-block deletion | Fixed and focused-tested |
| Repeatable table | Table block and columns | Column labels/paths/formats/alignment, widths, table style, row styles, filters | Column remove/reorder and block deletion | Fixed path caret; focused-tested; broader style combinations remain regression scope |
| Repeating section | Insert section | Data path, alias and repeated text | Whole-block deletion and undo | Insert history standardized; existing browser coverage |
| Conditional section | Insert section | Condition path, enabled value, then/else text | Whole-block deletion and undo | Insert history standardized; existing browser coverage |
| Image and barcode/QR | Insert object, upload/replace asset | Source, alt text, size, alignment and code settings | Whole-block deletion | Insert history and selection standardized; existing output coverage |
| Chart | Insert chart | Type, axes, data binding/static data, colours and display options | Whole-block deletion | Insert history and selection standardized; existing chart coverage |
| Columns | Start, break and end markers | Count, gap, widths and rule styling | Marker deletion | Insert history standardized; widths intentionally commit on blur to avoid rejecting incomplete comma-separated input |
| Shape | Line/rectangle insertion | Geometry, stroke, fill, layer and fixed placement | Whole-block deletion | Insert history standardized; existing shape coverage |
| Table of contents | Insert TOC | Anchor/label/level behavior | Whole-block deletion | Insert history and selection standardized; existing output coverage |
| Reusable component | Insert/reference, select child, update | Component library search and child controls | Remove reference or block | Existing component workflow coverage |
| Page settings/furniture | Open settings and add page furniture | Page size, margins, header/footer, rules, background and numbering | Reset/clear where offered | Existing settings/output coverage; native-reader/accessibility review remains open |
| Preview/history | Add objects and inspect preview/version list | Page navigation, local preview and server preview | Restore version or leave editor | Existing preview/history coverage; browser workflow extended here |

## Remaining validation boundaries

- The audit does not claim complete keyboard, screen-reader, IME or touch certification.
- Local editor preview and server-generated output are tested separately; neither substitutes for native Word/PDF reader review.
- The column-width field intentionally commits on blur because it accepts a comma-separated list and must not reject intermediate input. It should receive a dedicated structured editor if users need live validation or per-column controls.
- Full cross-component combinations, multilingual typing and long-document pagination remain follow-up test expansion.
