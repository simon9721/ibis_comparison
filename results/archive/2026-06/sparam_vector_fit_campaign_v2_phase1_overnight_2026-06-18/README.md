# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18`

## Summary

- Candidate rows: `5970`
- Ranked channels: `9`
- ngspice smoke rows: `72`
- HSPICE audit rows: `54`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `FAIL`: `5`
- `WARN`: `4`

## Independent View Classes

- full model: FAIL `5`, WARN `4`
- RX shape: FAIL `5`, WARN `4`
- RX timing: FAIL `5`, WARN `4`
- reflection/TX: FAIL `5`, WARN `4`

## Candidate Outcomes

- `vector_3r3c`: `908` rows, P/W/F `27/120/761`, selected `1`
- `vector_5r5c`: `908` rows, P/W/F `26/114/768`, selected `0`
- `vector_8r8c`: `852` rows, P/W/F `36/67/749`, selected `0`
- `vector_12r12c`: `740` rows, P/W/F `35/61/644`, selected `2`
- `vector_0r4c`: `454` rows, P/W/F `9/45/400`, selected `0`
- `vector_2r6c`: `454` rows, P/W/F `0/0/454`, selected `0`
- `vector_4r8c`: `438` rows, P/W/F `9/63/366`, selected `0`
- `auto_fit_low_order`: `358` rows, P/W/F `9/18/331`, selected `0`
- `auto_fit_high_order`: `334` rows, P/W/F `18/9/307`, selected `2`
- `auto_fit_default`: `262` rows, P/W/F `9/0/253`, selected `1`
- `auto_fit_tight`: `262` rows, P/W/F `9/0/253`, selected `0`

## Preprocessing Outcomes

- `freq_trim_0p9`: `1167` candidate rows, P/W/F `0/150/1017`, selected `0`
- `raw`: `1151` candidate rows, P/W/F `187/54/910`, selected `6`
- `freq_trim_0p95`: `1143` candidate rows, P/W/F `0/194/949`, selected `0`
- `hf_rolloff_20db_dec`: `1031` candidate rows, P/W/F `0/0/1031`, selected `0`
- `dc_hold`: `879` candidate rows, P/W/F `0/99/780`, selected `0`
- `hf_hold`: `599` candidate rows, P/W/F `0/0/599`, selected `0`

## Passivity Enforcement

- `True`: `5160` candidate rows, P/W/F `168/448/4544`, selected `2`
- `False`: `810` candidate rows, P/W/F `19/49/742`, selected `4`

## Best Settings Observed

- `vector_12r12c` preprocess `raw`, spacing `lin`, enforced `True`: selected `2`
- `auto_fit_high_order` preprocess `raw`, spacing ``, enforced `False`: selected `2`
- `vector_3r3c` preprocess `raw`, spacing `lin`, enforced `False`: selected `1`
- `auto_fit_default` preprocess `raw`, spacing ``, enforced `False`: selected `1`

## Reduced Baseline Context

- reduced baseline RX status `RX_WARN_VOLTAGE_MARGIN`: `3` channels
- reduced baseline RX status `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`: `2` channels

## HSPICE Calibration

- split `all`, independent `PASS`: HSPICE P/W/F/E `20/8/8/0`, total `36`, false-pass `0.4444444444444444`
- split `all`, independent `WARN`: HSPICE P/W/F/E `6/2/4/0`, total `12`, false-pass ``
- split `all`, independent `FAIL`: HSPICE P/W/F/E `4/2/0/0`, total `6`, false-pass ``
- split `calibration`, independent `PASS`: HSPICE P/W/F/E `16/6/8/0`, total `30`, false-pass `0.4666666666666667`
- split `calibration`, independent `WARN`: HSPICE P/W/F/E `6/2/4/0`, total `12`, false-pass ``
- split `calibration`, independent `FAIL`: HSPICE P/W/F/E `2/1/0/0`, total `3`, false-pass ``
- split `holdout`, independent `PASS`: HSPICE P/W/F/E `4/2/0/0`, total `6`, false-pass `0.3333333333333333`
- split `holdout`, independent `WARN`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `FAIL`: HSPICE P/W/F/E `2/1/0/0`, total `3`, false-pass ``

## Independent Edge Bandwidth Readiness

- Edge bandwidth rule: required bandwidth = `0.35 / edge_time`; PASS ratio >= `1`, WARN ratio >= `0.25`.
- `5 ps` requires about `70 GHz`: FAIL `6`, WARN `3`
- `50 ps` requires about `7 GHz`: PASS `7`, WARN `2`
- `500 ps` requires about `0.7 GHz`: PASS `9`

## Edge Bandwidth Vs HSPICE Audit

- edge `5.0 ps`, bandwidth `FAIL`: all audited HSPICE P/W/F/E `0/12/6/0`, selected-only P/W/F/E `0/4/2/0`
- edge `50.0 ps`, bandwidth `PASS`: all audited HSPICE P/W/F/E `12/0/0/0`, selected-only P/W/F/E `4/0/0/0`
- edge `50.0 ps`, bandwidth `WARN`: all audited HSPICE P/W/F/E `0/0/6/0`, selected-only P/W/F/E `0/0/2/0`
- edge `500.0 ps`, bandwidth `PASS`: all audited HSPICE P/W/F/E `18/0/0/0`, selected-only P/W/F/E `6/0/0/0`

## Edge-Adjusted Independent Calibration

- edge `all`, adjusted independent PASS: HSPICE P/W/F/E `20/0/0/0`, total `20`, false-pass `0.0`
- edge `50`, adjusted independent PASS: HSPICE P/W/F/E `8/0/0/0`, total `8`, false-pass `0.0`
- edge `500`, adjusted independent PASS: HSPICE P/W/F/E `12/0/0/0`, total `12`, false-pass `0.0`

## Audit Outcomes By Edge

- edge `5.0 ps`: total `18`, HSPICE P/W/F/E `0/12/6/0`
- edge `50.0 ps`: total `18`, HSPICE P/W/F/E `12/0/6/0`
- edge `500.0 ps`: total `18`, HSPICE P/W/F/E `18/0/0/0`

## Selected Models

- `Clarity_example_acf20e4a`: `raw_vector_3r3c_lin` (WARN), preprocess `raw`, order `9`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/Clarity_example_acf20e4a.sp`
- `ntwk2_e1c16499`: `raw_vector_12r12c_lin_enforced_s2000_original_pdc1` (WARN), preprocess `raw`, order `36`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/ntwk2_e1c16499.sp`
- `ntwk3_ad74ab42`: `raw_auto_fit_high_order` (FAIL), preprocess `raw`, order `6`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/ntwk3_ad74ab42.sp`
- `ntwk2_24638a5f`: `raw_vector_12r12c_lin_enforced_s2000_original_pdc1` (WARN), preprocess `raw`, order `36`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/ntwk2_24638a5f.sp`
- `ntwk3_8f8a2430`: `raw_auto_fit_high_order` (FAIL), preprocess `raw`, order `6`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/ntwk3_8f8a2430.sp`
- `Clarity_example_Fitted_55b55a71`: `raw_auto_fit_default` (WARN), preprocess `raw`, order `7`, model `results/sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18/selected_vector_models/Clarity_example_Fitted_55b55a71.sp`
- `Ch10_35_5F3N_f4_fc94db99`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_t_d3c7dddc`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch3_17_5F3N_f3_c08ef229`: `` (FAIL), preprocess ``, order ``, model ``

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
- `vf_selected_edge_readiness.csv`
- `vf_edge_bandwidth_calibration.csv`
- `vf_edge_adjusted_calibration_summary.csv`
- `vf_edge_adjusted_hspice_correlation.csv`
- `selected_vector_models/`
- `plots/frequency_fit/`
- `plots/passivity/`
- `plots/edge_bandwidth/`
- `plots/hspice_overlays/`
- `plots/side_overlays/`
- `share_pack/`
