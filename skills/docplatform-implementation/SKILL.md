---
name: docplatform-implementation
description: Implement or review a story in this document platform while preserving backlog traceability and recording its design decisions. Use for platform code, contracts, dependency choices, and project planning changes.
---

# Document-platform implementation

Resolve document paths from the repository root containing `AGENTS.md`.

Read the relevant story and acceptance criteria in `docs/epics.md`, then applicable entries in `docs/design-decisions.md`. `docs/tech-stack.md` is a proposal, not evidence that a dependency is installed or a decision approved. Use `docs/implementation-plan.md` to identify prerequisites without rewriting source priorities.

For the requested change:

1. Identify story IDs and the observable acceptance result. If work has no source story, label it an implementation enabler or proposed scope addition.
2. Record each design choice in `docs/design-decisions.md` before or with the change. Include behavioral defaults and UI choices as well as architecture. Keep Proposed/Accepted/Implemented distinct; link actual implementation and validation before marking Implemented. Preserve superseded reasoning.
3. Check exact versions and transitive/runtime licences before introducing dependencies, fonts or model weights. DD-013's allow-list conflict is unresolved. Do not transform a proposed exception into an accepted one.
4. Preserve local CPU execution, network-disabled untrusted document processing, versioned contracts and API-side authorization. Use isolated document execution even for synchronous requests.
5. Verify the changed acceptance criteria using the smallest relevant contract/integration/end-to-end checks. Record actual results and gaps. Do not claim native-reader, second-engineer or accessibility sign-off that did not happen.
6. Update relevant user/API documentation and the decision record in the same change. `docs/epics.md` is generated from the original DOCX; record proposed scope changes separately.

## Editor component-control rule

Every selectable document component owns one contextual-actions relationship. Component-specific controls must render inside the active component's contextual-actions container, alongside shared alignment, position, property and delete actions. Do not add a second floating, sibling, or grid-level control panel for a component type. If a component editor is implemented as a reusable child panel, mount it into the active contextual-actions container and preserve one accessible relationship. Verify the rule by selecting the component in the tree and confirming its type-specific controls are descendants of the contextual-actions region.

Use the shared contextual-control styling surface for every component-specific control: inherit the contextual panel font, use the common label/input/select/button tokens, and add only component-specific layout rules where necessary. Do not rely on browser-default form-control typography or create a component-only visual language.

For rendering/text/font/output work, also load `skills/docplatform-rendering/SKILL.md`. For OCR/extraction/provenance/review work, also load `skills/docplatform-extraction/SKILL.md`. These are file-based project skills routed by AGENTS.md; no machine-wide installation is required.
