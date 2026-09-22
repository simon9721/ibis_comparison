# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v1_2026-06-12`

## Summary

- Candidate rows: `6`
- Ranked channels: `3`
- ngspice smoke rows: `12`
- HSPICE audit rows: `3`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `FAIL`: `2`
- `WARN`: `1`

## Candidate Outcomes

- `vector_3r3c`: `6` rows, P/W/F `1/0/5`, selected `1`

## Preprocessing Outcomes

- `raw`: `3` candidate rows, P/W/F `1/0/2`, selected `1`
- `dc_hold`: `3` candidate rows, P/W/F `0/0/3`, selected `0`

## Passivity Enforcement

- `False`: `6` candidate rows, P/W/F `1/0/5`, selected `1`

## Best Settings Observed

- `vector_3r3c` preprocess `raw`, spacing `lin`, enforced `False`: selected `1`

## Reduced Baseline Context

- No reduced baseline match found for these channel paths.

## HSPICE Calibration

- split `all`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `all`, independent `WARN`: HSPICE P/W/F/E `1/0/2/0`, total `3`, false-pass ``
- split `all`, independent `FAIL`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `calibration`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `calibration`, independent `WARN`: HSPICE P/W/F/E `1/0/2/0`, total `3`, false-pass ``
- split `calibration`, independent `FAIL`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `WARN`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `FAIL`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``

## Audit Outcomes By Edge

- edge `5.0 ps`: total `1`, HSPICE P/W/F/E `0/0/1/0`
- edge `50.0 ps`: total `1`, HSPICE P/W/F/E `0/0/1/0`
- edge `500.0 ps`: total `1`, HSPICE P/W/F/E `1/0/0/0`

## Selected Models

- `Ch10_35_5F3N_f4_cdb7d8f1`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch3_17_5F3N_f3_a34c32c3`: `` (FAIL), preprocess ``, order ``, model ``
- `Clarity_example_4ef781de`: `raw_vector_3r3c_lin` (WARN), preprocess `raw`, order `9`, model `results/sparam_vector_fit_campaign_v1_2026-06-12/selected_vector_models/Clarity_example_4ef781de.sp`

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
