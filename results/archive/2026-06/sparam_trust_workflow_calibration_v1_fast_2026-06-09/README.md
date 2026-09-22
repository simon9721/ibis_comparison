# ngspice S-parameter Trust Workflow

Generated: 2026-06-09 21:11:11

## Summary

- Candidate metric rows: 497
- Selected channels: 149
- Independent PASS/WARN/FAIL: 0 / 149 / 0
- Failed channels: 56
- HSPICE correlation rows: 15
- Successful HSPICE correlations: 15
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

- `full_vector_fit`: PASS `0`, WARN `4`, FAIL `36`, unclassified `0`
- `full_vector_fit_enforced`: PASS `0`, WARN `0`, FAIL `27`, unclassified `0`
- `reduced_4p_dominant_delay_rc`: PASS `0`, WARN `145`, FAIL `40`, unclassified `0`
- `reduced_4p_dominant_delay_rc_reflect`: PASS `0`, WARN `145`, FAIL `40`, unclassified `0`
- `reduced_s2p_delay_rc`: PASS `0`, WARN `0`, FAIL `20`, unclassified `0`
- `reduced_s2p_delay_rc_ring`: PASS `0`, WARN `0`, FAIL `20`, unclassified `0`
- `reduced_s2p_delay_rc_ring_reflect`: PASS `0`, WARN `0`, FAIL `20`, unclassified `0`

## Source Families

- `cisco`: PASS `0`, WARN `144`, FAIL `0`
- `repo_local`: PASS `0`, WARN `1`, FAIL `0`
- `skrf_tests`: PASS `0`, WARN `4`, FAIL `0`

## Calibration Split

- `calibration`: PASS `0`, WARN `120`, FAIL `0`
- `holdout`: PASS `0`, WARN `29`, FAIL `0`

## False-PASS Headline

- Split `all`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`
- Split `calibration`: independent PASS total `0`, HSPICE pass `0`, warn `0`, fail `0`, error `0`, false-PASS `n/a`

## Family Audit Outcomes

- `full_vector_fit`: selected `4`, independent P/W/F `0/4/0`, HSPICE P/W/F/E `5/2/2/0`
- `full_vector_fit_enforced`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_4p_dominant_delay_rc`: selected `145`, independent P/W/F `0/145/0`, HSPICE P/W/F/E `0/3/3/0`
- `reduced_4p_dominant_delay_rc_reflect`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc_ring`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`
- `reduced_s2p_delay_rc_ring_reflect`: selected `0`, independent P/W/F `0/0/0`, HSPICE P/W/F/E `0/0/0/0`

## Warning Audit Outcomes

- `passivity_margin_low`: channels `2`, audit rows `6`, HSPICE P/W/F/E `4/2/0/0`
- `reduced_4p_not_full_matrix`: channels `145`, audit rows `6`, HSPICE P/W/F/E `0/3/3/0`
- `rx_edge_ringing_threshold_ambiguous`: channels `29`, audit rows `3`, HSPICE P/W/F/E `0/0/3/0`
- `rx_low_swing_metric_floor`: channels `145`, audit rows `6`, HSPICE P/W/F/E `0/3/3/0`
- `rx_overshoot_margin`: channels `4`, audit rows `9`, HSPICE P/W/F/E `5/2/2/0`
- `rx_settling_margin`: channels `138`, audit rows `6`, HSPICE P/W/F/E `0/3/3/0`
- `rx_undershoot_margin`: channels `4`, audit rows `9`, HSPICE P/W/F/E `5/2/2/0`
- `threshold_delay_confidence_low`: channels `147`, audit rows `12`, HSPICE P/W/F/E `4/5/3/0`
- `tx_edge_ringing_threshold_ambiguous`: channels `2`, audit rows `6`, HSPICE P/W/F/E `4/2/0/0`
- `voltage_shape_ok_threshold_delay_low`: channels `147`, audit rows `12`, HSPICE P/W/F/E `4/5/3/0`

## Selected Models

- `Clarity_example_acf20e4a`: `vector_3r3c` (WARN, scope `general_multiport`), order `9`, RMS `0.0004875`, max SV `0.9984`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Clarity_example_acf20e4a.sp`
- `ntwk2_e1c16499`: `vector_5r5c` (WARN, scope `general_multiport`), order `15`, RMS `3.131e-10`, max SV `1`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/ntwk2_e1c16499.sp`
- `ntwk2_24638a5f`: `vector_5r5c` (WARN, scope `general_multiport`), order `15`, RMS `3.131e-10`, max SV `1`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/ntwk2_24638a5f.sp`
- `RS_ZNB8_23e14c3f`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0001327`, max SV `2.648e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/RS_ZNB8_23e14c3f.sp`
- `Ch10_35_5F3N_f1_49905299`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001045`, max SV `0.002948`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_f1_49905299.sp`
- `Ch10_35_5F3N_f2_f23c49e2`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `5.251e-05`, max SV `3.419e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_f2_f23c49e2.sp`
- `Ch10_35_5F3N_f3_81049e25`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0005233`, max SV `9.274e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_f3_81049e25.sp`
- `Ch10_35_5F3N_f4_fc94db99`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0001093`, max SV `4.027e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_f4_fc94db99.sp`
- `Ch10_35_5F3N_f5_3a904f20`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `5.353e-05`, max SV `1.958e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_f5_3a904f20.sp`
- `Ch10_35_5F3N_n1_8e377765`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_n1_8e377765.sp`
- `Ch10_35_5F3N_n3_a9ef8f2b`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch10_35_5F3N_n3_a9ef8f2b.sp`
- `Ch1_10_5F3N_f1_8f9c2982`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0008541`, max SV `0.000694`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_f1_8f9c2982.sp`
- `Ch1_10_5F3N_f2_47dc69c2`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.000335`, max SV `0.0001185`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_f2_47dc69c2.sp`
- `Ch1_10_5F3N_f4_dfb4f0b9`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001027`, max SV `9.804e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_f4_dfb4f0b9.sp`
- `Ch1_10_5F3N_f5_30ca600f`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0003149`, max SV `6.711e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_f5_30ca600f.sp`
- `Ch1_10_5F3N_n1_9a8781a5`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_n1_9a8781a5.sp`
- `Ch1_10_5F3N_n3_3af593d3`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch1_10_5F3N_n3_3af593d3.sp`
- `Ch2_12_5F3N_f1_3378b0a3`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0006818`, max SV `0.0009241`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_f1_3378b0a3.sp`
- `Ch2_12_5F3N_f2_d795f530`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0003567`, max SV `0.0001026`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_f2_d795f530.sp`
- `Ch2_12_5F3N_f4_5d940b85`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0004632`, max SV `0.0001435`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_f4_5d940b85.sp`
- `Ch2_12_5F3N_f5_f42d0440`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0002052`, max SV `6.874e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_f5_f42d0440.sp`
- `Ch2_12_5F3N_n1_a8c804cf`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_n1_a8c804cf.sp`
- `Ch2_12_5F3N_n3_0722c1a4`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch2_12_5F3N_n3_0722c1a4.sp`
- `Ch3_17_5F3N_f1_ea073bed`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0006423`, max SV `0.001783`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_f1_ea073bed.sp`
- `Ch3_17_5F3N_f2_88fcb92b`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.000127`, max SV `1.567e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_f2_88fcb92b.sp`
- `Ch3_17_5F3N_f3_c08ef229`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.002713`, max SV `0.0003088`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_f3_c08ef229.sp`
- `Ch3_17_5F3N_f4_efc6aab7`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0005665`, max SV `0.0003167`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_f4_efc6aab7.sp`
- `Ch3_17_5F3N_f5_2005253f`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.000137`, max SV `3.615e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_f5_2005253f.sp`
- `Ch3_17_5F3N_n1_154e3882`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_n1_154e3882.sp`
- `Ch3_17_5F3N_n3_7c2c38b4`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch3_17_5F3N_n3_7c2c38b4.sp`
- `Ch4_20_5F3N_f1_3d23614b`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0002577`, max SV `0.0005357`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_f1_3d23614b.sp`
- `Ch4_20_5F3N_f2_82231e3b`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `7.83e-05`, max SV `2.737e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_f2_82231e3b.sp`
- `Ch4_20_5F3N_f3_f9f1e38c`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001786`, max SV `0.0003035`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_f3_f9f1e38c.sp`
- `Ch4_20_5F3N_f4_b2aeb782`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0002352`, max SV `6.602e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_f4_b2aeb782.sp`
- `Ch4_20_5F3N_f5_fb83e9a3`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0001012`, max SV `3.997e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_f5_fb83e9a3.sp`
- `Ch4_20_5F3N_n1_18bbe129`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001925`, max SV `3.059e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_n1_18bbe129.sp`
- `Ch4_20_5F3N_n3_3aef7b19`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001587`, max SV `2.118e-05`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch4_20_5F3N_n3_3aef7b19.sp`
- `Ch5_22_5F3N_f1_ceb18ce3`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.0008636`, max SV `0.002507`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch5_22_5F3N_f1_ceb18ce3.sp`
- `Ch5_22_5F3N_f2_46ed874c`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `7.853e-05`, max SV `0.0001018`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch5_22_5F3N_f2_46ed874c.sp`
- `Ch5_22_5F3N_f3_8c03a4fd`: `reduced_4p_dominant_delay_rc` (WARN, scope `matched_50ohm_reduced_4p`), order `9`, RMS `0.001616`, max SV `0.000273`, model `results/sparam_trust_workflow_calibration_v1_fast_2026-06-09/selected_models/Ch5_22_5F3N_f3_8c03a4fd.sp`
- ... 109 more

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
- `Ch1_10_5F3N_f3_ab427591`: no candidate passed independent qualification gates
- `Ch1_10_5F3N_n2_a8ccad10`: no candidate passed independent qualification gates
- `Ch1_10_5F3N_t_9f42119e`: no candidate passed independent qualification gates
- `Ch2_12_5F3N_f3_c4aa62ca`: no candidate passed independent qualification gates
- `Ch2_12_5F3N_n2_7df3d449`: no candidate passed independent qualification gates
- `Ch2_12_5F3N_t_6b0325a2`: no candidate passed independent qualification gates
- `Ch3_17_5F3N_n2_6af9a3d7`: no candidate passed independent qualification gates
- `Ch3_17_5F3N_t_b5beac5f`: no candidate passed independent qualification gates
- `Ch4_20_5F3N_n2_63b78e89`: no candidate passed independent qualification gates
- `Ch4_20_5F3N_t_78b3548c`: no candidate passed independent qualification gates
- `Ch5_22_5F3N_n2_62fabfed`: no candidate passed independent qualification gates
- `Ch5_22_5F3N_t_cd60ff78`: no candidate passed independent qualification gates
- `Ch6_25_5F3N_n2_1d1f7481`: no candidate passed independent qualification gates
- `Ch6_25_5F3N_t_99b0e890`: no candidate passed independent qualification gates
- `Ch7_28_5F3N_n2_411f3ca5`: no candidate passed independent qualification gates
- `Ch7_28_5F3N_t_14e90129`: no candidate passed independent qualification gates
- `Ch8_30_5F3N_n2_a4161197`: no candidate passed independent qualification gates
- `Ch8_30_5F3N_t_21ef6343`: no candidate passed independent qualification gates
- `Ch9_33_5F3N_n2_873a1ec3`: no candidate passed independent qualification gates

## HSPICE Calibration

- Split `all`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `all`, independent `WARN`: HSPICE pass `5`, warn `5`, fail `5`, error `0`, total `15`
- Split `all`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `PASS`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
- Split `calibration`, independent `WARN`: HSPICE pass `5`, warn `5`, fail `5`, error `0`, total `15`
- Split `calibration`, independent `FAIL`: HSPICE pass `0`, warn `0`, fail `0`, error `0`, total `0`
