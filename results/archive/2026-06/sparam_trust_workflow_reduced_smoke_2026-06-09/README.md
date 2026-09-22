# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 17:25:18

## Summary

- Candidate metric rows: 10
- Selected channels: 0
- Independent PASS/WARN/FAIL: 0 / 0 / 0
- Failed channels: 2
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
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`

## Source Families


## Selected Models


## Failed Channels

- `Ch10_35_5F3N_f1_49905299`: no candidate passed independent qualification gates
- `Ch10_35_5F3N_f2_f23c49e2`: no candidate passed independent qualification gates
