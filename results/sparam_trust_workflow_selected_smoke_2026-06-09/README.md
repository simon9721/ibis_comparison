# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 16:36:06

## Summary

- Candidate metric rows: 2
- Selected channels: 1
- Independent PASS/WARN/FAIL: 1 / 0 / 0
- Failed channels: 1
- HSPICE correlation rows: 3
- Successful HSPICE correlations: 3
- HSPICE is optional audit data only; it is not used by `qualify` model selection.

## Key Files

- `manifest.csv`: Touchstone inventory
- `metrics.csv`: HSPICE-independent fit/passivity metrics
- `ngspice_smoke.csv`: ngspice transient smoke metrics
- `ranking.csv`: selected model per channel
- `selected_models/`: stable copies of selected ngspice-ready models
- `hspice_correlation.csv`: optional HSPICE native S-element audit metrics
- `calibration_summary.csv`: optional independent-trust vs HSPICE-audit confusion matrix

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (PASS), order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_trust_workflow_selected_smoke_2026-06-09/selected_models/Clarity_example_acf20e4a.sp`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates

## HSPICE Calibration

- Independent `PASS`: HSPICE pass `1`, fail `2`, error `0`, total `3`, false-pass rate `0.6667`
- Independent `WARN`: HSPICE pass `0`, fail `0`, error `0`, total `0`
- Independent `FAIL`: HSPICE pass `0`, fail `0`, error `0`, total `0`
