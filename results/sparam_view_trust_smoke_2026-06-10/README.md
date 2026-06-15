# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 22:49:47

## Summary

- Candidate metric rows: 11
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- RX-through PASS/WARN/FAIL: 0 / 1 / 3
- Reflection PASS/WARN/FAIL: 0 / 0 / 4
- Full-model PASS/WARN/FAIL: 0 / 1 / 3
- Failed channels: 3
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

- `full_vector_fit`: PASS `0`, WARN `1`, FAIL `1`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_reflection`: PASS `0`, WARN `0`, FAIL `3`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `3`, unclassified `0`
- `reduced_s2p_reflection`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_rx_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`

## Source Families

- `skrf_tests`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Path-Level Readiness

- `rx`: ready `0`, warn `1`, fail `3`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`
- `reflection`: ready `0`, warn `0`, fail `4`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`
- `full_model`: ready `0`, warn `1`, fail `3`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`

## Family Audit Outcomes

- `full_vector_fit`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `0/0/0/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_reflection`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_reflection`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_rx_delay_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `rx_overshoot_margin`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_undershoot_margin`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (WARN, scope `general_multiport`), RX `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_view_trust_smoke_2026-06-10/selected_models/Clarity_example_acf20e4a.sp`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates
- `cst_example_4ports_e82e6e67`: no candidate passed independent qualification gates
- `designer_variable_coupler_ideal_20deg_e31d0708`: no candidate passed independent qualification gates
