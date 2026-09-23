# Document platform planning

Planning baseline created on 2026-09-22 from [the supplied backlog](Backlog_DocGen_DocTemplating_DocDigitization.docx). E1 MVP foundation code is now prepared; runtime verification is pending the dependency exception decision. See [E1 status and setup](docs/e1-foundation.md).

| Document | Purpose |
| --- | --- |
| [E1 foundation](docs/e1-foundation.md) | Setup, configuration, per-story status and verification commands |
| [Dependency review](docs/dependencies.md) | Pinned foundation dependencies and outstanding licence exceptions |
| [All epics and stories](docs/epics.md) | All 15 epics and 218 stories, with original acceptance criteria, priority, size and release |
| [Technology stack](docs/tech-stack.md) | Recommended architecture, alternatives, dependency constraints and research sources |
| [Implementation plan](docs/implementation-plan.md) | Epic dependencies, milestones, validation gates and unresolved requirements |
| [Design decisions](docs/design-decisions.md) | Living decision register; proposed choices remain distinct from accepted or implemented choices |
| [Project instructions](AGENTS.md) | Instructions for future implementation and use of project skills |

Recommended direction: React/TypeScript and ProseMirror for the editor, FastAPI/Python for APIs and processing, PostgreSQL for metadata and durable jobs, local/S3-compatible file storage, and isolated document workers. Compare Chromium and WeasyPrint before choosing the PDF renderer. Use Docling, PaddleOCR and a Tesseract adapter for digitization. Word-to-PDF conversion and the broader runtime depend on resolving the backlog's licence-policy conflict.

The user has started E1 foundation implementation. Run the multilingual rendering spike (E4-01) before selecting a renderer or claiming CPU document-processing acceptance, then complete generation milestone M1 and digitization milestone M2. No calendar commitment is inferred from relative story sizes.

## Project skills

Repository-local skills are maintained in `skills/` and explicitly routed by `AGENTS.md`:

- [Document-platform implementation](skills/docplatform-implementation/SKILL.md)
- [Multilingual rendering verification](skills/docplatform-rendering/SKILL.md)
- [Extraction and provenance verification](skills/docplatform-extraction/SKILL.md)

They are ready for explicit file-based use by future project agents. They have not been globally installed or registered in `.agents/skills`; native skill-menu discovery is therefore not claimed. The maintained repository routing makes them usable without changing machine-wide settings. Native discovery, if desired later, uses the locations described in [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Backlog verification

Run `python scripts/extract_backlog.py` to reproduce `docs/epics.md` from the DOCX using Python's standard library. The script checks unique IDs and release totals. The source document remains unchanged. Generated backlog text is separate from proposed architecture and delivery refinements.
