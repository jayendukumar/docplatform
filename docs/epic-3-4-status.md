# Epic 3 and Epic 4 implementation status

Date: 2026-09-24

This implementation covers the executable MVP contract slice for E3 and E4. It does not claim the full source epics are complete.

The source-story status overlay is now authoritative for the individual rows. E3 Must contract stories are marked implemented where their API/UI and validation evidence meets the bounded acceptance boundary. E4 remains intentionally mixed: E4-10's translation contract is implemented, while native rendering, shaping, font, line-breaking and visual-regression stories remain partial pending the evidence listed below.

## Implemented

- E3-01: folder, tag and name/tag/folder search on the template collection API.
- E3-02: draft versions are distinct from the published version; default reads and renders use the published pointer.
- E3-03: immutable version rows, history, and restore-as-new-version.
- E3-04: duplicate creates a new template and copies the portable definition.
- E3-05: starter catalog endpoint with four starter families and three-language selections.
- E3-06: schema derivation from bounded `{{dot.path}}` bindings.
- E3-07: deterministic portable ZIP export/import with a manifest and definition.
- E4-02 through E4-05 foundations: script detection, fallback-stack reporting, escaped mixed-script HTML, `dir=auto`, and locale-aware basic number formatting.
- E4-07 foundation: render responses include scripts, font stacks, and missing-glyph diagnostic fields.
- E4-09 foundation: locale-aware numeric formatting in the renderer contract.
- E4-10: bounded per-template translation maps, locale selection, deterministic fallback, and missing-key diagnostics.

The E5 contract slice now also provides bounded dot-path bindings, loops, boolean/comparison conditions, locale-aware formatters, schema validation and explicit missing-field policies. Evaluation limits are enforced for nesting, expanded blocks and loop items. This is a contract foundation, not completion of E5's approved extraction binding or aggregate/remote-data stories.

## Explicitly pending

E4-01 remains `pending-native-review`: the repository contains a repeatable `scripts/render_spike.py`, but no native-reader grades or second candidate engine result have been produced. The renderer is therefore `deterministic-html-0.1` and is not a final PDF engine. Noto font files are not bundled yet; CSS fallback names are reported but do not prove glyph coverage. E4-06 and E4-08 still need font assets, visual baselines, and reviewed fixtures; E4-10's translation contract is implemented, while native shaping and final-output parity remain separate gates. E3 R2 governance stories (review approval, promotion, access policies, analytics, archive and bulk undo) are not included.

## Validation evidence

- `python -m compileall -q backend/app scripts/render_spike.py` passed.
- `python scripts/render_spike.py` passed and reported Arabic, Hebrew, Devanagari, Tamil, Thai and CJK script detection with `pending-native-review`.
- `backend/tests/test_epic34.py` lifecycle, bundle, escaping and script contract coverage passed as part of `47 passed, 5 skipped`; the five skipped tests require an explicitly configured PostgreSQL test database.
- `npm run build` passed after installing the pinned frontend lockfile. Targeted Ruff checks passed for the new Epic 3/4 test file; the full repository lint remains non-zero on existing and newly exposed style/exception findings.
- Installation-time licence flags are recorded in [dependency review](dependencies.md); no compliance approval is claimed.
- `backend/.venv/Scripts/python.exe -m pytest -q tests/test_template_logic.py` passed (`5 passed`). The targeted E3/E4 integration run was partially blocked by the existing Windows pytest temp-directory permission issue described in DD-029.
