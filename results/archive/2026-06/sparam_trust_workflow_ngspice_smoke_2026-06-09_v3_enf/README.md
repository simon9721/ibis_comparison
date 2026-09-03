# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 16:31:34

## Summary

- Candidate metric rows: 2
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

## Selected Models


## Failed Channels

- `ch_model_fit_c02b8fb1`: no candidate passed independent qualification gates
