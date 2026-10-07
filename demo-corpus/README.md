# Demo-template verification corpus

This corpus contains deterministic JSON definitions and rendered HTML samples for every homepage starter and every language exposed by that starter. The samples verify that a user can generate a populated document without editing the core template first.

Regenerate it from the repository root:

```powershell
python scripts/build_demo_corpus.py
```

`generated/manifest.json` records the catalog and document counts, category, language, scripts, and any missing bindings or translations. The generated HTML is a structural smoke corpus; it is not legal, tax, investment, insurance, employment, or compliance advice, and it does not replace native-reader or industry-review sign-off.
