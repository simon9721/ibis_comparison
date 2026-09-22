# ngspice S-parameter Trust Workflow

Generated: 2026-06-16 20:53:30

## Summary

- Candidate metric rows: 18
- Selected channels: 2
- Independent PASS/WARN/FAIL: 0 / 2 / 0
- RX-through PASS/WARN/FAIL: 0 / 2 / 1
- RX voltage-shape PASS/WARN/FAIL: 1 / 1 / 1
- RX timing PASS/WARN/FAIL: 1 / 1 / 1
- Reflection PASS/WARN/FAIL: 0 / 0 / 3
- Full-model PASS/WARN/FAIL: 0 / 2 / 1
- Failed channels: 1
- HSPICE correlation rows: 1
- Successful HSPICE correlations: 1
- BBS extraction rows: 30
- BBS candidate metric rows: 14
- BBS ngspice smoke rows: 96
- BBS HSPICE audit rows: 4
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
- `bbs_audit_share_pack/`: per-plotted-case BBS models, testbenches, outputs, and RX/TX plots
- `bbs_audit_share_pack_index.csv`: index of the BBS share-pack files
- `selected_models/bbs/`: archived BBS HSPICE and General SPICE netlists
- `plots/bbs_overlays/`: BBS HSPICE-vs-ngspice overlays

## Candidate Families

- `bbs_full_model`: PASS `0`, WARN `0`, FAIL `14`, unclassified `0`
- `full_vector_fit`: PASS `0`, WARN `1`, FAIL `1`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `1`, unclassified `0`
- `reduced_4p_rx_dominant_delay_rc`: PASS `0`, WARN `1`, FAIL `0`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `1`, FAIL `0`
- `extra`: PASS `0`, WARN `1`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `2`, FAIL `0`

## Broadband SPICE Integration

- BBS extraction success: `28/30` rows
- BBS extraction timeouts: `2`
- BBS HSPICE-compatible outputs: `14`
- BBS General SPICE outputs: `14`
- BBS independent PASS/WARN/FAIL: `0/0/14`
- BBS HSPICE audit P/W/F/E: `0/0/4/0`
- BBS audit share-pack cases: `4`
- BBS remains a full-model candidate family; HSPICE audit results are reported separately and do not affect `qualify` ranking.

### BBS Preset Extraction Summary

- `causality`: ok `4`, failed `0`, timeout `0`
- `clean`: ok `4`, failed `2`, timeout `2`
- `lowfreq`: ok `4`, failed `0`, timeout `0`
- `recip_lowfreq`: ok `4`, failed `0`, timeout `0`
- `reciprocity`: ok `4`, failed `0`, timeout `0`
- `smooth_lowfreq`: ok `4`, failed `0`, timeout `0`
- `smoothing`: ok `4`, failed `0`, timeout `0`

### Best BBS Candidate Per Channel

- `Agilent_E5071B_17b7949f`: `bbs_passivity2_gspice_clean` (best_bbs_metric_candidate), mode `passivity2`, preset `clean`, independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, ngspice pass `False`, extractions `14/14`
- `Ch10_35_5F3N_f4_6affb031`: `none` (no_successful_bbs_gspice_model), mode ``, preset ``, independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, ngspice pass ``, extractions `0/2`
- `Clarity_example_09b58d4b`: `bbs_passivity2_gspice_clean` (best_bbs_metric_candidate), mode `passivity2`, preset `clean`, independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, ngspice pass `True`, extractions `14/14`

### BBS Candidate Metric Rows

- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_clean`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_clean/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_clean_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_reciprocity`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_reciprocity/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_reciprocity_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_lowfreq/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_lowfreq_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_smoothing`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_smoothing/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_smoothing_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_causality`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_causality/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_causality_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_recip_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_recip_lowfreq/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_recip_lowfreq_ngspice_wrapper.sp`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_smooth_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Agilent_E5071B_17b7949f/models/bbs_passivity2_gspice_smooth_lowfreq/Agilent_E5071B_17b7949f_bbs_passivity2_gspice_smooth_lowfreq_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_clean`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_clean/Clarity_example_09b58d4b_bbs_passivity2_gspice_clean_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_reciprocity`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_reciprocity/Clarity_example_09b58d4b_bbs_passivity2_gspice_reciprocity_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_lowfreq/Clarity_example_09b58d4b_bbs_passivity2_gspice_lowfreq_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_smoothing`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_smoothing/Clarity_example_09b58d4b_bbs_passivity2_gspice_smoothing_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_causality`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_causality/Clarity_example_09b58d4b_bbs_passivity2_gspice_causality_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_recip_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_recip_lowfreq/Clarity_example_09b58d4b_bbs_passivity2_gspice_recip_lowfreq_ngspice_wrapper.sp`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_smooth_lowfreq`: independent `FAIL`, RX `FAIL`, reflection `FAIL`, full `FAIL`, wrapper `results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/models/bbs_passivity2_gspice_smooth_lowfreq/Clarity_example_09b58d4b_bbs_passivity2_gspice_smooth_lowfreq_ngspice_wrapper.sp`

### BBS HSPICE Audit Overlays

- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_clean` `audit_amp1p5_edge5_r50`: HSPICE audit `FAIL`, RX `WARN`, reflection `FAIL`, RX active RMSE `0.0009560196119054348` V, TX active RMSE `0.19920262044518247` V, rise delay delta `-5.803876169862178` ps, RX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Agilent_E5071B_17b7949f/rx/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_rx.png`, TX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Agilent_E5071B_17b7949f/tx/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_tx.png`
- `Agilent_E5071B_17b7949f` `bbs_passivity2_gspice_reciprocity` `audit_amp1p5_edge5_r50`: HSPICE audit `FAIL`, RX `WARN`, reflection `FAIL`, RX active RMSE `0.0009560196119054348` V, TX active RMSE `0.19920262044518247` V, rise delay delta `-5.803876169862178` ps, RX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Agilent_E5071B_17b7949f/rx/bbs_passivity2_gspice_reciprocity_audit_amp1p5_edge5_r50_rx.png`, TX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Agilent_E5071B_17b7949f/tx/bbs_passivity2_gspice_reciprocity_audit_amp1p5_edge5_r50_tx.png`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_clean` `audit_amp1p5_edge5_r50`: HSPICE audit `FAIL`, RX `FAIL`, reflection `PASS`, RX active RMSE `0.04616932727721244` V, TX active RMSE `0.009369862836086965` V, rise delay delta `4.912230951641845` ps, RX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Clarity_example_09b58d4b/rx/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_rx.png`, TX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Clarity_example_09b58d4b/tx/bbs_passivity2_gspice_clean_audit_amp1p5_edge5_r50_tx.png`
- `Clarity_example_09b58d4b` `bbs_passivity2_gspice_reciprocity` `audit_amp1p5_edge5_r50`: HSPICE audit `FAIL`, RX `FAIL`, reflection `PASS`, RX active RMSE `0.04616932727721244` V, TX active RMSE `0.009369862836086965` V, rise delay delta `4.912230951641845` ps, RX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Clarity_example_09b58d4b/rx/bbs_passivity2_gspice_reciprocity_audit_amp1p5_edge5_r50_rx.png`, TX plot `results/sparam_bbs_quality_tuning_v1_2026-06-17/plots/bbs_overlays/Clarity_example_09b58d4b/tx/bbs_passivity2_gspice_reciprocity_audit_amp1p5_edge5_r50_tx.png`

## Path-Level Readiness

- `rx_voltage_shape`: pass `1`, warn `1`, fail `1`
- `rx_timing`: pass `1`, warn `1`, fail `1`
- `rx_voltage_shape`: ready `1`, warn `1`, fail `1`, selected models `2`, HSPICE P/W/F/E `0/0/1/0`
- `rx_timing`: ready `1`, warn `1`, fail `1`, selected models `2`, HSPICE P/W/F/E `0/1/0/0`
- `rx`: ready `0`, warn `2`, fail `1`, selected models `2`, HSPICE P/W/F/E `0/0/1/0`
- `reflection`: ready `0`, warn `0`, fail `3`, selected models `0`, HSPICE P/W/F/E `1/0/0/0`
- `full_model`: ready `0`, warn `2`, fail `1`, selected models `0`, HSPICE P/W/F/E `0/0/1/0`

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
- `reduced_4p_rx_dominant_delay_rc`: selected `1`, independent P/W/F `0/1/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `reduced_4p_not_full_matrix`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_low_swing_metric_floor`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_overshoot_margin`: channels `1`, audit rows `1`, HSPICE P/W/F/E `0/0/1/0`
- `rx_undershoot_margin`: channels `1`, audit rows `1`, HSPICE P/W/F/E `0/0/1/0`
- `threshold_delay_confidence_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `1`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Clarity_example_09b58d4b`: `vector_3r3c` (WARN, scope `general_multiport`), RX `RX_WARN_VOLTAGE_MARGIN`, RX-shape `WARN`, RX-timing `PASS`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_bbs_quality_tuning_v1_2026-06-17/selected_models/Clarity_example_09b58d4b.sp`
- `Ch10_35_5F3N_f4_6affb031`: `reduced_4p_rx_dominant_delay_rc` (WARN, scope `matched_50ohm_rx_through`), RX `RX_VOLTAGE_OK_TIMING_AMBIGUOUS`, RX-shape `PASS`, RX-timing `WARN`, reflection `FAIL`, full `WARN`, order `9`, RMS `0.0001093`, max SV `3.808e-05`, model `results/sparam_bbs_quality_tuning_v1_2026-06-17/selected_models/Ch10_35_5F3N_f4_6affb031.sp`

## Failed Channels

- `Agilent_E5071B_17b7949f`: no candidate passed independent qualification gates

## HSPICE Calibration

- Split `all`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `all`, independent `WARN`: HSPICE pass `0`, warn `0`, fail `1`, error `0`, total `1`
- Split `all`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `WARN`: HSPICE pass `0`, warn `0`, fail `1`, error `0`, total `1`
- Split `calibration`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
