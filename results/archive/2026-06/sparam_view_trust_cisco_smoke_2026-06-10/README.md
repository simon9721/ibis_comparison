# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 22:58:03

## Summary

- Candidate metric rows: 6
- Selected channels: 3
- Independent PASS/WARN/FAIL: 0 / 3 / 0
- RX-through PASS/WARN/FAIL: 0 / 3 / 0
- Reflection PASS/WARN/FAIL: 0 / 0 / 3
- Full-model PASS/WARN/FAIL: 0 / 3 / 0
- Failed channels: 0
- HSPICE correlation rows: 3
- Successful HSPICE correlations: 3
- HSPICE is optional audit data only; it is not used by `qualify` model selection.

## Key Files

- `manifest.csv`: Touchstone inventory
- `metrics.csv`: HSPICE-independent fit/passivity metrics
- `ngspice_smoke.csv`: ngspice transient smoke metrics
- `ranking.csv`: selected model per channel
- `selected_models/`: stable copies of selected ngspice-ready models
- `selected_models/rx/`: scoped RX-through selected models when available
- `selected_models/reflection/`: scoped reflection selected models when available
- `selected_models/full/`: full multiport selected models when independently PASS
- `hspice_correlation.csv`: optional HSPICE native S-element audit metrics
- `calibration_summary.csv`: optional independent-trust vs HSPICE-audit confusion matrix
- `view_trust_summary.csv`: RX/reflection/full readiness counts
- `view_calibration_summary.csv`: optional view-level false-PASS calibration
- `candidate_family_summary.csv`: candidate-family selection and audit outcomes
- `warning_audit_summary.csv`: warning reason vs HSPICE audit outcomes
- `audit_overlay_groups/`: optional grouped HSPICE-vs-ngspice overlay PDFs

## Candidate Families

- `reduced_4p_reflection`: PASS `0`, WARN `3`, FAIL `0`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `3`, FAIL `0`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `3`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `3`, FAIL `0`

## Path-Level Readiness

- `rx`: ready `0`, warn `3`, fail `0`, selected models `3`, HSPICE P/W/F/E `0/3/0/0`
- `reflection`: ready `0`, warn `0`, fail `3`, selected models `0`, HSPICE P/W/F/E `3/0/0/0`
- `full_model`: ready `0`, warn `3`, fail `0`, selected models `0`, HSPICE P/W/F/E `0/3/0/0`

## False-PASS Headline

- Split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- Split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## View False-PASS Headline

- View `rx`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## Family Audit Outcomes

- `reduced_4p_reflection`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `3`, independent P/W/F `0/3/0`, HSPICE P/W/F/E `0/3/0/0`

## Warning Audit Outcomes

- `reduced_4p_not_full_matrix`: channels `3`, audit rows `3`, HSPICE P/W/F/E `0/3/0/0`
- `rx_low_swing_metric_floor`: channels `3`, audit rows `3`, HSPICE P/W/F/E `0/3/0/0`
- `rx_settling_margin`: channels `3`, audit rows `3`, HSPICE P/W/F/E `0/3/0/0`
- `threshold_delay_confidence_low`: channels `3`, audit rows `3`, HSPICE P/W/F/E `0/3/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `3`, audit rows `3`, HSPICE P/W/F/E `0/3/0/0`

## Selected Models

- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_view_trust_cisco_smoke_2026-06-10/selected_models/Ch10_35_5F3N_f1_49905299.sp`
- `Ch10_35_5F3N_f2_f23c49e2`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `5.251e-05`, max SV `3.318e-05`, model `results/sparam_view_trust_cisco_smoke_2026-06-10/selected_models/Ch10_35_5F3N_f2_f23c49e2.sp`
- `Ch10_35_5F3N_f3_81049e25`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0005233`, max SV `9.219e-05`, model `results/sparam_view_trust_cisco_smoke_2026-06-10/selected_models/Ch10_35_5F3N_f3_81049e25.sp`

## HSPICE Calibration

- Split `all`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `all`, independent `WARN`: HSPICE pass `0`, warn `3`, fail `0`, error `0`, total `3`
- Split `all`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `WARN`: HSPICE pass `0`, warn `3`, fail `0`, error `0`, total `3`
- Split `calibration`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
