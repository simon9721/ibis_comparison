# ngspice S-parameter Trust Workflow

Generated: 2026-06-10 00:29:27

## Summary

- Candidate metric rows: 6
- Selected channels: 2
- Independent PASS/WARN/FAIL: 0 / 2 / 0
- RX-through PASS/WARN/FAIL: 0 / 2 / 0
- RX voltage-shape PASS/WARN/FAIL: 0 / 2 / 0
- RX timing PASS/WARN/FAIL: 0 / 2 / 0
- Reflection PASS/WARN/FAIL: 0 / 0 / 2
- Full-model PASS/WARN/FAIL: 0 / 2 / 0
- Failed channels: 0
- HSPICE correlation rows: 0
- Successful HSPICE correlations: 0
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

- `reduced_4p_reflection_s11_rc`: PASS `0`, WARN `2`, FAIL `0`, unclassified `0`
- `reduced_4p_rx_delayeq_rc_ring`: PASS `0`, WARN `2`, FAIL `0`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `2`, FAIL `0`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `2`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `2`, FAIL `0`

## Path-Level Readiness

- `rx_voltage_shape`: pass `0`, warn `2`, fail `0`
- `rx_timing`: pass `0`, warn `2`, fail `0`
- `rx_voltage_shape`: ready `0`, warn `2`, fail `0`, selected models `2`, HSPICE P/W/F/E `0/0/0/0`
- `rx_timing`: ready `0`, warn `2`, fail `0`, selected models `2`, HSPICE P/W/F/E `0/0/0/0`
- `rx`: ready `0`, warn `2`, fail `0`, selected models `2`, HSPICE P/W/F/E `0/0/0/0`
- `reflection`: ready `0`, warn `0`, fail `2`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`
- `full_model`: ready `0`, warn `2`, fail `0`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`

## Family Audit Outcomes

- `reduced_4p_reflection_s11_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_delayeq_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `2`, independent P/W/F `0/2/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `reduced_4p_not_full_matrix`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_low_swing_metric_floor`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_settling_margin`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `threshold_delay_confidence_low`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, RX-shape `WARN`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_rx_trust_v2_cisco_smoke_2026-06-10/selected_models/Ch10_35_5F3N_f1_49905299.sp`
- `Ch10_35_5F3N_f2_f23c49e2`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, RX-shape `WARN`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `5.251e-05`, max SV `3.318e-05`, model `results/sparam_rx_trust_v2_cisco_smoke_2026-06-10/selected_models/Ch10_35_5F3N_f2_f23c49e2.sp`
