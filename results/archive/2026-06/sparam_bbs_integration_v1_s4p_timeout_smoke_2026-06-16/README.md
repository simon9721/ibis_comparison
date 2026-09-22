# ngspice S-parameter Trust Workflow

Generated: 2026-06-16 17:18:53

## Summary

- Candidate metric rows: 1
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- RX-through PASS/WARN/FAIL: 0 / 1 / 0
- RX voltage-shape PASS/WARN/FAIL: 1 / 0 / 0
- RX timing PASS/WARN/FAIL: 0 / 1 / 0
- Reflection PASS/WARN/FAIL: 0 / 0 / 1
- Full-model PASS/WARN/FAIL: 0 / 1 / 0
- Failed channels: 0
- HSPICE correlation rows: 0
- Successful HSPICE correlations: 0
- BBS extraction rows: 2
- BBS candidate metric rows: 0
- BBS ngspice smoke rows: 0
- BBS HSPICE audit rows: 0
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
- `bbs_candidates.csv`: BroadbandSPICE extraction outputs
- `bbs_ngspice_smoke.csv`: ngspice smoke metrics for BBS General SPICE models
- `bbs_hspice_correlation.csv`: optional BBS HSPICE native S-element audit
- `selected_models/bbs/`: archived BBS HSPICE and General SPICE netlists
- `plots/bbs_overlays/`: BBS HSPICE-vs-ngspice overlays

## Candidate Families

- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `1`, FAIL `0`, unclassified `0`

## Source Families

- `extra`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Broadband SPICE Integration

- BBS extraction success: `0/2` rows
- BBS HSPICE-compatible outputs: `0`
- BBS General SPICE outputs: `0`
- BBS independent PASS/WARN/FAIL: `0/0/0`
- BBS HSPICE audit P/W/F/E: `0/0/0/0`

## Path-Level Readiness

- `rx_voltage_shape`: pass `1`, warn `0`, fail `0`
- `rx_timing`: pass `0`, warn `1`, fail `0`
- `rx_voltage_shape`: ready `1`, warn `0`, fail `0`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`
- `rx_timing`: ready `0`, warn `1`, fail `0`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`
- `rx`: ready `0`, warn `1`, fail `0`, selected models `1`, HSPICE P/W/F/E `0/0/0/0`
- `reflection`: ready `0`, warn `0`, fail `1`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`
- `full_model`: ready `0`, warn `1`, fail `0`, selected models `0`, HSPICE P/W/F/E `0/0/0/0`

## Family Audit Outcomes

- `reduced_4p_rx_dominant_delay_rc`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `reduced_4p_not_full_matrix`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_low_swing_metric_floor`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `threshold_delay_confidence_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Ch10_35_5F3N_f4_ce6f6d8c`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`, RX-shape `PASS`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0001093`, max SV `3.808e-05`, model `results/sparam_bbs_integration_v1_s4p_timeout_smoke_2026-06-16/selected_models/Ch10_35_5F3N_f4_ce6f6d8c.sp`
