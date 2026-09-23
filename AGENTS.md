# Document platform project instructions

## Context and source of truth

Read `README.md`, the relevant stories in `docs/epics.md`, `docs/tech-stack.md`, and `docs/design-decisions.md` before implementation. Use `docs/implementation-plan.md` for sequencing. The DOCX is the original baseline; `docs/epics.md` is generated and must not be silently rewritten to change scope.

## Design decision record: user requirement

The user requires every design decision to be documented while the project is implemented. Record a decision before or with the change in `docs/design-decisions.md`. This includes architecture, dependencies, schemas, contracts, security, UI/UX, document behavior, operational defaults and changes in scope. Use a full DD entry for consequential choices; small reversible choices may share a dated batch entry with an explicit rationale for each. Mechanical edits with no choice may reference the existing decision.

Include date, status, affected story IDs, context, choice, alternatives, consequences, validation and implementation references. Do not present a proposal as accepted or implemented. An implemented decision must link the changed files and actual validation evidence. Update the entry when evidence changes; supersede prior decisions rather than erasing their history. A decision entry is not permission to publish, deploy, contact people or change product licensing.

## Project skills

These repository-local skills use `SKILL.md` format and are loaded explicitly through these instructions; no global installation or native skill-menu registration is assumed.

- For implementing or reviewing a backlog story, read `skills/docplatform-implementation/SKILL.md`.
- For editor text behavior, fonts, localization, rendering or Word/PDF output, also read `skills/docplatform-rendering/SKILL.md`.
- For ingestion, OCR, schema extraction, confidence, provenance or correction/review, also read `skills/docplatform-extraction/SKILL.md`.

Load only applicable skills. Resolve their project references from this repository root.

## Implementation constraints

- Preserve IDs and source release/priority assignments; label proposed re-sequencing explicitly.
- Support CPU-only self-hosting and a local extraction path without external calls. External AI services are optional and configured deliberately.
- Treat rendering engines as provisional until E4-01 evidence is recorded. Do not claim multilingual correctness from library documentation alone.
- Templates cannot execute arbitrary code or access networks. Keep document child processes isolated from credentials and privileged worker supervisors.
- Retain original and normalized extraction values, source locations, versions and correction history. Only approved snapshots feed the closed-loop generation action.
- Review actual dependency, model, font and container licences before adoption. The source allow-list conflict in DD-013 remains unresolved; do not silently weaken it or claim compliance.
- Verify relevant acceptance criteria and record results. Do not invent benchmarks, native-reader approval, accessibility certification or second-engineer review.
- Keep design documentation and implementation references current in the same change. Do not build future release features merely because an interface anticipates them.
