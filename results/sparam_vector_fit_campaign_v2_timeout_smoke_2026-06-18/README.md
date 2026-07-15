# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v2_timeout_smoke_2026-06-18`

## Summary

- Candidate rows: `1`
- Ranked channels: `1`
- ngspice smoke rows: `0`
- HSPICE audit rows: `0`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `FAIL`: `1`

## Candidate Outcomes

- `vector_3r3c`: `1` rows, P/W/F `0/0/1`, selected `0`

## Preprocessing Outcomes

- `raw`: `1` candidate rows, P/W/F `0/0/1`, selected `0`

## Passivity Enforcement

- `False`: `1` candidate rows, P/W/F `0/0/1`, selected `0`

## Best Settings Observed

- No vector-fit candidate was selected.

## Reduced Baseline Context

- reduced baseline RX status `RX_WARN_VOLTAGE_MARGIN`: `1` channels

## HSPICE Calibration

- No HSPICE audit data yet.

## Audit Outcomes By Edge

- No HSPICE audit data yet.

## Selected Models

- `Clarity_example_acf20e4a`: `` (FAIL), preprocess `None`, order `None`, model `None`

## Interpretation Checklist

- `FULL_MODEL_READY` requires a selected vector-fit model with independent PASS after smoke checks.
- `dc_hold` indicates the fit used a synthetic DC point copied from the first measured frequency.
- `freq_trim_0p9` and `freq_trim_0p75` fit on trimmed high-frequency data but are scored on the original grid.
- Reduced-model columns, when present, are baseline context only and do not affect vector-fit selection.

## Reproduction Commands

Pilot command used for this folder:

```powershell
py -3.14 scripts/run_sparam_vector_fit_campaign.py fit `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `
  --skrf-target "$env:TEMP\ibis_skrf_target" `
  --no-skrf-tests `
  --no-repo-local `
  --extra-touchstone-dir results/converted_sp_comparison_2026-06-12/inputs `
  --candidates vector_3r3c_lin `
  --preprocess raw,dc_hold `
  --dense-samples 101 `
  --skip-passivity-enforcement
```

Full campaign template:

```powershell
py -3.14 scripts/run_sparam_vector_fit_campaign.py fit `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `
  --skrf-target "$env:TEMP\ibis_skrf_target" `
  --skrf-tests-dir results/sparam_conversion_quality_2026-06-08/inputs/skrf_tests `
  --extra-touchstone-dir hspice/sparam `
  --candidate-profile full `
  --preprocess raw,dc_hold,freq_trim_0p9,freq_trim_0p75 `
  --dense-samples 501
```

After fitting, run:

```powershell
py -3.14 scripts/run_sparam_vector_fit_campaign.py smoke-ngspice `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12

py -3.14 scripts/run_sparam_vector_fit_campaign.py audit-hspice `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `
  --max-channels 20 `
  --resume
```

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
