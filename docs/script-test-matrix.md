# Script test matrix

This page is generated from the deterministic offline report produced by `scripts/render_spike.py`. It is not native-reader approval and does not establish final PDF-engine selection.

| Script family | Reported script | Deterministic result | Status |
| --- | --- | --- | --- |
| Arabic | `arabic` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Hebrew | `hebrew` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Devanagari | `devanagari` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Tamil | `tamil` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Thai | `thai` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Chinese | `cjk` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Japanese | `cjk` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |
| Korean | `korean` | Script detection, escaped HTML and fallback-stack report | Contract covered; native review pending |

## Rebuild the contract report

```powershell
python scripts/render_spike.py > artifacts/script-matrix.json
python scripts/build_script_matrix_page.py artifacts/script-matrix.json > artifacts/script-test-matrix.md
```

The report is intentionally offline and deterministic. Before E4-01 can be accepted, add a second candidate engine, capture exact engine/font/environment manifests, produce visual baselines, and obtain native-reader grades. Do not convert a passing script-detection check into a glyph, shaping, line-breaking, or PDF claim.

## CI contract

`.github/workflows/script-matrix.yml` rebuilds the JSON report and this page, then checks the generated page against the checked-in documentation. The gate is deterministic contract coverage for E4-08/E14-03, not visual regression: no native font rendering, screenshot baseline, or native-reader approval is claimed yet.
