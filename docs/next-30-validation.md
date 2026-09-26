# Next 30 story validation matrix

Date: 2026-09-26

This tranche records the next 30 evidence-bounded implementation slices. `partial` is intentional: it means the local contract or implementation exists, while the source story still requires an explicitly named external or empirical acceptance gate.

| Story IDs | Delivered slice | Evidence | Residual gate |
| --- | --- | --- | --- |
| E1-06–E1-12 | CPU runtime, migration, Helm, offline bundle, backup/restore, retention and local-development contracts | `docs/next-20-validation.md`, `charts/`, `scripts/`, repository tests | Live prior-release, cluster, disaster-recovery, scheduled-production and fresh-machine evidence |
| E2-04 | QR, Code 128 and EAN-13 bounded editor/preview/PDF path | `backend/app/codes.py`, renderer and browser/PDF tests | Device scanner and final-engine fidelity review |
| E2-07–E2-10 | Page-flow controls, locale propagation, multilingual entry foundations, undo/redo, copy/paste, alignment and guides | `backend/app/rendering.py`, `frontend/src/main.tsx`, `frontend/tests/foundation.spec.ts` | Full pagination corpus, IME/selection corpus and native-reader review |
| E2-11–E2-12 | Reusable components and bounded brand-theme tokens | `backend/app/components.py`, editor and component tests | Cross-template governance and broader typography review |
| E2-13 | Named/focusable editor controls and keyboard selection path | browser accessibility tests and editor styles | WCAG 2.2 AA and assistive-technology audit |
| E2-14–E2-16 | Bounded charts, locked PDF backgrounds, anchors and TOC links | renderer, PDF and browser tests | Embedded-font/chart review, broader page geometry, pagination-derived numbers and native-reader review |
| E3-08–E3-09 | Shell-free template sync contract and review/publish boundary documentation | `scripts/sync_templates.py`, governance routes/tests, implementation docs | Live repository CI, conflict policy and multi-user approval evidence |
| E4-01–E4-05 | Repeatable candidate comparison, script detection, fallback stacks and locale/layout contracts | `scripts/compare_render_candidates.py`, `scripts/render_spike.py`, renderer tests | Second engine, native-reader grades, shaping/bidi/line-break visual approval |
| E4-06–E4-10 | Custom-font/source diagnostics, missing-glyph warnings, deterministic matrix page, locale formatting and translation files | renderer diagnostics, script matrix, starter fixtures and tests | Reviewed font licences, real embedding/subsetting and native-reader/visual regression evidence |

The PDF image-alignment defect is covered by DD-262 and the renderer regression in `backend/tests/test_template_logic.py`. The local editor now exposes image alignment and shows image blocks as images. No row above is promoted to full source-story acceptance without its residual gate.
