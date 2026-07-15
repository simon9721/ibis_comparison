# io_buf Two-State Gate pybis Model

This study tests an opt-in hidden-gate pybis model. The normal complete-edge coefficient reconstruction is the first gate: if the model cannot reproduce original `Ku/Kd` tables, short-pulse results are diagnostic only.

## Headline Finding

- The original single-map PWL two-state implementation is **not validated** because it fails the normal complete-edge `Ku/Kd` reconstruction gate.
- This rerun adds direction-specific on/off maps plus a Kd rate-residual candidate, then applies the same normal gate before short-pulse interpretation.
- Direction-specific maps plus the Kd residual now pass the offline complete-edge table reconstruction gate, which is real structural progress.
- The same residual model is still **not default-ready** in transient: the normal long-pulse case is worse than legacy, and short-high Kd recovery remains wrong even when Kd undershoot is restored.
- This update adds two retrigger-aware Kd recovery-onset candidates. They keep the same directional maps/residual, but route detected short-high pulldown re-turn-on through an IBIS-derived mean or fast recovery delay.
- The mean recovery candidate confirms the missing lever is Kd onset timing: it improves short-high Kd RMSE without materially changing the long-pulse control. It still is **not default-ready** because one fixed recovery delay is early for some widths and late for others.
- Short-low behavior improves more than short-high behavior, which says the remaining problem is directional/retrigger recovery, not just static map shape.
- A short-pulse pad improvement is still not enough; `Ku` and `Kd` must also agree, especially the Kd undershoot and recovery timing.
- Cached transistor-pad recovery timing now checks the Kd-hold question at pad level. The transistor `io_buf.sp` pad returns much sooner than native-IBIS Kd recovery on the short-high cases, so the ~2 ns native Kd hold should be treated as a native-IBIS playback target unless the transistor/reference setup mismatch can be reconciled.

## Normal Ku/Kd Reconstruction Gate

- Original PWL gate result: `FAIL`
- Directional-map gate result: `FAIL`
- Directional + residual gate result: `PASS`
- Worst PWL table RMSE / max error: `0.055843` / `0.20467`
- Worst directional table RMSE / max error: `0.03081` / `0.073894`
- Worst directional + residual table RMSE / max error: `0.019939` / `0.048685`
- Kd rate residual gain: `0.00023869148148216097` ns
- PU on/off tau: `1.2844495834781395` / `0.36311155305263615` ns
- PD on/off tau: `0.27496289583913525` / `0.23728160091864137` ns

## Measured Transient Takeaways

- Long-pulse legacy pad / Ku / Kd RMSE: `5.289 mV`, `0.00434`, `0.00561`.
- Long-pulse directional+residual pad / Ku / Kd RMSE: `18.739 mV`, `0.01886`, `0.01110`.
- Long-pulse mean-recovery pad / Ku / Kd RMSE: `18.738 mV`, `0.01886`, `0.01271`.
- `short_pulse_1ns_high`: directional+residual pad improves to `21.914 mV`, but Kd RMSE remains `0.48754`.
- `short_pulse_1ns_high` with mean recovery: Kd RMSE improves to `0.33736`, but status remains `PAD_ONLY_IMPROVEMENT` because Kd is still not coefficient-correct.
- `short_pulse_2ns_high` with mean recovery: Kd RMSE improves from `0.23513` to `0.11111`.
- `short_pulse_2ns_low`: directional+residual reaches status `GOOD` with pad / Ku / Kd RMSE `23.271 mV`, `0.02141`, `0.01319`.
- Kd recovery timing details are saved in `kd_recovery_diagnostics/recovery_timing_summary.csv`; the fixed mean/fast delays improve onset but do not yet solve all pulse widths.
- Windowed Kd error split for `short_pulse_1ns_high` mean recovery, measured from reverse edge to active-window end: total RMSE `0.38356`, pre-50/onset-window RMSE `0.42993`, post-both-50 RMSE `0.14847`, pre-50 SSE fraction `96.5%`. Classification hint: `pre_50_dominated_with_shape_tail`.
- HSPICE Kd recovery extraction shows apparent min-to-final tau spread `1.720x`, but the actual 10%-90% main-slope tau spread is only `1.086x`. This says the remaining short-high issue is mostly recovery staging/early trajectory, not a simple fixed tau change.
- HSPICE hold-time extraction prefers a width-drift law over one constant hold: `T_hold50 = 1.7153 + 0.3119 * pulse_width` ns, with H2 residual `21.5 ps` versus constant-hold residual `195.7 ps`. Verdict: `HOLD_PLUS_WIDTH_DRIFT_PREFERRED`.
- GDN-keyed hold extraction shows the present `GDN@reverse` is not the right latch variable: primary GDN fit residual `84.0 ps`, origin-forced residual `1597.8 ps`, verdict `GDN_AT_REVERSE_COLLAPSES_WIDTHS`. The current GDN state collapses 500 ps and 1 ns pulses to the same value.
- Held-out command-age validation on a new `1.5 ns` short-high HSPICE case gives error `+49.4 ps` against a `+/-30 ps` gate. Verdict: `FAIL`. This means the simple two-parameter command-age line should not be implemented as the next candidate without a better law.
- Reference-truth audit changes the framing: HSPICE native IBIS and transistor `io_buf.sp` differ by `525.5 mV` on the long-pulse pad and `40.1 mV` on `short_pulse_1ns_high`. Coefficient RMSE should be read as native-IBIS playback agreement, not automatically transistor truth.
- The double-toggle case does **not** prove full-table commitment because it ends with a sustained final high. Pure short-high native-IBIS Ku peaks are partial, so the remaining reference concern is specifically Kd recovery/hold behavior.
- Transistor pad recovery timing does **not** show the native-IBIS Kd hold: transistor pad 50% return occurs at `0.158 / 0.176 / 0.264 ns` after the reverse edge for `0.5 / 1 / 2 ns` short-high pulses, while native-IBIS Kd 50% recovery occurs at `1.851 / 2.057 / 2.329 ns`.
- This makes the native-IBIS Kd hold an HSPICE native-IBIS playback target, not proven transistor behavior. The safest conclusion is now: the two-state model is close to transistor pad behavior on short-high, but still does not reproduce native-IBIS Kd playback.

Figures:

- `fit_diagnostics/ku_kd_table_reconstruction.png`
- `fit_diagnostics/gate_to_coefficient_maps.png`
- `fit_diagnostics/directional_maps_and_residual.png`

## Transient Case Summary

| Case | Flow | Status | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd min | Coeff range ok |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.0129 | -0.0718 |  |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | PAD_REFERENCE | 525.498 | n/a | n/a | n/a | n/a |  |
| edge_1ps_base_50r_2pf | ngspice_legacy | GOOD | 5.289 | 0.00434 | 0.00561 | 1.0120 | -0.0718 | True |
| edge_1ps_base_50r_2pf | ngspice_value_match_v2 | GOOD | 5.211 | 0.00392 | 0.00561 | 1.0125 | -0.0718 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_identity | CHECK | 90.485 | 0.07110 | 0.04682 | 0.9950 | 0.0011 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_pwl | CHECK | 66.635 | 0.04422 | 0.02855 | 0.9956 | 0.0011 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_hybrid | CHECK | 60.267 | 0.03871 | 0.02349 | 1.0100 | -0.0199 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_directional | CHECK | 25.407 | 0.01918 | 0.02787 | 0.9957 | 0.0011 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_directional_residual | WARN | 18.739 | 0.01886 | 0.01110 | 0.9957 | -0.0719 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_directional_residual_recover_mean | WARN | 18.738 | 0.01886 | 0.01271 | 0.9957 | -0.0719 | True |
| edge_1ps_base_50r_2pf | ngspice_two_state_directional_residual_recover_fast | WARN | 18.737 | 0.01886 | 0.01356 | 0.9957 | -0.0719 | True |
| short_pulse_500ps_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.0466 | -0.0225 |  |
| short_pulse_500ps_high | hspice_transistor_sp | PAD_REFERENCE | 30.529 | n/a | n/a | n/a | n/a |  |
| short_pulse_500ps_high | ngspice_legacy | CHECK | 678.863 | 0.50245 | 0.57847 | 1.0125 | -0.0717 | True |
| short_pulse_500ps_high | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 20.176 | 0.02191 | 0.59158 | 0.0276 | 0.9470 | True |
| short_pulse_500ps_high | ngspice_two_state_identity | PAD_ONLY_IMPROVEMENT | 14.958 | 0.01535 | 0.62591 | 0.0304 | 0.0028 | True |
| short_pulse_500ps_high | ngspice_two_state_pwl | PAD_ONLY_IMPROVEMENT | 30.082 | 0.02096 | 0.62823 | 0.0586 | 0.0021 | True |
| short_pulse_500ps_high | ngspice_two_state_hybrid | CHECK | 677.453 | 0.44514 | 0.52922 | 1.0102 | -0.0721 | True |
| short_pulse_500ps_high | ngspice_two_state_directional | PAD_ONLY_IMPROVEMENT | 40.880 | 0.02332 | 0.62984 | 0.0594 | 0.0029 | True |
| short_pulse_500ps_high | ngspice_two_state_directional_residual | PAD_ONLY_IMPROVEMENT | 40.997 | 0.02332 | 0.61846 | 0.0594 | -0.0151 | True |
| short_pulse_500ps_high | ngspice_two_state_directional_residual_recover_mean | PAD_ONLY_IMPROVEMENT | 28.327 | 0.02332 | 0.51536 | 0.0594 | 0.0144 | True |
| short_pulse_500ps_high | ngspice_two_state_directional_residual_recover_fast | PAD_ONLY_IMPROVEMENT | 13.506 | 0.02332 | 0.45753 | 0.0594 | 0.0785 | True |
| short_pulse_1ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.0746 | -0.0632 |  |
| short_pulse_1ns_high | hspice_transistor_sp | PAD_REFERENCE | 40.136 | n/a | n/a | n/a | n/a |  |
| short_pulse_1ns_high | ngspice_legacy | CHECK | 653.256 | 0.47041 | 0.50381 | 1.0125 | -0.0718 | True |
| short_pulse_1ns_high | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 25.579 | 0.02652 | 0.63487 | 0.0310 | 0.9180 | True |
| short_pulse_1ns_high | ngspice_two_state_identity | PAD_ONLY_IMPROVEMENT | 19.177 | 0.02601 | 0.48760 | 0.1019 | 0.0013 | True |
| short_pulse_1ns_high | ngspice_two_state_pwl | PAD_ONLY_IMPROVEMENT | 35.015 | 0.02682 | 0.49053 | 0.0586 | 0.0012 | True |
| short_pulse_1ns_high | ngspice_two_state_hybrid | CHECK | 442.535 | 0.30962 | 0.52615 | 1.0102 | -0.0719 | True |
| short_pulse_1ns_high | ngspice_two_state_directional | PAD_ONLY_IMPROVEMENT | 42.963 | 0.02322 | 0.49383 | 0.0696 | 0.0013 | True |
| short_pulse_1ns_high | ngspice_two_state_directional_residual | PAD_ONLY_IMPROVEMENT | 21.914 | 0.02161 | 0.48754 | 0.0696 | -0.0185 | True |
| short_pulse_1ns_high | ngspice_two_state_directional_residual_recover_mean | PAD_ONLY_IMPROVEMENT | 22.172 | 0.02161 | 0.33736 | 0.0696 | -0.0109 | True |
| short_pulse_1ns_high | ngspice_two_state_directional_residual_recover_fast | PAD_ONLY_IMPROVEMENT | 22.837 | 0.02161 | 0.43877 | 0.0696 | -0.0109 | True |
| short_pulse_2ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.5432 | -0.0720 |  |
| short_pulse_2ns_high | hspice_transistor_sp | PAD_REFERENCE | 399.310 | n/a | n/a | n/a | n/a |  |
| short_pulse_2ns_high | ngspice_legacy | CHECK | 361.362 | 0.28330 | 0.23142 | 1.0125 | -0.0724 | True |
| short_pulse_2ns_high | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 243.549 | 0.15234 | 0.58037 | 0.2808 | -0.0192 | True |
| short_pulse_2ns_high | ngspice_two_state_identity | CHECK | 139.900 | 0.10077 | 0.22560 | 0.5827 | 0.0011 | True |
| short_pulse_2ns_high | ngspice_two_state_pwl | CHECK | 66.702 | 0.05922 | 0.22845 | 0.5661 | 0.0011 | True |
| short_pulse_2ns_high | ngspice_two_state_hybrid | CHECK | 59.924 | 0.05721 | 0.23381 | 0.5646 | -0.0189 | True |
| short_pulse_2ns_high | ngspice_two_state_directional | CHECK | 77.328 | 0.06972 | 0.23583 | 0.7186 | 0.0011 | True |
| short_pulse_2ns_high | ngspice_two_state_directional_residual | CHECK | 93.587 | 0.06963 | 0.23513 | 0.7186 | -0.0698 | True |
| short_pulse_2ns_high | ngspice_two_state_directional_residual_recover_mean | CHECK | 93.670 | 0.06963 | 0.11111 | 0.7186 | -0.0698 | True |
| short_pulse_2ns_high | ngspice_two_state_directional_residual_recover_fast | CHECK | 93.703 | 0.06963 | 0.33466 | 0.7186 | -0.0698 | True |
| double_toggle_1ps | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.0024 | -0.0064 |  |
| double_toggle_1ps | hspice_transistor_sp | PAD_REFERENCE | 233.892 | n/a | n/a | n/a | n/a |  |
| double_toggle_1ps | ngspice_legacy | CHECK | 567.523 | 0.45138 | 0.62934 | 0.7684 | 0.0092 | True |
| double_toggle_1ps | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 566.841 | 0.45030 | 0.62627 | 0.7678 | 0.0104 | True |
| double_toggle_1ps | ngspice_two_state_identity | CHECK | 511.486 | 0.41456 | 0.62590 | 0.7251 | 0.0027 | True |
| double_toggle_1ps | ngspice_two_state_pwl | CHECK | 548.884 | 0.44202 | 0.62886 | 0.8000 | 0.0021 | True |
| double_toggle_1ps | ngspice_two_state_hybrid | CHECK | 552.653 | 0.44424 | 0.62696 | 0.7639 | 0.0098 | True |
| double_toggle_1ps | ngspice_two_state_directional | CHECK | 569.095 | 0.45179 | 0.62925 | 0.7649 | 0.0028 | True |
| double_toggle_1ps | ngspice_two_state_directional_residual | CHECK | 569.294 | 0.45179 | 0.62825 | 0.7649 | 0.0103 | True |
| double_toggle_1ps | ngspice_two_state_directional_residual_recover_mean | CHECK | 569.294 | 0.45179 | 0.62825 | 0.7649 | 0.0103 | True |
| double_toggle_1ps | ngspice_two_state_directional_residual_recover_fast | CHECK | 569.294 | 0.45179 | 0.62825 | 0.7649 | 0.0103 | True |
| short_pulse_500ps_low | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.0135 | -0.0725 |  |
| short_pulse_500ps_low | hspice_transistor_sp | PAD_REFERENCE | 612.609 | n/a | n/a | n/a | n/a |  |
| short_pulse_500ps_low | ngspice_legacy | CHECK | 506.091 | 0.38881 | 0.55164 | 1.0101 | -0.0285 | True |
| short_pulse_500ps_low | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 506.586 | 0.38870 | 0.55147 | 1.0125 | -0.0285 | True |
| short_pulse_500ps_low | ngspice_two_state_identity | CHECK | 318.945 | 0.27591 | 0.02717 | 0.9554 | 0.0011 | True |
| short_pulse_500ps_low | ngspice_two_state_pwl | CHECK | 351.607 | 0.28883 | 0.02235 | 0.9870 | 0.0011 | True |
| short_pulse_500ps_low | ngspice_two_state_hybrid | CHECK | 507.111 | 0.36246 | 0.52745 | 1.0095 | -0.0192 | True |
| short_pulse_500ps_low | ngspice_two_state_directional | CHECK | 364.165 | 0.29382 | 0.02161 | 0.9887 | 0.0011 | True |
| short_pulse_500ps_low | ngspice_two_state_directional_residual | CHECK | 366.414 | 0.29519 | 0.02171 | 0.9887 | -0.0391 | True |
| short_pulse_500ps_low | ngspice_two_state_directional_residual_recover_mean | CHECK | 366.387 | 0.29519 | 0.02171 | 0.9887 | -0.0391 | True |
| short_pulse_500ps_low | ngspice_two_state_directional_residual_recover_fast | CHECK | 366.386 | 0.29519 | 0.02171 | 0.9887 | -0.0391 | True |
| short_pulse_1ns_low | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.0135 | -0.0717 |  |
| short_pulse_1ns_low | hspice_transistor_sp | PAD_REFERENCE | 546.148 | n/a | n/a | n/a | n/a |  |
| short_pulse_1ns_low | ngspice_legacy | CHECK | 385.094 | 0.30691 | 0.49584 | 1.0101 | -0.0718 | True |
| short_pulse_1ns_low | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 384.501 | 0.30658 | 0.49588 | 1.0125 | -0.0718 | True |
| short_pulse_1ns_low | ngspice_two_state_identity | CHECK | 325.031 | 0.28830 | 0.02841 | 0.9554 | 0.0011 | True |
| short_pulse_1ns_low | ngspice_two_state_pwl | CHECK | 357.538 | 0.30178 | 0.02407 | 0.9870 | 0.0011 | True |
| short_pulse_1ns_low | ngspice_two_state_hybrid | CHECK | 394.947 | 0.31047 | 0.46914 | 1.0095 | -0.0192 | True |
| short_pulse_1ns_low | ngspice_two_state_directional | CHECK | 365.794 | 0.30454 | 0.02341 | 0.9887 | 0.0011 | True |
| short_pulse_1ns_low | ngspice_two_state_directional_residual | CHECK | 366.852 | 0.30601 | 0.01276 | 0.9887 | -0.0719 | True |
| short_pulse_1ns_low | ngspice_two_state_directional_residual_recover_mean | CHECK | 366.855 | 0.30601 | 0.01276 | 0.9887 | -0.0719 | True |
| short_pulse_1ns_low | ngspice_two_state_directional_residual_recover_fast | CHECK | 366.836 | 0.30601 | 0.01276 | 0.9887 | -0.0719 | True |
| short_pulse_2ns_low | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.0135 | -0.0717 |  |
| short_pulse_2ns_low | hspice_transistor_sp | PAD_REFERENCE | 540.937 | n/a | n/a | n/a | n/a |  |
| short_pulse_2ns_low | ngspice_legacy | PAD_ONLY_IMPROVEMENT | 15.866 | 0.01746 | 0.30005 | 1.0101 | -0.0718 | True |
| short_pulse_2ns_low | ngspice_value_match_v2 | VALUE_MATCH_AMBIGUOUS | 15.856 | 0.01745 | 0.29960 | 1.0125 | -0.0718 | True |
| short_pulse_2ns_low | ngspice_two_state_identity | CHECK | 103.536 | 0.08330 | 0.04334 | 0.9554 | 0.0011 | True |
| short_pulse_2ns_low | ngspice_two_state_pwl | CHECK | 71.752 | 0.04899 | 0.02536 | 0.9870 | 0.0011 | True |
| short_pulse_2ns_low | ngspice_two_state_hybrid | CHECK | 65.780 | 0.04383 | 0.21175 | 1.0095 | -0.0192 | True |
| short_pulse_2ns_low | ngspice_two_state_directional | CHECK | 30.188 | 0.01644 | 0.02192 | 0.9887 | 0.0011 | True |
| short_pulse_2ns_low | ngspice_two_state_directional_residual | GOOD | 23.271 | 0.02141 | 0.01319 | 0.9887 | -0.0719 | True |
| short_pulse_2ns_low | ngspice_two_state_directional_residual_recover_mean | GOOD | 15.061 | 0.01640 | 0.01519 | 0.9887 | -0.0719 | True |
| short_pulse_2ns_low | ngspice_two_state_directional_residual_recover_fast | GOOD | 15.048 | 0.01640 | 0.01253 | 0.9887 | -0.0719 | True |

## Output Figures

- `figures/<case>/01_input_pad_overlay.png`
- `figures/<case>/02_ku_overlay.png`
- `figures/<case>/03_kd_overlay.png`
- `figures/<case>/04_gate_state_diagnostics.png`
- `figures/<case>/05_summary_bars.png`
- `figures/summary_bars.png`
- `kd_recovery_diagnostics/kd_error_window_split.csv`
- `kd_recovery_diagnostics/short_pulse_1ns_high_mean_recovery_kd_error_windows.png`
- `kd_recovery_diagnostics/effective_tau/hspice_effective_kd_recovery_tau.csv`
- `kd_recovery_diagnostics/effective_tau/hspice_effective_tau_vs_depth.png`
- `kd_recovery_diagnostics/effective_tau/hspice_kd_recovery_tau_fits.png`
- `kd_recovery_diagnostics/hold_time/hspice_kd_hold_time.csv`
- `kd_recovery_diagnostics/hold_time/hold_law_fit_summary.csv`
- `kd_recovery_diagnostics/hold_time/hspice_kd_hold_time_fit.png`
- `kd_recovery_diagnostics/hold_time/candidate_hold_time_comparison.png`
- `kd_recovery_diagnostics/gdn_hold_time/gdn_hold_samples.csv`
- `kd_recovery_diagnostics/gdn_hold_time/gdn_hold_fit_summary.csv`
- `kd_recovery_diagnostics/gdn_hold_time/gdn_keyed_hold_fit.png`
- `kd_recovery_diagnostics/gdn_hold_time/gdn_at_reverse_by_variant.png`
- `kd_recovery_diagnostics/command_age_hold/command_age_hold_training_and_heldout.csv`
- `kd_recovery_diagnostics/command_age_hold/command_age_hold_validation_summary.csv`
- `kd_recovery_diagnostics/command_age_hold/command_age_hold_heldout_validation.png`
- `reference_truth_audit/pad_rescore_vs_references.csv`
- `reference_truth_audit/pad_ranking_by_reference.csv`
- `reference_truth_audit/short_high_pad_timing.csv`
- `reference_truth_audit/double_toggle_commitment.csv`
- `reference_truth_audit/plots/*_pad_reference_overlay.png`
- `reference_truth_audit/plots/double_toggle_full_table_commitment.png`
- `reference_truth_audit/pad_recovery_timing/pad_recovery_timing.csv`
- `reference_truth_audit/pad_recovery_timing/plots/pad_recovery_timing_vs_width.png`
- `reference_truth_audit/pad_recovery_timing/plots/*_pad_recovery_timing.png`

## HSPICE Reference Cache

| Case | Reference | Source |
|---|---|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | cache |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | cache |
| short_pulse_500ps_high | hspice_native_ibis | cache |
| short_pulse_500ps_high | hspice_transistor_sp | cache |
| short_pulse_1ns_high | hspice_native_ibis | cache |
| short_pulse_1ns_high | hspice_transistor_sp | cache |
| short_pulse_2ns_high | hspice_native_ibis | cache |
| short_pulse_2ns_high | hspice_transistor_sp | cache |
| double_toggle_1ps | hspice_native_ibis | cache |
| double_toggle_1ps | hspice_transistor_sp | cache |
| short_pulse_500ps_low | hspice_native_ibis | cache |
| short_pulse_500ps_low | hspice_transistor_sp | cache |
| short_pulse_1ns_low | hspice_native_ibis | cache |
| short_pulse_1ns_low | hspice_transistor_sp | cache |
| short_pulse_2ns_low | hspice_native_ibis | cache |
| short_pulse_2ns_low | hspice_transistor_sp | cache |

## Interpretation Rule

No two-state variant is a success unless it first passes normal `Ku/Kd` reconstruction and then improves short pulses in pad, `Ku`, and `Kd` together. Pad-only improvement remains a false pass.
