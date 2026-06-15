# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 17:33:37

## Summary

- Candidate metric rows: 5
- Selected channels: 0
- Independent PASS/WARN/FAIL: 0 / 0 / 0
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

- `full_vector_fit`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`

## Source Families


## Selected Models


## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates
