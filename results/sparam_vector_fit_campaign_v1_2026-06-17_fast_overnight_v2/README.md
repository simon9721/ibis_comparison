# scikit-rf Vector Fitting Campaign

Study folder: `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2`

## Summary

- Candidate rows: `1126`
- Ranked channels: `40`
- ngspice smoke rows: `72`
- HSPICE audit rows: `18`
- HSPICE is audit-only; vector-fit selection is based on independent fit/smoke metrics.

## Selected Candidate Classes

- `FAIL`: `36`
- `WARN`: `4`

## Candidate Outcomes

- `vector_3r3c`: `291` rows, P/W/F `6/8/277`, selected `1`
- `vector_8r8c`: `283` rows, P/W/F `8/4/271`, selected `0`
- `vector_5r5c`: `282` rows, P/W/F `6/8/268`, selected `4`
- `auto_fit_default`: `135` rows, P/W/F `2/0/133`, selected `1`
- `auto_fit_tight`: `135` rows, P/W/F `2/0/133`, selected `0`

## Preprocessing Outcomes

- `raw`: `598` candidate rows, P/W/F `24/4/570`, selected `6`
- `dc_hold`: `528` candidate rows, P/W/F `0/16/512`, selected `0`

## Passivity Enforcement

- `False`: `640` candidate rows, P/W/F `11/10/619`, selected `6`
- `True`: `486` candidate rows, P/W/F `13/10/463`, selected `0`

## Best Settings Observed

- `vector_5r5c` preprocess `raw`, spacing `lin`, enforced `False`: selected `2`
- `vector_5r5c` preprocess `raw`, spacing `log`, enforced `False`: selected `2`
- `vector_3r3c` preprocess `raw`, spacing `lin`, enforced `False`: selected `1`
- `auto_fit_default` preprocess `raw`, spacing ``, enforced `False`: selected `1`

## Reduced Baseline Context

- reduced baseline RX status `WARN`: `12` channels
- reduced baseline RX status `RX_WARN_VOLTAGE_MARGIN`: `3` channels
- reduced baseline RX status `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`: `1` channels

## HSPICE Calibration

- split `all`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `all`, independent `WARN`: HSPICE P/W/F/E `6/2/4/0`, total `12`, false-pass ``
- split `all`, independent `FAIL`: HSPICE P/W/F/E `4/2/0/0`, total `6`, false-pass ``
- split `calibration`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `calibration`, independent `WARN`: HSPICE P/W/F/E `6/2/4/0`, total `12`, false-pass ``
- split `calibration`, independent `FAIL`: HSPICE P/W/F/E `2/1/0/0`, total `3`, false-pass ``
- split `holdout`, independent `PASS`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `WARN`: HSPICE P/W/F/E `0/0/0/0`, total `0`, false-pass ``
- split `holdout`, independent `FAIL`: HSPICE P/W/F/E `2/1/0/0`, total `3`, false-pass ``

## Audit Outcomes By Edge

- edge `5.0 ps`: total `6`, HSPICE P/W/F/E `0/4/2/0`
- edge `50.0 ps`: total `6`, HSPICE P/W/F/E `4/0/2/0`
- edge `500.0 ps`: total `6`, HSPICE P/W/F/E `6/0/0/0`

## Selected Models

- `Agilent_E5071B_4f4fd1d7`: `` (FAIL), preprocess ``, order ``, model ``
- `Clarity_example_acf20e4a`: `raw_vector_3r3c_lin` (WARN), preprocess `raw`, order `9`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/Clarity_example_acf20e4a.sp`
- `cst_example_4ports_e82e6e67`: `` (FAIL), preprocess ``, order ``, model ``
- `designer_variable_coupler_ideal_20deg_e31d0708`: `` (FAIL), preprocess ``, order ``, model ``
- `designer_variable_coupler_ideal_75deg_50e48e76`: `` (FAIL), preprocess ``, order ``, model ``
- `fet_7e5200ad`: `` (FAIL), preprocess ``, order ``, model ``
- `hfss_twoport_e975fe9f`: `` (FAIL), preprocess ``, order ``, model ``
- `LFCN-2352__Plus125degC_4793e65c`: `` (FAIL), preprocess ``, order ``, model ``
- `LFCN-2352__Plus25degC_d04142bc`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk1_f450e450`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk2_e1c16499`: `raw_vector_5r5c_lin` (WARN), preprocess `raw`, order `15`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/ntwk2_e1c16499.sp`
- `ntwk3_ad74ab42`: `raw_vector_5r5c_log` (FAIL), preprocess `raw`, order `15`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/ntwk3_ad74ab42.sp`
- `ntwk4_806cfc7d`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk4_n_6d3c414e`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk_arbitrary_frequency_3e8760a8`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk_noise_65eeb4e4`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk_noise_interp_a132609e`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk1_e20029da`: `` (FAIL), preprocess ``, order ``, model ``
- `ntwk2_24638a5f`: `raw_vector_5r5c_lin` (WARN), preprocess `raw`, order `15`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/ntwk2_24638a5f.sp`
- `ntwk3_8f8a2430`: `raw_vector_5r5c_log` (FAIL), preprocess `raw`, order `15`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/ntwk3_8f8a2430.sp`
- `RS_ZNB8_23e14c3f`: `` (FAIL), preprocess ``, order ``, model ``
- `RS_ZVR_1.20_beta_f_6cd9e598`: `` (FAIL), preprocess ``, order ``, model ``
- `thru_a0b4754f`: `` (FAIL), preprocess ``, order ``, model ``
- `Clarity_example_Fitted_55b55a71`: `raw_auto_fit_default` (WARN), preprocess `raw`, order `7`, model `results/sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2/selected_vector_models/Clarity_example_Fitted_55b55a71.sp`
- `Ch10_35_5F3N_f1_49905299`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_f2_f23c49e2`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_f3_81049e25`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_f4_fc94db99`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_f5_3a904f20`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_n1_8e377765`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_n2_b3e24295`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_n3_a9ef8f2b`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch10_35_5F3N_t_d3c7dddc`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_f1_8f9c2982`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_f2_47dc69c2`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_f3_ab427591`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_f4_dfb4f0b9`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_f5_30ca600f`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_n1_9a8781a5`: `` (FAIL), preprocess ``, order ``, model ``
- `Ch1_10_5F3N_n2_a8ccad10`: `` (FAIL), preprocess ``, order ``, model ``

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
