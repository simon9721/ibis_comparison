# ngspice S-parameter Trust Workflow

Generated: 2026-06-16 17:28:02

## Summary

- Candidate metric rows: 7
- Selected channels: 1
- Independent PASS/WARN/FAIL: 0 / 1 / 0
- RX-through PASS/WARN/FAIL: 0 / 1 / 1
- RX voltage-shape PASS/WARN/FAIL: 0 / 1 / 1
- RX timing PASS/WARN/FAIL: 1 / 0 / 1
- Reflection PASS/WARN/FAIL: 0 / 0 / 2
- Full-model PASS/WARN/FAIL: 0 / 1 / 1
- Failed channels: 1
- HSPICE correlation rows: 1
- Successful HSPICE correlations: 1
- BBS extraction rows: 4
- BBS candidate metric rows: 2
- BBS ngspice smoke rows: 24
- BBS HSPICE audit rows: 2
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

- `bbs_full_model`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`
- `full_vector_fit`: PASS `0`, WARN `1`, FAIL `1`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `0`, FAIL `2`, unclassified `0`

## Source Families

- `extra`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `1`, FAIL `0`

## Broadband SPICE Integration

- BBS extraction success: `4/4` rows
- BBS HSPICE-compatible outputs: `2`
- BBS General SPICE outputs: `2`
- BBS independent PASS/WARN/FAIL: `0/0/2`
- BBS HSPICE audit P/W/F/E: `0/0/2/0`
- `Agilent_E5071B_605d686c` `bbs_passivity2_gspice`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_integration_v1_2026-06-16/channels/Agilent_E5071B_605d686c/models/bbs_passivity2_gspice/Agilent_E5071B_605d686c_bbs_passivity2_gspice_ngspice_wrapper.sp`
- `Clarity_example_4e655cc2` `bbs_passivity2_gspice`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_integration_v1_2026-06-16/channels/Clarity_example_4e655cc2/models/bbs_passivity2_gspice/Clarity_example_4e655cc2_bbs_passivity2_gspice_ngspice_wrapper.sp`

## Path-Level Readiness

- `rx_voltage_shape`: pass `0`, warn `1`, fail `1`
- `rx_timing`: pass `1`, warn `0`, fail `1`
- `rx_voltage_shape`: ready `0`, warn `1`, fail `1`, selected models `1`, HSPICE P/W/F/E `0/0/1/0`
- `rx_timing`: ready `1`, warn `0`, fail `1`, selected models `1`, HSPICE P/W/F/E `0/1/0/0`
- `rx`: ready `0`, warn `1`, fail `1`, selected models `1`, HSPICE P/W/F/E `0/0/1/0`
- `reflection`: ready `0`, warn `0`, fail `2`, selected models `0`, HSPICE P/W/F/E `1/0/0/0`
- `full_model`: ready `0`, warn `1`, fail `1`, selected models `0`, HSPICE P/W/F/E `0/0/1/0`

## False-PASS Headline

- Split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- Split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## View False-PASS Headline

- View `rx_voltage_shape`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx_voltage_shape`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx_timing`, split `all`: independent PASS total `1`, HSPICE pass `0`, warn `1`, fail `0`, error `0`, false-PASS `1`
- View `rx_timing`, split `calibration`: independent PASS total `1`, HSPICE pass `0`, warn `1`, fail `0`, error `0`, false-PASS `1`
- View `rx`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `rx`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `reflection`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- View `full_model`, split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## Family Audit Outcomes

- `bbs_full_model`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `full_vector_fit`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `0/0/1/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_rx_dominant_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `rx_overshoot_margin`: channels `1`, audit rows `1`, HSPICE P/W/F/E `0/0/1/0`
- `rx_undershoot_margin`: channels `1`, audit rows `1`, HSPICE P/W/F/E `0/0/1/0`

## Selected Models

- `Clarity_example_4e655cc2`: `vector_3r3c` (WARN, scope `general_multiport`), RX `RX_WARN_VOLTAGE_MARGIN`, RX-shape `WARN`, RX-timing `PASS`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_bbs_integration_v1_2026-06-16/selected_models/Clarity_example_4e655cc2.sp`

## Failed Channels

- `Agilent_E5071B_605d686c`: no candidate passed independent qualification gates

## HSPICE Calibration

- Split `all`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `all`, independent `WARN`: HSPICE pass `0`, warn `0`, fail `1`, error `0`, total `1`
- Split `all`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `WARN`: HSPICE pass `0`, warn `0`, fail `1`, error `0`, total `1`
- Split `calibration`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
