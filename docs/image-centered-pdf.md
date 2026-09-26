# Centered template images in generated PDF

## Symptom

An image authored with `align: "center"` could appear centered in the HTML/editor preview but appear at the left edge of its figure in a generated PDF. The defect was most visible with a PDF engine that retained the block-level figure but treated the replaced `<img>` as an inline element positioned at the figure's start edge.

## Root cause

The portable template emitted `text-align:center` on the figure and calculated alignment-specific margins in the renderer, but the margins were not present on the image's inline style. The stylesheet also supplied class-based rules for the image element. That was sufficient for the browser candidate when its stylesheet was applied, but it made the final geometry dependent on selector handling and inline-image layout in the selected PDF engine. In particular, `margin-left:auto` and `margin-right:auto` do not center an inline-level replaced element reliably.

The generated PDF path stages the rendered HTML and invokes the configured candidate engine in an isolated child process. It does not reposition image content after PDF creation. Therefore, the fix belongs in the portable HTML layout contract, before engine conversion.

## Fix

`backend/app/rendering.py` now applies alignment to the image element itself:

| Authored alignment | Image display | Image margins |
| --- | --- | --- |
| `left` | `block` | `margin-left:0; margin-right:auto` |
| `center` | `block` | `margin-left:auto; margin-right:auto` |
| `right` | `block` | `margin-left:auto; margin-right:0` |

The figure keeps `text-align` as a compatibility hint, while the image's inline style is authoritative for replaced-element geometry. The existing class-based CSS remains as a fallback for preview and candidate engines.

This code path is shared by every image block. It therefore applies to fixed images, bound images, uploaded asset URLs, and image blocks produced inside bounded repeated/conditional rendering paths. The renderer validates the source, width and height before emitting the same alignment contract.

## Repetition and coverage

The implementation was checked for each alignment and for the repeated rendering path:

- unit rendering assertions cover left, center and right image styles;
- the asset/bound-source renderer test confirms the same image path retains the explicit style;
- the configured PDF adapter test reads the staged HTML and verifies the centered inline margin contract reaches the PDF engine;
- the real Chromium candidate test extracts the generated PDF content transform for left, center and right images and compares the image X position with the available content width;
- table/loop rendering uses the same block renderer, so image alignment is not implemented as a special case for one container.

## Evidence and limitation

The focused renderer and PDF tests provide artifact-level and Chromium-candidate geometry evidence. They do not constitute native-reader approval, a second-engine comparison, embedded-font approval, or final E4-01 acceptance. Those gates remain pending and the renderer remains a candidate rather than a selected production engine.
