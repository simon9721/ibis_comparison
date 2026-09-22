# Archive index

Everything that was in `results/archive/` on 2026-09-21: 305 entries, 87.7 GB.
The archive itself is on **cloud storage** and is deleted from this disk after the upload;
this list stays so you can tell what is there without downloading it.

- Cloud location: OneDrive - University of Missouri, folder `ibis_comparison_results_archive/`:
  one zip per month bucket (August in four parts), named in the `zip` column below. Each zip
  holds `<bucket>/<entry>/...` and opens on its own.
- Batch 1 (2026-09-03): nothing active referred to them. Batch 2 (2026-09-21): not named by
  any script written since 09-08 (the gate-state / track 1 / track 2 period). The rules, the
  checks and batch 2's per-entry table (git-tracked counts, where each was named) are in
  `results/archive/README.md` and `results/archive/BATCH_2026-09-21.md`, both uploaded with it.
- Documents under `docs/` and the root `README.md` that link `results/archive/<month>/...`
  point into this cloud copy.
- Tracked files are also in git history (`git log -- results/archive/<month>/<name>`);
  gitignored ones (HSPICE `.tr0/.lis`, ngspice `.raw`, `*.log`) exist only in the cloud copy.
- Restoring an entry: put it back at `results/archive/<bucket>/<name>`, or at `results/<name>`
  to make older scripts that name it find it again.

| bucket | entry | MB | batch | zip | what it is |
|---|---|---:|:---:|---|---|
| 2026-05 | `edge_family_diagnostics_2026-05-11` | 1 | 1 | ibis_archive_2026-05.zip | Edge Family Diagnostics |
| 2026-05 | `edge_family_stress_crossflow_2026-05-11` | 3 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_60b_edge50_2026-05-11` | 3 | 1 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_62b_edge50_2026-05-11` | 2 | 1 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_edge15_gear1_2026-05-12` | 2 | 1 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_edge50_2026-05-11` | 2 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_edge50_gear1_2026-05-12` | 3 | 1 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_edge60_2026-05-11` | 2 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_tanh10_2026-05-11` | 2 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_80b_tanh15_2026-05-11` | 2 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_crossflow_coarse10_context38_2026-05-11` | 3 | 2 | ibis_archive_2026-05.zip | Cross-Flow Edge-Family Stress Comparison |
| 2026-05 | `edge_family_stress_ngspice_2026-05-11` | 4 | 1 | ibis_archive_2026-05.zip | ngspice Refspice Edge-Family Stress Study |
| 2026-05 | `final_prbs_rlgc_comparison_2026-05-11` | 3 | 2 | ibis_archive_2026-05.zip | Final PRBS7 + 50 Ohm RLGC Comparison |
| 2026-05 | `hibiki_i3c_tx_0p125ma_1160ohm_ground_5pulse_ngspice_2026-05-28` | <1 | 2 | ibis_archive_2026-05.zip | I3C_TX_0p125mA_tx 1160 ohm ground-terminated 5-pulse ngspice run |
| 2026-05 | `hibiki_i3c_tx_0p125ma_1160ohm_ngspice_2026-05-28` | <1 | 2 | ibis_archive_2026-05.zip | I3C_TX_0p125mA_tx 1160 ohm matched-load ngspice run |
| 2026-05 | `hibiki_i3c_tx_0p125ma_ngspice_2026-05-28` | <1 | 2 | ibis_archive_2026-05.zip | I3C_TX_0p125mA_tx ngspice validation |
| 2026-05 | `hibiki_i3c_tx_0p125ma_wmodel_baseline_ngspice_2026-05-29` | 32 | 2 | ibis_archive_2026-05.zip | Hibiki I3C_TX_0p125mA_tx with Wmodel baseline channel conversion |
| 2026-05 | `hibiki_i3c_tx_0p125ma_wmodel_cascade_ngspice_2026-05-29` | 14 | 2 | ibis_archive_2026-05.zip | Hibiki I3C_TX_0p125mA_tx with cascaded Wmodel baseline traces |
| 2026-05 | `hspice_tr0_comparison_2026-05-11` | 1 | 1 | ibis_archive_2026-05.zip | (generated README; producer not found) |
| 2026-05 | `io_buf_sp_physical_eye_2026-05-11` | <1 | 1 | ibis_archive_2026-05.zip | (generated README; producer not found) |
| 2026-05 | `ngspice_kukd_ab_context38_2026-05-11` | 2 | 2 | ibis_archive_2026-05.zip | Visualize the Ku/Kd optimization mechanism: |
| 2026-05 | `prbs_rlgc_clean_2026-05-10` | 8 | 2 | ibis_archive_2026-05.zip | Diagnose whether PRBS receiver eyes contain real edge-family variation. |
| 2026-05 | `pybis_spike_trend_sweep_2026-05-12` | 2 | 2 | ibis_archive_2026-05.zip | Pybis Spike Trend Sweep |
| 2026-05 | `refspice_pybis_correlation_study_2026-05-27` | 3 | 2 | ibis_archive_2026-05.zip | Compare clean refspice/pybis RSF runs against the source IBIS VT tables. |
| 2026-05 | `setup_audit_2026-05-12` | 1 | 1 | ibis_archive_2026-05.zip | (generated README; producer not found) |
| 2026-05 | `stressed_edge50_corrected_crossflow_2026-05-12_clean` | 2 | 2 | ibis_archive_2026-05.zip | Corrected stressed edge50 cross-flow transient run |
| 2026-05 | `stressed_results_2026-05-11` | 2 | 1 | ibis_archive_2026-05.zip | Plot clear transient and eye-diagram results for the stressed context38 case. |
| 2026-05 | `transient_plot_tool_validation_2026-05-13` | 1 | 2 | ibis_archive_2026-05.zip | (generated README; producer not found) |
| 2026-05 | `transient_review_plots_2026-05-13` | 14 | 2 | ibis_archive_2026-05.zip | Transient And Eye Review Plots |
| 2026-05 | `xyce_edge50_122ns_failure_probe_2026-05-12` | <1 | 1 | ibis_archive_2026-05.zip | Xyce Edge50 122 ns Failure Probe |
| 2026-05 | `xyce_edge50_122ns_fix_sweep_2026-05-12` | <1 | 1 | ibis_archive_2026-05.zip | Xyce Edge50 122 ns Fix Sweep |
| 2026-05 | `xyce_edge50_prbs80_fix_validation_2026-05-12` | <1 | 1 | ibis_archive_2026-05.zip | Xyce Edge50 PRBS80 Fix Validation |
| 2026-05 | `xyce_edge50_solver_isolation_2026-05-12` | <1 | 1 | ibis_archive_2026-05.zip | Xyce Edge50 122 ns Fix Sweep |
| 2026-05 | `xyce_pybis_context38_variant_sweep_2026-05-11` | 2 | 1 | ibis_archive_2026-05.zip | Xyce pybis Context38 Variant Sweep |
| 2026-05 | `xyce_pybis_minmod_ladder_2026-05-11` | <1 | 2 | ibis_archive_2026-05.zip | Xyce pybis Minimum-Modification Ladder |
| 2026-06 | `agilent_e5071b_bbs_s4p_overlay_2026-06-19` | 3 | 2 | ibis_archive_2026-06.zip | Agilent_E5071B_17b7949f BBS Touchstone Overlay |
| 2026-06 | `agilent_io_buf_ibis_bbs_pulsetrain_2026-06-19` | 12 | 1 | ibis_archive_2026-06.zip | Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS |
| 2026-06 | `agilent_io_buf_ibis_bbs_pulsetrain_damped_2026-06-19` | 14 | 1 | ibis_archive_2026-06.zip | Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS |
| 2026-06 | `agilent_io_buf_ibis_bbs_pulsetrain_settled_2026-06-19` | 26 | 1 | ibis_archive_2026-06.zip | Agilent Channel io_buf Pulse Train: HSPICE IBIS vs ngspice pybis/BBS |
| 2026-06 | `agilent_io_buf_ibis_bbs_transient_2026-06-19` | 14 | 1 | ibis_archive_2026-06.zip | Agilent Channel io_buf Transient: HSPICE IBIS vs ngspice pybis/BBS |
| 2026-06 | `bbs_cli_smoke_2026-06-16_gspice_fixed` | <1 | 1 | ibis_archive_2026-06.zip | empty folder (already empty when archived); holds only a two-line note |
| 2026-06 | `bbs_integration_canonical_inputs_2026-06-16` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `bbs_integration_s4p_input_2026-06-16` | 1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `bbs_preset_api_smoke_2026-06-17` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `bbs_quality_tuning_cisco_input_2026-06-17` | 1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `bbs_quality_tuning_pilot_inputs_2026-06-17` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `bbs_quality_tuning_smoke_inputs_2026-06-17` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `clarity_bbs_s2p_overlay_2026-06-19` | 1 | 2 | ibis_archive_2026-06.zip | Clarity_example BBS Overlay |
| 2026-06 | `converted_sp_comparison_2026-06-12` | 8 | 2 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `hspice_rsf_io_buf_inv_chain_2026-06-04` | 3 | 1 | ibis_archive_2026-06.zip | HSPICE RSF io_buf and inv_chain Comparison |
| 2026-06 | `io_buf_charge_limited_gate_retrigger_2026-06-22` | 1,603 | 1 | ibis_archive_2026-06.zip | io_buf Charge-Limited Gate-State pybis Retrigger Study |
| 2026-06 | `io_buf_coeff_state_retrigger_2026-06-20` | 128 | 1 | ibis_archive_2026-06.zip | io_buf Coefficient-State pybis Retrigger Study |
| 2026-06 | `io_buf_directional_gate_state_retrigger_2026-06-22` | 694 | 1 | ibis_archive_2026-06.zip | io_buf Directional Gate-State pybis Retrigger Study |
| 2026-06 | `io_buf_fast_edge_retest_2026-06-05` | 15 | 2 | ibis_archive_2026-06.zip | io_buf Fast-Edge Regeneration Retest |
| 2026-06 | `io_buf_gate_state_retrigger_2026-06-22` | 282 | 1 | ibis_archive_2026-06.zip | io_buf Gate-State pybis Retrigger Study |
| 2026-06 | `io_buf_old_new_four_overlays_2026-06-05` | 1 | 2 | ibis_archive_2026-06.zip | io_buf Old/New Overlay Figures |
| 2026-06 | `io_buf_shortpulse_hybrid_retrigger_2026-06-21` | 269 | 1 | ibis_archive_2026-06.zip | io_buf Short-Pulse Hybrid Retrigger Study |
| 2026-06 | `io_buf_state_continuous_retrigger_2026-06-20` | 136 | 1 | ibis_archive_2026-06.zip | io_buf State-Continuous pybis Retrigger Study |
| 2026-06 | `io_buf_switching_coeff_overlay_2026-06-18` | 7 | 1 | ibis_archive_2026-06.zip | io_buf Switching Coefficient Overlay |
| 2026-06 | `io_buf_switching_coeff_sweep_2026-06-19` | 84 | 2 | ibis_archive_2026-06.zip | io_buf Switching Coefficient Sweep |
| 2026-06 | `io_buf_two_state_gate_model_2026-06-30` | 1,748 | 1 | ibis_archive_2026-06.zip | io_buf Two-State Gate pybis Model |
| 2026-06 | `io_buf_value_match_v2_misalignment_demo_2026-06-26` | 1 | 1 | ibis_archive_2026-06.zip | Value-Matched Replay v2 Misalignment Demo |
| 2026-06 | `io_buf_value_matched_replay_2026-06-23` | 778 | 1 | ibis_archive_2026-06.zip | io_buf Value-Matched Replay Baseline |
| 2026-06 | `io_buf_value_matched_replay_v2_2026-06-26` | 1,142 | 1 | ibis_archive_2026-06.zip | io_buf Corrected Value-Matched Replay v2 |
| 2026-06 | `loose_files/driver_OutputInput_Typical_pre_kukd_3e0bf44.sub` | <1 | 2 | ibis_archive_2026-06.zip | loose file |
| 2026-06 | `loose_files/ngspice_lab_example_config.json` | <1 | 2 | ibis_archive_2026-06.zip | loose file |
| 2026-06 | `my_top_hspice_channel_2026-06-18` | 2 | 1 | ibis_archive_2026-06.zip | my_top / TopXP Simulation Flow |
| 2026-06 | `my_top_hspice_simulation_input_2026-06-18` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `ngspice_lab_hibiki_1160_5pulse` | <1 | 2 | ibis_archive_2026-06.zip | ngspice lab run |
| 2026-06 | `simple_good_bad_overlays_2026-06-12` | 15 | 1 | ibis_archive_2026-06.zip | Simple Good/Bad HSPICE-ngspice Overlays |
| 2026-06 | `sparam_bbs_integration_v1_2026-06-16` | 11 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_bbs_integration_v1_s4p_timeout_smoke_2026-06-16` | 8 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_bbs_quality_tuning_v1_2026-06-17` | 42 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_bbs_quality_tuning_v1_smoke_2026-06-17` | 7 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_cisco_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | Cisco Backplane S-parameter Investigation |
| 2026-06 | `sparam_cisco_delay_parallel_2026-06-08` | 23 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_delay_parallel_batch_2026-06-08` | 351 | 1 | ibis_archive_2026-06.zip | Delay-parallel Batch Results |
| 2026-06 | `sparam_cisco_delay_proto_2026-06-08` | 2 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_delay_reduced_2026-06-08` | 16 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_highorder_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | S-parameter Conversion Quality Study |
| 2026-06 | `sparam_cisco_native_hspice_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_ngspice_forced_2026-06-08` | 5 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_pilot_2026-06-08` | 1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_proto_2026-06-09` | 30 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_proto_2026-06-09_strength025` | 30 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_proto_2026-06-09_strength050` | 30 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_proto_2026-06-09_trimmed_strength050` | 30 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_proto_2026-06-09_trimmed_strength100` | 30 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_cisco_s11_strength_sweep_2026-06-09` | 148 | 1 | ibis_archive_2026-06.zip | S11 Strength Sweep |
| 2026-06 | `sparam_cisco_stage_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | S-parameter Conversion Quality Study |
| 2026-06 | `sparam_conversion_quality_2026-06-08` | 2,172 | 2 | ibis_archive_2026-06.zip | S-parameter Conversion Quality Study |
| 2026-06 | `sparam_conversion_quality_2026-06-08_smoke` | 4 | 1 | ibis_archive_2026-06.zip | S-parameter Conversion Quality Study |
| 2026-06 | `sparam_molex_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_ngspice_flow_optimized_2026-06-08` | <1 | 1 | ibis_archive_2026-06.zip | Optimized ngspice S-parameter Flow |
| 2026-06 | `sparam_rx_trust_v2_2026-06-11` | 1,973 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_rx_trust_v2_cisco_smoke_2026-06-10` | 25 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_rx_trust_v2_s2p_smoke_2026-06-10` | 16 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_s2p_reduced_2026-06-09` | 11 | 1 | ibis_archive_2026-06.zip | 2-port Reduced S-parameter Prototype |
| 2026-06 | `sparam_trust_workflow_calibration_v1_2026-06-09` | 104 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_calibration_v1_fast_2026-06-09` | 999 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_calibration_v1_smoke_cisco_2026-06-09` | 19 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_calibration_v1_smoke_s2p_2026-06-09` | 3 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_ngspice_smoke_2026-06-09` | <1 | 1 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_ngspice_smoke_2026-06-09_v3` | <1 | 1 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_ngspice_smoke_2026-06-09_v3_enf` | <1 | 1 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_s2p_smoke_2026-06-09` | <1 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_s2p_smoke_2026-06-09_b` | 2 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_smoke_2026-06-09` | <1 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_smoke_2026-06-09_b` | <1 | 1 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_smoke_2026-06-09_c` | 8 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_reduced_smoke_2026-06-09_d` | 11 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_selected_smoke_2026-06-09` | 2 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_selected_smoke_warn_2026-06-09` | 2 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_trust_workflow_smoke_2026-06-09` | <1 | 1 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-12` | 3 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-12_cisco_smoke` | <1 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-12_expanded_pilot` | 18 | 2 | ibis_archive_2026-06.zip | Expanded scikit-rf Vector-Fit Pilot Findings |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight` | <1 | 2 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2` | 81 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v1_2026-06-17_overnight` | 10 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_vector_fit_campaign_v2_edge_metric_smoke_2026-06-18` | <1 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18` | 388 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_smoke2_2026-06-18` | 6 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_smoke_2026-06-18` | <1 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_timeout_smoke_2026-06-18` | <1 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_topk_smoke_2026-06-18` | 9 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_workers_smoke2_2026-06-18` | <1 | 2 | ibis_archive_2026-06.zip | scikit-rf Vector Fitting Campaign |
| 2026-06 | `sparam_vector_fit_campaign_v2_workers_smoke_2026-06-18` | <1 | 1 | ibis_archive_2026-06.zip | (generated README; producer not found) |
| 2026-06 | `sparam_view_trust_cisco_smoke2_2026-06-10` | 24 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_view_trust_cisco_smoke3_2026-06-10` | 10 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_view_trust_cisco_smoke_2026-06-10` | 28 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `sparam_view_trust_smoke_2026-06-10` | 11 | 2 | ibis_archive_2026-06.zip | ngspice S-parameter Trust Workflow |
| 2026-06 | `status_bucket_overlays_2026-06-12` | 12 | 1 | ibis_archive_2026-06.zip | Status-Bucket HSPICE-ngspice Overlays |
| 2026-06 | `visual_support_pack_2026-06-12` | 6 | 1 | ibis_archive_2026-06.zip | Visual Support Pack |
| 2026-07 | `ex2_slow_fast_gate_state_comparison_2026-07-28` | 922 | 1 | ibis_archive_2026-07.zip | ex2 Slow/Fast IBIS and Gate-State Experiment |
| 2026-07 | `figure_editor_demo_2026-07-30` | <1 | 2 | ibis_archive_2026-07.zip | Figure Editor Demo |
| 2026-07 | `ibis_kukd_handwritten_notes_deck` | 95 | 2 | ibis_archive_2026-07.zip | IBIS Ku/Kd Handwritten Notes Deck |
| 2026-07 | `inv_chain_forced_midtransition_reversal_2026-07-28` | 237 | 1 | ibis_archive_2026-07.zip | inv_chain Forced Mid-Transition Reversal Study |
| 2026-07 | `inv_chain_gate_state_clean_comparison_2026-07-27` | 97 | 2 | ibis_archive_2026-07.zip | inv_chain Clean IBIS / pybis / Transistor Comparison |
| 2026-07 | `inv_chain_s2ibispy_slow_fast_comparison_2026-07-27` | 302 | 1 | ibis_archive_2026-07.zip | inv_chain Slow/Fast IBIS Comparison Ladder |
| 2026-07 | `inv_chain_transistor_visible_reversal_2026-07-28` | 723 | 1 | ibis_archive_2026-07.zip | inv_chain Transistor-Visible Reversal Sweep |
| 2026-07 | `io_buf_correct_hspice_reference_waveforms_2026-07-23` | 5 | 2 | ibis_archive_2026-07.zip | Corrected io_buf HSPICE Reference Waveforms |
| 2026-07 | `io_buf_correct_hspice_vs_pybis_2026-07-23` | 83 | 2 | ibis_archive_2026-07.zip | Corrected HSPICE References versus pybis |
| 2026-07 | `io_buf_hspice_capacitance_driver_strength_2026-07-23` | 18 | 2 | ibis_archive_2026-07.zip | io_buf HSPICE Capacitance and Driver-Strength Investigation |
| 2026-07 | `io_buf_inv_chain_dual_residual_hybrid_comparison_2026-07-27` | 652 | 1 | ibis_archive_2026-07.zip | Legacy-Normal / Gate-State-on-Reversal Comparison |
| 2026-07 | `io_buf_inv_chain_ibis_waveform_failure_analysis_2026-07-28` | 3 | 1 | ibis_archive_2026-07.zip | io_buf vs inv_chain: IBIS Waveform Failure Analysis |
| 2026-07 | `io_buf_inv_chain_reversal_hybrid_comparison_2026-07-27` | 514 | 1 | ibis_archive_2026-07.zip | Legacy-Normal / Gate-State-on-Reversal Comparison |
| 2026-07 | `three_buffer_common_pulse_sweep_2026-07-30` | 1,169 | 1 | ibis_archive_2026-07.zip | Three-Buffer Common-Pulse Sweep |
| 2026-07 | `three_buffer_common_pulse_sweep_edge50ps_2026-07-30` | 1,319 | 2 | ibis_archive_2026-07.zip | Three-Buffer Common-Pulse Sweep |
| 2026-07 | `three_buffer_gate_voltage_vs_kukd_2026-07-31` | 5 | 1 | ibis_archive_2026-07.zip | Three-Buffer Gate Voltage vs. Ku/Kd Figures |
| 2026-07 | `three_buffer_gate_vs_hybrid_2026-07-28` | 345 | 1 | ibis_archive_2026-07.zip | Three-Buffer Full Gate-State vs Reversal Hybrid |
| 2026-07 | `three_buffer_prbs_hybrid_v2_2026-07-31` | 54 | 1 | ibis_archive_2026-07.zip | Three-Buffer PRBS Hybrid V2 |
| 2026-07 | `three_buffer_prbs_hybrid_v2_continuous_anchor_2026-07-31` | 60 | 2 | ibis_archive_2026-07.zip | Three-Buffer PRBS Hybrid V2 |
| 2026-07 | `three_buffer_prbs_hybrid_v2_latched_pilot_2026-07-31` | 5 | 1 | ibis_archive_2026-07.zip | Three-Buffer PRBS Hybrid V2 |
| 2026-07 | `three_buffer_prbs_phase1_2026-07-31` | 109 | 2 | ibis_archive_2026-07.zip | Three-Buffer Direct-Load PRBS7 Phase 1 |
| 2026-08 | `_ab_fixed` | 63 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_ab_level` | 63 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_baseline_edgecmd` | 346 | 2 | ibis_archive_2026-08_part4.zip | Find HSPICE runs built on the ngspice model card. |
| 2026-08 | `_diag_level` | 222 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_iobuf_retarget` | 583 | 2 | ibis_archive_2026-08_part3.zip | (generated README; producer not found) |
| 2026-08 | `_iobuf_stockcard` | 175 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_level_v2` | 2,554 | 2 | ibis_archive_2026-08_part3.zip | (generated README; producer not found) |
| 2026-08 | `_level_v3` | 2,091 | 2 | ibis_archive_2026-08_part3.zip | (generated README; producer not found) |
| 2026-08 | `_m_delaycmd` | <1 | 2 | ibis_archive_2026-08_part2.zip | (generated README; producer not found) |
| 2026-08 | `_m_edgecmd` | 301 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_probe_coeff` | 12 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_probe_legacy` | 11 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_probe_padmatch` | 32 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_probe_v3` | 394 | 2 | ibis_archive_2026-08_part3.zip | (generated README; producer not found) |
| 2026-08 | `_probe_v4` | 246 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `_probe_v5` | 214 | 2 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `external_ibis_adaptive_stress_2026-08-11` | 1,299 | 1 | ibis_archive_2026-08_part3.zip | External IBIS Adaptive Stress Campaign |
| 2026-08 | `external_ibis_adaptive_stress_init_smoke_2026-08-11` | 17 | 1 | ibis_archive_2026-08_part1.zip | External IBIS Adaptive Stress Campaign |
| 2026-08 | `external_ibis_adaptive_stress_smoke_2026-08-11` | 5 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Adaptive Stress Campaign |
| 2026-08 | `external_ibis_algorithm_comparison_2026-08-11` | 1,488 | 1 | ibis_archive_2026-08_part3.zip | External IBIS Algorithm Comparison |
| 2026-08 | `external_ibis_algorithm_comparison_pilot_2026-08-11` | 62 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Algorithm Comparison |
| 2026-08 | `external_ibis_algorithm_pilot_2026-08-11` | <1 | 1 | ibis_archive_2026-08_part2.zip | (generated README; producer not found) |
| 2026-08 | `external_ibis_full_swing_adaptive_inventory_2026-08-07` | <1 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_adaptive_smoke_2026-08-07` | 218 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_adaptive_smoke_v2_2026-08-07` | 49 | 1 | ibis_archive_2026-08_part3.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_adaptive_v2_2026-08-07` | 1,570 | 1 | ibis_archive_2026-08_part3.zip | External IBIS Full-Transition Campaign |
| 2026-08 | `external_ibis_full_swing_all_2026-08-07` | 973 | 1 | ibis_archive_2026-08_part3.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_logging_smoke_2026-08-07` | 2 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_pilot_2026-08-07` | 150 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_sentinel_smoke_2026-08-07` | 2 | 1 | ibis_archive_2026-08_part4.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `external_ibis_full_swing_smoke_2026-08-07` | 7 | 1 | ibis_archive_2026-08_part1.zip | External IBIS Full-Transition Pilot |
| 2026-08 | `full_swing_kukd_comparison_2026-08-27` | <1 | 2 | ibis_archive_2026-08_part4.zip | Full-swing Ku/Kd from three independent sources, on one set of axes. |
| 2026-08 | `ibis_intro_figures_2026-08-25` | 618 | 2 | ibis_archive_2026-08_part3.zip | Full swing: the gate-state model against legacy pybis, on one axis. |
| 2026-08 | `inv_chain_ex2_value_matched_replay_2026-08-04` | 3,701 | 1 | ibis_archive_2026-08_part1.zip | inv_chain and ex2 Value-Matched Replay |
| 2026-08 | `kukd_animation` | 6 | 2 | ibis_archive_2026-08_part2.zip | Animation: how Ku(t) and Kd(t) are extracted from a transistor buffer. |
| 2026-08 | `kukd_fixture_variants_2026-08-28` | 13 | 1 | ibis_archive_2026-08_part4.zip | Does silicon Ku/Kd change when the fixtures themselves change? |
| 2026-08 | `kukd_load_transfer_test_2026-08-28` | 8 | 1 | ibis_archive_2026-08_part4.zip | Does silicon Ku/Kd extracted under two fixtures describe a third load? |
| 2026-08 | `loose_files/baseline_edgecmd.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf short-high silicon depth 0.43] width 972.7 ps` |
| 2026-08 | `loose_files/codex.md` | 2 | 2 | ibis_archive_2026-08_part4.zip | transcript of an 08-19 Codex session (2.4 MB), not a result |
| 2026-08 | `loose_files/depth_sweep.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿  io_buf     short_high    250.0 ps -> depth -0.093  recovery     50.5 ps` |
| 2026-08 | `loose_files/level_v2.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf short-high silicon depth 0.43] width 972.7 ps` |
| 2026-08 | `loose_files/levelcmd.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf short-high silicon depth 0.43] width 972.7 ps` |
| 2026-08 | `loose_files/native_anchor_io_buf.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf]` |
| 2026-08 | `loose_files/native_anchor_sweep.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[inv_chain]` |
| 2026-08 | `loose_files/silicon_anchored.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf short-high silicon depth 0.25] width 785.3 ps` |
| 2026-08 | `loose_files/silicon_kukd_extract.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf short_high 90%] pulse 2896.8 ps` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load__work_2026-08-04.worker.err.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `empty` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load__work_2026-08-04.worker.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `[ex2/slow_1ns] calibration` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_ex2_fast_work_2026-08-04.worker.err.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `empty` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_ex2_fast_work_2026-08-04.worker.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `[ex2/fast_5ps] calibration` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_ex2_slow_work_2026-08-04.worker.err.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `empty` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_ex2_slow_work_2026-08-04.worker.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `[ex2/slow_1ns] calibration` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_inv_fast_work_2026-08-04.worker.err.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `empty` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_inv_fast_work_2026-08-04.worker.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `[inv_chain/fast_5ps] calibration` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_inv_slow_work_2026-08-04.worker.err.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `empty` |
| 2026-08 | `loose_files/three_buffer_pad_matched_replay_load_inv_slow_work_2026-08-04.worker.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `[inv_chain/slow_1ns] calibration` |
| 2026-08 | `loose_files/transistor_anchor_io_buf_refresh.log` | <1 | 2 | ibis_archive_2026-08_part4.zip | run log; first line: `﻿[io_buf]` |
| 2026-08 | `presentation_2026-08-20` | 31 | 1 | ibis_archive_2026-08_part4.zip | One figure per case, flat and numbered, for dropping straight into slides. |
| 2026-08 | `replay_vs_integrator_2026-08-26` | 56 | 2 | ibis_archive_2026-08_part4.zip | One circuit, two gates: integrated and replayed, driving identical pads. |
| 2026-08 | `reversal_discontinuity_2026-08-20` | <1 | 1 | ibis_archive_2026-08_part4.zip | Why some reversal policies will not simulate: the jump they demand. |
| 2026-08 | `silicon_anchored_levelcmd_2026-08-19` | 365 | 1 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `silicon_anchored_shortpulse_2026-08-19` | 1,292 | 1 | ibis_archive_2026-08_part3.zip | Compare pybis against silicon at pulse widths that actually stress silicon. |
| 2026-08 | `silicon_kukd_conditioning_2026-08-27` | 3 | 2 | ibis_archive_2026-08_part4.zip | Ku and Kd on the rising and the falling edge, as separate close-ups. |
| 2026-08 | `silicon_kukd_figures_2026-08-27` | 2 | 2 | ibis_archive_2026-08_part4.zip | Transistor-derived Ku/Kd — representative set |
| 2026-08 | `silicon_kukd_recovery_uniform_2026-08-27` | 17 | 2 | ibis_archive_2026-08_part4.zip | Is the silicon Ku target reachable, or is Ku/Kd itself the limit? |
| 2026-08 | `silicon_recovery_depth_sweep_2026-08-19` | 64 | 1 | ibis_archive_2026-08_part4.zip | Compare pybis against silicon at pulse widths that actually stress silicon. |
| 2026-08 | `silicon_vs_pybis_kukd_figures_2026-08-19` | <1 | 2 | ibis_archive_2026-08_part4.zip | Compare Ku/Kd from silicon against pybis and against HSPICE's IBIS engine. |
| 2026-08 | `three_buffer_gup_gdn_waveforms_2026-08-04` | 5 | 2 | ibis_archive_2026-08_part4.zip | Three-Buffer Direct GUP/GDN Waveforms |
| 2026-08 | `three_buffer_kukd_excursion_analysis_2026-08-04` | <1 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Ku/Kd Excursion Audit |
| 2026-08 | `three_buffer_kukd_excursion_decomposition_2026-08-04` | 4 | 2 | ibis_archive_2026-08_part4.zip | Three-Buffer Ku/Kd Excursion Decomposition |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_2026-08-18` | 646 | 1 | ibis_archive_2026-08_part3.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_pilot_2026-08-18` | <1 | 1 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_pilot_2026-08-19` | 379 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_pilot_final_2026-08-19` | 379 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_smoke2_2026-08-19` | 77 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_smoke3_2026-08-19` | 89 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_smoke4_2026-08-19` | <1 | 1 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_smoke5_2026-08-19` | 89 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep With Hybrid |
| 2026-08 | `three_buffer_loaded_swing_stress_sweep_hybrid_v3_smoke_2026-08-19` | <1 | 1 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `three_buffer_output_level_reversal_screen_2026-08-11` | 66 | 2 | ibis_archive_2026-08_part2.zip | Three-Buffer True Output-Level Reversal Screen |
| 2026-08 | `three_buffer_pad_matched_replay_2026-08-04` | 6,673 | 2 | ibis_archive_2026-08_part2.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_load__work_2026-08-04` | 248 | 1 | ibis_archive_2026-08_part4.zip | (generated README; producer not found) |
| 2026-08 | `three_buffer_pad_matched_replay_load_ex2_fast_work_2026-08-04` | 2,712 | 1 | ibis_archive_2026-08_part3.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_load_ex2_slow_work_2026-08-04` | 1,567 | 1 | ibis_archive_2026-08_part3.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_load_inv_fast_work_2026-08-04` | 3,583 | 1 | ibis_archive_2026-08_part2.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_load_inv_slow_work_2026-08-04` | 2,994 | 1 | ibis_archive_2026-08_part2.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_load_portability_2026-08-04` | 16,275 | 2 | ibis_archive_2026-08_part1.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_inv_chain_custom_2026-08-11` | 2,158 | 1 | ibis_archive_2026-08_part3.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_midtransition_2026-08-11` | 5,696 | 1 | ibis_archive_2026-08_part2.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_pilot_2026-08-04` | 168 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_pilot_high_2026-08-04` | 130 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_pilot_io_fast_2026-08-04` | 160 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_pilot_low_2026-08-04` | 142 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Pad-Voltage-Matched Replay |
| 2026-08 | `three_buffer_pad_matched_replay_v2_true_output_2026-08-11` | 393 | 2 | ibis_archive_2026-08_part4.zip | Build clean isolated-pulse evidence for true output-level reversals. |
| 2026-08 | `three_buffer_prbs_pad_matched_v2_stress_2026-08-11` | 25 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Stressed PRBS7: Pad-Matched Replay V2 |
| 2026-08 | `three_buffer_prbs_pad_matched_v2_true_output_2026-08-11` | 25 | 2 | ibis_archive_2026-08_part4.zip | Three-Buffer Stressed PRBS7: Pad-Matched Replay V2 |
| 2026-08 | `three_buffer_single_true_output_reversal_2026-08-11` | 981 | 1 | ibis_archive_2026-08_part2.zip | Three-Buffer Single True Output-Level Reversal |
| 2026-08 | `three_buffer_transistor_anchored_refresh_2026-08-19` | 333 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer Loaded-Swing Stress Sweep |
| 2026-08 | `three_buffer_true_output_reversal_2026-08-11` | <1 | 1 | ibis_archive_2026-08_part4.zip | Three-Buffer True Output-Level Mid-Transition Reversal |
| 2026-08 | `three_buffer_voltage_matching_v2_clear_results_2026-08-14` | 34 | 1 | ibis_archive_2026-08_part4.zip | Voltage-Matching V2: Clear Three-Buffer Results |
| 2026-08 | `two_study_error_decomposition_2026-08-19` | <1 | 1 | ibis_archive_2026-08_part4.zip | Three-buffer stress evidence, split into two studies |
| 2026-08 | `voltage_matching_explainer_deck_2026-08-14` | 6 | 1 | ibis_archive_2026-08_part3.zip | Voltage Matching V2 Explainer Deck |
| 2026-09 | `ccomp_accumulation_2026-09-04` | 39 | 2 | ibis_archive_2026-09.zip | The outward timing accumulation is C_comp |
| 2026-09 | `cv_capacitance_2026-09-04` | 11 | 2 | ibis_archive_2026-09.zip | The accumulation follows C_comp's *size*, not its bias-dependence |
| 2026-09 | `defect_b_full_swing_2026-09-03` | 107 | 2 | ibis_archive_2026-09.zip | Defect B is stress-specific: the command layer is fine on a clean edge |
| 2026-09 | `delay_cmd_timing_2026-09-03` | <1 | 2 | ibis_archive_2026-09.zip | Does delay_cmd fix the timing shift? No — and the shift is smaller than quoted |
| 2026-09 | `engine_overlay_2026-09-04` | 1 | 2 | ibis_archive_2026-09.zip | The same pybis model in both engines, pad against pad. |
| 2026-09 | `ex2_full_swing_control_2026-09-04` | 7 | 2 | ibis_archive_2026-09.zip | The unstressed ex2 bench that the accumulation study was missing. |
| 2026-09 | `ex2_opendrain_full_swing_2026-09-03` | 3 | 2 | ibis_archive_2026-09.zip | Open-drain ex2: transistor vs native IBIS vs pybis, on a pull-up load. |
| 2026-09 | `fixture_characterisation_2026-09-04` | 2 | 2 | ibis_archive_2026-09.zip | What the fixtures do to the V-T waveforms, and to the Ku/Kd solved from them. |
| 2026-09 | `golden_waveform_ex2_2026-09-03` | 39 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `golden_waveform_io_buf_2026-09-03` | 37 | 2 | ibis_archive_2026-09.zip | Golden-waveform test across all three buffers — and what it says about defect B |
| 2026-09 | `golden_waveform_test_2026-09-03` | 19 | 2 | ibis_archive_2026-09.zip | Golden-waveform test: pybis handles C_comp correctly |
| 2026-09 | `inv_chain_variants_full_swing_2026-09-03` | 23 | 2 | ibis_archive_2026-09.zip | Do the models track silicon when the silicon changes? |
| 2026-09 | `kd_decompose_2026-09-04` | 4 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `ku_decompose_2026-09-04` | 4 | 2 | ibis_archive_2026-09.zip | Scale the falling residual by how far the transition actually got. |
| 2026-09 | `ku_excess_decompose_2026-09-07` | 58 | 2 | ibis_archive_2026-09.zip | Where does our excess Ku live -- the gate map, or the residual? |
| 2026-09 | `ku_overshoot_2026-09-04` | 23 | 2 | ibis_archive_2026-09.zip | Why does our Ku keep rising after the reversal, when native's turns around? |
| 2026-09 | `kukd_fixture_variants_2026-08-28` | 13 | 2 | ibis_archive_2026-09.zip | 09-04 re-run of the 2026-08 copy: same inputs, CSV and plots; only the HSPICE outputs differ |
| 2026-09 | `native_ccomp_sweep_2026-09-04` | 2 | 2 | ibis_archive_2026-09.zip | Replace the fixed C_comp with the netlist's measured C(V), and re-measure. |
| 2026-09 | `native_reversal_entry_2026-09-07` | <1 | 2 | ibis_archive_2026-09.zip | What does native do with its falling trajectory when the pulse is truncated? |
| 2026-09 | `native_stress_law_2026-09-03` | <1 | 2 | ibis_archive_2026-09.zip | How native IBIS and pybis handle stressed pulses — measured, not assumed |
| 2026-09 | `native_vs_solved_ku_2026-09-04` | <1 | 2 | ibis_archive_2026-09.zip | Solve the transistor's Ku/Kd at full swing -- the reference that never existed. |
| 2026-09 | `native_vt_table_selection_2026-09-03` | 6 | 2 | ibis_archive_2026-09.zip | How much V-T data is native IBIS actually using, and does it matter? |
| 2026-09 | `native_waveform_count_2026-09-04` | 1 | 2 | ibis_archive_2026-09.zip | The stress pedestal: one V-T trajectory cannot represent a partial transition |
| 2026-09 | `pad_capacitance_2026-09-04` | <1 | 2 | ibis_archive_2026-09.zip | The buffer's real pad capacitance versus bias, from the transistor netlist. |
| 2026-09 | `pd_command_probe_2026-09-04` | 5 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `pu_off_devices_2026-09-04` | 113 | 2 | ibis_archive_2026-09.zip | Does the pull-up off-delay explain the pedestal on the other two buffers? |
| 2026-09 | `pu_off_sweep_2026-09-04` | 108 | 2 | ibis_archive_2026-09.zip | The command gate eats a fixed slice out of every pulse |
| 2026-09 | `pybis_ccomp_converged_2026-09-03` | 377 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `pybis_ccomp_validation_2026-09-03` | 36 | 2 | ibis_archive_2026-09.zip | Validating the C_comp fix: net-positive, but not the whole story |
| 2026-09 | `pybis_engine_model_decoupling_2026-09-03` | <1 | 2 | ibis_archive_2026-09.zip | Decoupling the SPICE engine from the IBIS implementation |
| 2026-09 | `pybis_lag_converged_2026-09-03` | 96 | 2 | ibis_archive_2026-09.zip | The same pybis model in both engines, pad against pad. |
| 2026-09 | `pybis_lag_localization_2026-09-03` | 4 | 2 | ibis_archive_2026-09.zip | The pybis lag and the ~3x gap are one thing: an output-stage delay |
| 2026-09 | `residual_reindex_2026-09-04` | 16 | 2 | ibis_archive_2026-09.zip | Re-indexing the residual table: the first lever that moves the pedestal |
| 2026-09 | `residual_rescale_time_2026-09-04` | 79 | 2 | ibis_archive_2026-09.zip | Two derived corrections that halve the stress error |
| 2026-09 | `residual_scaled_2026-09-04` | 54 | 2 | ibis_archive_2026-09.zip | The stress pedestal is the Kd residual, and it is twice too large |
| 2026-09 | `s2ibispy_edge_rate_sweep_2026-09-02` | 56 | 2 | ibis_archive_2026-09.zip | s2ibispy: what is fixed, and what has to be chosen per buffer |
| 2026-09 | `s2ibispy_parameter_selection_ex2_fast_5ps_2026-09-02` | 61 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `s2ibispy_parameter_selection_inv_chain_fast_5ps_2026-09-02` | 62 | 2 | ibis_archive_2026-09.zip | (generated README; producer not found) |
| 2026-09 | `s2ibispy_parameter_selection_io_buf_50ps_2026-09-02` | 70 | 2 | ibis_archive_2026-09.zip | Parameter selection across all three buffers |
| 2026-09 | `stress_shapes_2026-09-03` | <1 | 2 | ibis_archive_2026-09.zip | Looking at the stressed waveform shapes — which we had never done |
| 2026-09 | `timing_shift_decomposition_2026-09-03` | <1 | 2 | ibis_archive_2026-09.zip | The timing shift: how much is stress, and how much was always there |
| 2026-09 | `two_fixture_conditioning_2026-09-04` | <1 | 2 | ibis_archive_2026-09.zip | Is the two-fixture Ku/Kd solve ill-conditioned on ex2? Measured: no. |
| 2026-09 | `variant_family_overlay_2026-09-04` | 5 | 2 | ibis_archive_2026-09.zip | Overlay every variant in a family at the same depth target. |
| 2026-09 | `variant_stress_depth_2026-09-03` | 221 | 2 | ibis_archive_2026-09.zip | Does the timing shift grow under stress? Yes — on all nine variants |
| 2026-09 | `variant_timing_offset_2026-09-03` | 30 | 2 | ibis_archive_2026-09.zip | The timing offset is mostly not ours — it is the IBIS format |
| undated | `_scratch_inv_chain` | <1 | 2 | ibis_archive_undated.zip | (generated README; producer not found) |
| undated | `presentation_toolkit_demo` | <1 | 1 | ibis_archive_undated.zip | Reusable Presentation Toolkit Demo |
| undated | `tmp_coeff_state_check` | <1 | 1 | ibis_archive_undated.zip | (generated README; producer not found) |
