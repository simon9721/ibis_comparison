# ngspice S-parameter Trust Workflow

Generated: 2026-06-10 00:34:57

## Summary

- Candidate metric rows: 9
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- RX-through PASS/WARN/FAIL: 0 / 1 / 1
- RX voltage-shape PASS/WARN/FAIL: 0 / 1 / 1
- RX timing PASS/WARN/FAIL: 1 / 0 / 1
- Reflection PASS/WARN/FAIL: 0 / 0 / 2
- Full-model PASS/WARN/FAIL: 0 / 1 / 1
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
- `reduced_4p_reflection_s11_rc`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_rx_delayeq_rc_ring`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_reflection_s11_rc`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_rx_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_s2p_rx_delayeq_rc_ring`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`

## Source Families

- `skrf_tests`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Path-Level Readiness

- `rx_voltage_shape`: pass `0`, warn `1`, fail `1`
- `rx_timing`: pass `1`, warn `0`, fail `1`
- `rx_voltage_shape`: ready `0`, warn `1`, fail `1`, selected models `1`, HSPICE P/W/F/E `1/0/2/0`
- `rx_timing`: ready `1`, warn `0`, fail `1`, selected models `1`, HSPICE P/W/F/E `2/1/0/0`
- `rx`: ready `0`, warn `1`, fail `1`, selected models `1`, HSPICE P/W/F/E `1/0/2/0`
- `reflection`: ready `0`, warn `0`, fail `2`, selected models `0`, HSPICE P/W/F/E `3/0/0/0`
- `full_model`: ready `0`, warn `1`, fail `1`, selected models `0`, HSPICE P/W/F/E `1/0/2/0`

## False-PASS Headline

- Split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- Split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## View False-PASS Headline

- View `rx_voltage_shape`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx_voltage_shape`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx_timing`, split `all`: independent PASS total `3`, HSPICE pass `2`, warn `1`, fail `0`, error `0`, false-PASS `0.3333`
- View `rx_timing`, split `calibration`: independent PASS total `3`, HSPICE pass `2`, warn `1`, fail `0`, error `0`, false-PASS `0.3333`
- View `rx`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## Family Audit Outcomes

- `full_vector_fit`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `1/0/2/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_reflection_s11_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_delayeq_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_reflection_s11_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_rx_delay_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_rx_delayeq_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `rx_overshoot_margin`: channels `1`, audit rows `3`, HSPICE P/W/F/E `1/0/2/0`
- `rx_undershoot_margin`: channels `1`, audit rows `3`, HSPICE P/W/F/E `1/0/2/0`

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (WARN, scope `general_multiport`), RX `RX_WARN_VOLTAGE_MARGIN`, RX-shape `WARN`, RX-timing `PASS`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_rx_trust_v2_s2p_smoke_2026-06-10/selected_models/Clarity_example_acf20e4a.sp`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates

## HSPICE Calibration

- Split `all`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `all`, independent `WARN`: HSPICE pass `1`, warn `0`, fail `2`, error `0`, total `3`
- Split `all`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `WARN`: HSPICE pass `1`, warn `0`, fail `2`, error `0`, total `3`
- Split `calibration`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
