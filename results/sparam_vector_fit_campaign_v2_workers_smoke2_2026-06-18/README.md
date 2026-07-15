# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v2_workers_smoke2_2026-06-18`

## Summary

- Candidate rows: `2`
- Ranked channels: `1`
- ngspice smoke rows: `0`
- HSPICE audit rows: `0`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `PASS`: `1`

## Independent View Classes

- full model: PASS `1`
- RX shape: PASS `1`
- RX timing: PASS `1`
- reflection/TX: PASS `1`

## Candidate Outcomes

- `vector_5r5c`: `1` rows, P/W/F `0/0/1`, selected `0`
- `vector_3r3c`: `1` rows, P/W/F `1/0/0`, selected `1`

## Preprocessing Outcomes

- `raw`: `2` candidate rows, P/W/F `1/0/1`, selected `1`

## Passivity Enforcement

- `False`: `2` candidate rows, P/W/F `1/0/1`, selected `1`

## Best Settings Observed

- `vector_3r3c` preprocess `raw`, spacing `lin`, enforced `False`: selected `1`

## Reduced Baseline Context

- reduced baseline RX status `RX_WARN_VOLTAGE_MARGIN`: `1` channels

## HSPICE Calibration

- No HSPICE audit data yet.

## Audit Outcomes By Edge

- No HSPICE audit data yet.

## Selected Models

- `Clarity_example_acf20e4a`: `raw_vector_3r3c_lin` (PASS), preprocess `raw`, order `9`, model `results/sparam_vector_fit_campaign_v2_workers_smoke2_2026-06-18/selected_vector_models/Clarity_example_acf20e4a.sp`

## Interpretation Checklist

- `FULL_MODEL_READY` requires a selected vector-fit model with independent PASS after smoke checks.
- `dc_hold` indicates the fit used a synthetic DC point copied from the first measured frequency.
- `freq_trim_*`, resampling, and high-frequency extension modes fit modified data but are scored on the original grid.
- `*_propdiag` candidates are diagnostic-only and cannot be selected as final deliverables.
- `TIMEOUT` rows mean one candidate exceeded `--candidate-timeout-s`; the campaign continued.
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
  --phase-profile phase1 `
  --candidate-timeout-s 900 `
  --passivity-strategy near-pass `
  --enforce-samples-list 200,2000,20000 `
  --enforce-fmax-list original,2x,high `
  --enforce-preserve-dc-list true,false `
  --dense-samples 501 `
  --resume
```

After fitting, run:

```powershell
py -3.14 scripts/run_sparam_vector_fit_campaign.py smoke-ngspice `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12

py -3.14 scripts/run_sparam_vector_fit_campaign.py audit-hspice `
  --study-dir results/sparam_vector_fit_campaign_v1_2026-06-12 `
  --audit-top-k 3 `
  --max-channels 20 `
  --resume
```

## Key Files

- `manifest.csv`
- `vf_candidate_grid.csv`
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
- `plots/side_overlays/`
- `share_pack/`
