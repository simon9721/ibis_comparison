# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 17:29:53

## Summary

- Candidate metric rows: 10
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- Failed channels: 1
- HSPICE correlation rows: 0
- Successful HSPICE correlations: 0
- HSPICE is optional audit data only; it is not used by `qualify` model selection.

## Key Files

- `manifest.csv`: Touchstone inventory
- `metrics.csv`: HSPICE-independent fit/passivity metrics
- `ngspice_smoke.csv`: ngspice transient smoke metrics
- `ranking.csv`: selected model per channel
- `selected_models/`: stable copies of selected ngspice-ready models
- `hspice_correlation.csv`: optional HSPICE native S-element audit metrics
- `calibration_summary.csv`: optional independent-trust vs HSPICE-audit confusion matrix

## Candidate Families

- `full_vector_fit`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `1`, FAIL `1`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Selected Models

- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_trust_workflow_reduced_smoke_2026-06-09_c/selected_models/Ch10_35_5F3N_f1_49905299.sp`

## Failed Channels

- `Ch10_35_5F3N_f2_f23c49e2`: no candidate passed independent qualification gates
