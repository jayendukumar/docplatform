# Template editor and rendering direction

Date: 2026-09-24

## Purpose

This note records the agreed product and technical direction from the 2026-09-24 planning conversation. It is a reference for the next implementation phase and does not rewrite the generated backlog in `docs/epics.md`.

## Agreed target

Prioritize the end-to-end template-authoring flow:

1. An owner creates and edits a template in the browser.
2. The template supports the bounded data-binding and layout rules already defined by the project.
3. The owner previews the template with sample data.
4. The platform renders a PDF through the selected renderer boundary.

The initial renderer remains Chromium. A Prince renderer adapter will be introduced as an optional, explicitly configured alternative. Chromium remains the default until the rendering comparison and acceptance evidence justify changing the default.

The editor direction is hybrid: improve the current bounded browser editor toward a Word-like authoring experience while retaining the platform's versioned JSON template model, safe bindings, reusable components, and isolated rendering boundary. A full DOCX-first office editor is not the immediate target.

## Renderer decision

The renderer must be selected through an adapter boundary rather than being embedded throughout the API and editor. The intended shape is:

```text
Template JSON -> safe HTML/document artifact -> renderer adapter -> PDF + diagnostics
                                                     |-> Chromium (default)
                                                     |-> Prince (optional)
```

The Prince adapter may be developed and benchmarked before purchasing a production license. Prince's free/testing version is suitable only for permitted testing or non-commercial evaluation; its non-commercial output has watermark and attribution conditions. Commercial customer documents, invoices, paid-service output, or redistribution require the appropriate Prince commercial, OEM, or commercial-service license. License selection must be confirmed with YesLogic before commercial deployment.

Prince must remain inside the existing isolated document-worker boundary. The adapter must use the renderer's local-file and network restrictions, including `--no-local-files` and `--no-network` where applicable, and must not expose license material to untrusted document input.

## Editor direction

The immediate editor should remain compatible with the current bounded `TemplateDefinition` contract. Work may make the surface more Word-like through:

- page-oriented editing and preview;
- reliable text editing, selection, copy/paste, undo/redo, and keyboard shortcuts;
- formatting, tables, images, headers, footers, page settings, flow controls, and locale preview;
- reusable component insertion and propagation;
- clearer separation between editing state, saved template versions, and final rendered output.

An embedded office editor such as ONLYOFFICE or Collabora remains a future alternative if true DOCX compatibility becomes the primary requirement. Choosing that path later would be a larger architectural change because DOCX or ODT would become a canonical or first-class document model and bindings, loops, components, versioning, callbacks, and conversion would need a new contract.

## In scope for the next phase

- Complete the critical E2 editor flow, especially the remaining evidence gaps in E2-07, E2-08, and E2-09.
- Stabilize the template-to-render contract and server-authoritative preview.
- Add the renderer adapter abstraction while keeping Chromium as the default.
- Add a Prince adapter boundary, configuration, availability reporting, and isolated integration path.
- Compare Chromium and Prince on the fixed rendering corpus before any default-engine change.
- Verify page flow, tables, images, fonts, metadata, mixed-direction text, and supported script fixtures.
- Keep design decisions, renderer versions, font hashes, licenses, and validation evidence current.

## Deferred backlog

The following remain backlog items unless they become necessary prerequisites:

- a full DOCX-first Word editor;
- ONLYOFFICE or Collabora integration;
- broad governance and promotion workflows;
- hosted service, billing, and tenant features;
- advanced extraction, AI assistance, and ecosystem integrations;
- non-PDF output formats beyond the current planned scope;
- PDF/A and accessible tagged PDF programs unless required by the selected renderer acceptance plan.

Deferral does not change their source priority or release assignment in `docs/epics.md`.

## Constraints and acceptance posture

- Chromium remains the default renderer until empirical evidence supports a change.
- Prince support is optional and must fail clearly when not installed or licensed; it must not silently replace Chromium.
- No native-reader, multilingual, accessibility, font-embedding, or commercial-licensing claim is made without recorded evidence.
- The generated backlog remains unchanged.
- The current project licensing conflict and dependency review remain unresolved until explicitly decided.
- The implementation must preserve CPU-only, offline-capable, network-disabled document processing.

## Reference material

- [Product backlog](epics.md)
- [Implementation plan](implementation-plan.md)
- [Technology stack](tech-stack.md)
- [Template contract](template-contract.md)
- [Rendering candidates](rendering-candidates.md)
- [Design decisions](design-decisions.md)
- [Prince licensing](https://www.princexml.com/purchase/)
- [Prince server integration and isolation guidance](https://www.princexml.com/doc/server-integration/)
