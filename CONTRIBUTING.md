# Contributing

Thanks for improving Document Platform. Read `AGENTS.md`, the relevant story in `docs/epics.md`, and the applicable local skill before changing code.

## Before opening a change

- Preserve the generated backlog transcription in `docs/epics.md`.
- Record consequential design choices in `docs/design-decisions.md`.
- Keep local CPU execution and the network-disabled document-processing boundary intact.
- Add focused tests and record actual validation. Do not claim native-reader, accessibility, licence, or benchmark approval without evidence.
- Check dependency, font, model, and container licences before adoption. The project licence policy is still unresolved; see DD-013.

## Change checklist

1. Identify the story IDs and acceptance criteria.
2. Update implementation and user/API documentation together.
3. Run the smallest relevant unit, contract, integration, and build checks.
4. Describe known gaps and environmental blockers in the decision record.

Use small, reviewable changes. Do not include secrets, customer documents, generated credentials, or local environment files in a change.
