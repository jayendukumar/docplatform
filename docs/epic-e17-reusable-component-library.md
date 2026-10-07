# E17 — Reusable component library (proposed scope addition)

Status: Proposed scope addition, implementation slice accepted on 2026-10-06.

This epic extends the original 15-epic backlog. `docs/epics.md` remains generated from the supplied DOCX and is not rewritten. The implementation is an enabler for the existing editor and template-management stories, especially E2-02 and E3-03; it does not alter their original acceptance criteria.

## Outcome

A user can turn a meaningful group of existing editor blocks into a named reusable component, find it in a component library, insert it into any template, and understand whether a selected object is a component or an ordinary block. Components remain declarative document content: they may contain supported base blocks and nested component references, but never executable code or network instructions.

## Stories and acceptance criteria

| ID | Story | Acceptance |
| --- | --- | --- |
| E17-01 | Owner: save selected editor blocks as a named reusable component | The user can select one or more blocks, name the component in an inline editor form, save it, and see a clear success or validation message. Duplicate names are reported without losing the selection. |
| E17-02 | Owner: browse and insert reusable components from a library | The editor exposes a searchable, keyboard-usable library with each component's name and version. Insert adds a reference block to the current template; the stored template contains the component reference rather than a copied expansion. |
| E17-03 | Owner: reuse a component in any template | A component created while editing one template can be inserted into another template after reopening it. Rendering expands the current component definition and preserves cycle/missing-component safeguards. |
| E17-04 | Owner: understand and maintain component content | Selecting a component identifies it as reusable, shows its child objects, and offers an explicit update action for the component definition. Ordinary block deletion and component-reference deletion are distinct actions. |
| E17-05 | Dev: keep reusable definitions safe and versioned | Component definitions are validated as bounded block trees, nested references remain declarative, updates increment the component version, and existing template versions remain reproducible under the documented live-reference policy. |

## Ease-of-use decisions

- The library is placed beside the editor actions, not hidden in page settings.
- Creation uses an inline name field with a disabled save action until blocks are selected and a name is present; browser prompts are not used.
- Insertion is one click and returns focus to the newly inserted reference block.
- A component reference is visually and semantically distinct from its children. The editor does not silently flatten it.
- The first implementation keeps the existing live-reference behavior: a component update affects every template that references it at render time. A future release may add immutable component versions or pinning after measured demand.

## Delivery sequence

1. Replace prompt/button-only creation with a visible library workflow and selection feedback.
2. Add component-list filtering, insert actions, and clear component-reference status.
3. Verify cross-template reuse, nested expansion, cycle rejection, and component version increments.
4. Document the live-reference behavior and identify follow-up work for permissions, immutable component versions, and richer child editing.

## Non-goals for this slice

Marketplace sharing, per-component permissions, immutable version pinning, drag-and-drop layout editing inside an expanded component, and arbitrary script/code execution are not part of E17-01 through E17-05.
