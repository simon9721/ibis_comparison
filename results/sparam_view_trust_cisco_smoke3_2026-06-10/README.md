# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 23:02:33

## Summary

- Candidate metric rows: 2
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- RX-through PASS/WARN/FAIL: 0 / 1 / 0
- Reflection PASS/WARN/FAIL: 0 / 0 / 1
- Full-model PASS/WARN/FAIL: 0 / 1 / 0
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

- `reduced_4p_reflection`: PASS `0`, WARN `1`, FAIL `0`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `1`, FAIL `0`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Path-Level Readiness

- `rx`: ready `0`, warn `1`, fail `0`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`
- `reflection`: ready `0`, warn `0`, fail `1`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`
- `full_model`: ready `0`, warn `1`, fail `0`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`

## Family Audit Outcomes

- `reduced_4p_reflection`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `reduced_4p_not_full_matrix`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_low_swing_metric_floor`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_settling_margin`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `threshold_delay_confidence_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_view_trust_cisco_smoke3_2026-06-10/selected_models/Ch10_35_5F3N_f1_49905299.sp`
