# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v1_2026-06-12_cisco_smoke`

## Summary

- Candidate rows: `1`
- Ranked channels: `1`
- ngspice smoke rows: `0`
- HSPICE audit rows: `0`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `FAIL`: `1`

## Candidate Outcomes

- `vector_3r3c`: `1` rows

## Preprocessing Outcomes

- `raw`: `1` candidate rows, `0` selected

## Passivity Enforcement

- `False`: `1` candidate rows, `0` selected

## HSPICE Calibration

- No HSPICE audit data yet.

## Selected Models

- `Ch10_35_5F3N_f4_cdb7d8f1`: `` (FAIL), preprocess `None`, order `None`, model `None`

## Interpretation Checklist

- `FULL_MODEL_READY` requires a selected vector-fit model with independent PASS after smoke checks.
- `dc_hold` indicates the fit used a synthetic DC point copied from the first measured frequency.
- `freq_trim_0p9` and `freq_trim_0p75` fit on trimmed high-frequency data but are scored on the original grid.
- Reduced-model columns, when present, are baseline context only and do not affect vector-fit selection.

## Key Files

- `manifest.csv`
- `vf_candidates.csv`
- `vf_metrics.csv`
- `vf_ranking.csv`
- `vf_ngspice_smoke.csv`
- `vf_hspice_correlation.csv`
- `vf_calibration_summary.csv`
- `selected_vector_models/`
- `plots/frequency_fit/`
- `plots/passivity/`
- `plots/hspice_overlays/`
