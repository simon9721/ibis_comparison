# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 20:23:19

## Summary

- Candidate metric rows: 621
- Selected channels: 11
- Independent PASS/WARN/FAIL: 0 / 11 / 0
- Failed channels: 21
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
- `candidate_family_summary.csv`: candidate-family selection and audit outcomes
- `warning_audit_summary.csv`: warning reason vs HSPICE audit outcomes
- `audit_overlay_groups/`: optional grouped HSPICE-vs-ngspice overlay PDFs

## Candidate Families

- `full_vector_fit`: PASS `0`, WARN `4`, FAIL `253`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `204`, unclassified `0`
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `8`, FAIL `24`, unclassified `0`
- `reduced_4p_dominant_delay_rc_reflect`: PASS `0`, WARN `8`, FAIL `24`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `32`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `32`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `32`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `7`, FAIL `0`
- `skrf_tests`: PASS `0`, WARN `4`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `10`, FAIL `0`
- `holdout`: PASS `0`, WARN `1`, FAIL `0`

## Family Audit Outcomes

- `full_vector_fit`: selected `3`, independent P/W/F `0/3/0`, HSPICE P/W/F/E `0/0/0/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_dominant_delay_rc`: selected `8`, independent P/W/F `0/8/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_dominant_delay_rc_reflect`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc_ring_reflect`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `passivity_margin_low`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_not_full_matrix`: channels `8`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_edge_ringing_threshold_ambiguous`: channels `3`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_low_swing_metric_floor`: channels `8`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_overshoot_margin`: channels `3`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_settling_margin`: channels `7`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `rx_undershoot_margin`: channels `3`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `threshold_delay_confidence_low`: channels `10`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `tx_edge_ringing_threshold_ambiguous`: channels `2`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `10`, audit rows `0`, HSPICE P/W/F/E `0/0/0/0`

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (WARN, scope `general_multiport`), order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Clarity_example_acf20e4a.sp`
- `ntwk2_e1c16499`: `vector_5r5c` (WARN, scope `general_multiport`), order `15`, RMS `3.131e-10`, max SV `1`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/ntwk2_e1c16499.sp`
- `ntwk2_24638a5f`: `vector_5r5c` (WARN, scope `general_multiport`), order `15`, RMS `3.131e-10`, max SV `1`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/ntwk2_24638a5f.sp`
- `RS_ZNB8_23e14c3f`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0001327`, max SV `2.648e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/RS_ZNB8_23e14c3f.sp`
- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_f1_49905299.sp`
- `Ch10_35_5F3N_f2_f23c49e2`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `5.251e-05`, max SV `3.419e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_f2_f23c49e2.sp`
- `Ch10_35_5F3N_f3_81049e25`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0005233`, max SV `9.274e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_f3_81049e25.sp`
- `Ch10_35_5F3N_f4_fc94db99`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0001093`, max SV `4.027e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_f4_fc94db99.sp`
- `Ch10_35_5F3N_f5_3a904f20`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `5.353e-05`, max SV `1.958e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_f5_3a904f20.sp`
- `Ch10_35_5F3N_n1_8e377765`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_n1_8e377765.sp`
- `Ch10_35_5F3N_n3_a9ef8f2b`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_2026-06-09/selected_models/Ch10_35_5F3N_n3_a9ef8f2b.sp`

## Failed Channels

- `Agilent_E5071B_4f4fd1d7`: no candidate passed independent qualification gates
- `cst_example_4ports_e82e6e67`: no candidate passed independent qualification gates
- `designer_variable_coupler_ideal_20deg_e31d0708`: no candidate passed independent qualification gates
- `designer_variable_coupler_ideal_75deg_50e48e76`: no candidate passed independent qualification gates
- `fet_7e5200ad`: no candidate passed independent qualification gates
- `hfss_twoport_e975fe9f`: no candidate passed independent qualification gates
- `LFCN-2352__Plus125degC_4793e65c`: no candidate passed independent qualification gates
- `LFCN-2352__Plus25degC_d04142bc`: no candidate passed independent qualification gates
- `ntwk1_f450e450`: no candidate passed independent qualification gates
- `ntwk3_ad74ab42`: no candidate passed independent qualification gates
- `ntwk4_806cfc7d`: no candidate passed independent qualification gates
- `ntwk4_n_6d3c414e`: no candidate passed independent qualification gates
- `ntwk_arbitrary_frequency_3e8760a8`: no candidate passed independent qualification gates
- `ntwk_noise_65eeb4e4`: no candidate passed independent qualification gates
- `ntwk_noise_interp_a132609e`: no candidate passed independent qualification gates
- `ntwk1_e20029da`: no candidate passed independent qualification gates
- `ntwk3_8f8a2430`: no candidate passed independent qualification gates
- `RS_ZVR_1.20_beta_f_6cd9e598`: no candidate passed independent qualification gates
- `thru_a0b4754f`: no candidate passed independent qualification gates
- `Ch10_35_5F3N_n2_b3e24295`: no candidate passed independent qualification gates
- `Ch10_35_5F3N_t_d3c7dddc`: no candidate passed independent qualification gates
