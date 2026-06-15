# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 17:34:31

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

- `full_vector_fit`: PASS `0`, WARN `1`, FAIL `1`, unclassified `0`
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`

## Source Families

- `skrf_tests`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (WARN, scope `general_multiport`), order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_trust_workflow_reduced_s2p_smoke_2026-06-09_b/selected_models/Clarity_example_acf20e4a.sp`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates
