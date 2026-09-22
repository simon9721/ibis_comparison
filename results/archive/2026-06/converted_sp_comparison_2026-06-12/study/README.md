# ngspice S-parameter Trust Workflow

Generated: 2026-06-12 09:40:16

## Summary

- Candidate metric rows: 14
- Selected channels: 3
- Independent PASS/WARN/FAIL: 1 / 0 / 2
- RX-through PASS/WARN/FAIL: 1 / 2 / 0
- RX voltage-shape PASS/WARN/FAIL: 3 / 0 / 0
- RX timing PASS/WARN/FAIL: 1 / 2 / 0
- Reflection PASS/WARN/FAIL: 0 / 0 / 3
- Full-model PASS/WARN/FAIL: 1 / 2 / 0
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

- `full_vector_fit`: PASS `1`, WARN `0`, FAIL `2`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_4p_rx_delayeq_rc_ring`: PASS `0`, WARN `2`, FAIL `1`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `2`, FAIL `1`, unclassified `0`
- `reduced_s2p_rx_delayeq_rc_ring`: PASS `0`, WARN `0`, FAIL `3`, unclassified `0`

## Source Families

- `extra`: PASS `1`, WARN `0`, FAIL `2`

## Calibration Split

- `calibration`: PASS `1`, WARN `0`, FAIL `2`

## Path-Level Readiness

- `rx_voltage_shape`: pass `3`, warn `0`, fail `0`
- `rx_timing`: pass `1`, warn `2`, fail `0`
- `rx_voltage_shape`: ready `3`, warn `0`, fail `0`, selected models `3`, HSPICE P/W/F/E `0/0/0/0`
- `rx_timing`: ready `1`, warn `2`, fail `0`, selected models `3`, HSPICE P/W/F/E `0/0/0/0`
- `rx`: ready `1`, warn `2`, fail `0`, selected models `3`, HSPICE P/W/F/E `0/0/0/0`
- `reflection`: ready `0`, warn `0`, fail `3`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`
- `full_model`: ready `1`, warn `2`, fail `0`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`

## Family Audit Outcomes

- `full_vector_fit`: selected `3`, independent P/W/F `1/0/2`, HSPICE P/W/F/E `0/0/0/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_delayeq_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_rx_delayeq_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `NO_WARNING`: channels `3`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Ch10_35_5F3N_f4_cdb7d8f1`: `vector_3r3c` (FAIL, scope `general_multiport`), RX `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`, RX-shape `PASS`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.09994`, max SV `0.9127`, model `results/converted_sp_comparison_2026-06-12/study/selected_models/Ch10_35_5F3N_f4_cdb7d8f1.sp`
- `Ch3_17_5F3N_f3_a34c32c3`: `vector_3r3c` (FAIL, scope `general_multiport`), RX `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`, RX-shape `PASS`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.121`, max SV `0.4614`, model `results/converted_sp_comparison_2026-06-12/study/selected_models/Ch3_17_5F3N_f3_a34c32c3.sp`
- `Clarity_example_4ef781de`: `vector_3r3c` (PASS, scope `general_multiport`), RX `RX_READY`, RX-shape `PASS`, RX-timing `PASS`, reflection `FAIL`, full `FULL_MODEL_READY`, order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/converted_sp_comparison_2026-06-12/study/selected_models/Clarity_example_4ef781de.sp`
