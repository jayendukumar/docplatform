# Document platform planning

Planning baseline created on 2026-09-22 from [the supplied backlog](Backlog_DocGen_DocTemplating_DocDigitization.docx). E1 MVP foundation code is now prepared; runtime verification is pending the dependency exception decision. See [E1 status and setup](docs/e1-foundation.md).

| Document | Purpose |
| --- | --- |
| [E1 foundation](docs/e1-foundation.md) | Setup, configuration, per-story status and verification commands |
| [Dependency review](docs/dependencies.md) | Pinned foundation dependencies and outstanding licence exceptions |
| [Licence scan](docs/dependencies.md#strict-scan) | Strict allow-list scan and generated SBOM workflow |
| [All epics and stories](docs/epics.md) | All 15 epics and 218 stories, with original acceptance criteria, priority, size and release |
| [E16 template fidelity tuning (proposed)](docs/epic-e16-template-fidelity.md) | Proposed internal epic: rebuild reference PDFs with the editor, compare and rank editor component gaps |
| [E17 reusable component library (proposed)](docs/epic-e17-reusable-component-library.md) | Proposed scope addition: create, browse, insert and maintain declarative reusable component trees |
| [E18 template gallery and workspace organization (proposed)](docs/epic-e18-template-gallery-and-workspace-organization.md) | Proposed scope addition: categorized starter rows, broad industry coverage, blank templates and folders |
| [Demo-template verification corpus](demo-corpus/README.md) | Generated structural samples for every starter and exposed language |
| [E19 identity, organization workspaces and entitlements (proposed)](docs/epic-e19-identity-organization-workspaces-and-entitlements.md) | Proposed scope addition: ordered personal/org template views, workspace isolation, guest access and SSO placeholders |
| [Fictitious identity seed](docs/demo-identity-seed.md) | Explicit local seed for organization admins, members and membership-free individual accounts |
| [Editor usability audit](docs/editor-usability-audit.md) | Interaction findings, fixes and remaining validation boundaries for editor components |
| [Technology stack](docs/tech-stack.md) | Recommended architecture, alternatives, dependency constraints and research sources |
| [Implementation plan](docs/implementation-plan.md) | Epic dependencies, milestones, validation gates and unresolved requirements |
| [Design decisions](docs/design-decisions.md) | Living decision register; proposed choices remain distinct from accepted or implemented choices |
| [Script test matrix](docs/script-test-matrix.md) | Current offline multilingual contract coverage and explicit review gaps |
| [Ingestion contract](docs/ingestion-contract.md) | Upload validation, routing, and versioned PageModel contract |
| [Extraction contract](docs/extraction-contract.md) | Bundled schemas and offline provenance-preserving local extraction |
| [Review contract](docs/review-contract.md) | Revision-safe corrections, review states, and approved-only binding |
| [Template contract](docs/template-contract.md) | Versioned text and repeatable-table blocks used by the editor and renderer |
| [Authentication contract](docs/auth-contract.md) | Local password storage, sessions, CSRF, and review mutation protection |
| [TLS deployment](docs/tls.md) | Reverse-proxy examples and secure-cookie deployment setting |
| [Jobs contract](docs/jobs-contract.md) | Durable render/extraction queue state, leases, polling, and known worker gaps |
| [API reference](docs/api-reference.md) | Generated OpenAPI explorer, render flow and contract verification |
| [Ten-minute quickstart](docs/quickstart.md) | Compose readiness, API explorer and verified candidate render |
| [Local development](docs/local-development.md) | Non-Docker contributor setup and its boundaries |
| [Project instructions](AGENTS.md) | Instructions for future implementation and use of project skills |
| [Contributing](CONTRIBUTING.md) | Contributor workflow and evidence checklist |
| [Code of Conduct](CODE_OF_CONDUCT.md) | Community behavior policy and current governance gap |

Recommended direction: React/TypeScript and ProseMirror for the editor, FastAPI/Python for APIs and processing, PostgreSQL for metadata and durable jobs, local/S3-compatible file storage, and isolated document workers. Compare Chromium and WeasyPrint before choosing the PDF renderer. Use Docling, PaddleOCR and a Tesseract adapter for digitization. Word-to-PDF conversion and the broader runtime depend on resolving the backlog's licence-policy conflict.

The user has started E1 foundation implementation. Run the multilingual rendering spike (E4-01) before selecting a renderer or claiming CPU document-processing acceptance, then complete generation milestone M1 and digitization milestone M2. No calendar commitment is inferred from relative story sizes.

The landing-page My Templates and Organization Templates sections display 12 entries by default. Set the frontend build variable `VITE_TEMPLATE_DISPLAY_LIMIT` to change that limit (values are bounded to 1–100); selecting More templates loads the remaining entries.

## Project skills

Repository-local skills are maintained in `skills/` and explicitly routed by `AGENTS.md`:

- [Document-platform implementation](skills/docplatform-implementation/SKILL.md)
- [Multilingual rendering verification](skills/docplatform-rendering/SKILL.md)
- [Extraction and provenance verification](skills/docplatform-extraction/SKILL.md)

They are ready for explicit file-based use by future project agents. They have not been globally installed or registered in `.agents/skills`; native skill-menu discovery is therefore not claimed. The maintained repository routing makes them usable without changing machine-wide settings. Native discovery, if desired later, uses the locations described in [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Backlog verification

Run `python scripts/extract_backlog.py` to reproduce `docs/epics.md` from the DOCX using Python's standard library. The script checks unique IDs and release totals. The source document remains unchanged. Generated backlog text is separate from proposed architecture and delivery refinements.
