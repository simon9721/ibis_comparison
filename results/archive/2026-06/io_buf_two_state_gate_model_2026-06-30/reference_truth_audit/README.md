# io_buf Reference Truth Audit

This audit checks whether conclusions change when pad-level scoring uses HSPICE transistor `io_buf.sp` instead of HSPICE native IBIS. It uses existing cached waveforms only; no new simulations are run.

## Headline Finding

- HSPICE native IBIS and HSPICE transistor disagree strongly on the long-pulse pad: `525.5 mV` RMSE.
- On `short_pulse_1ns_high`, native-vs-transistor pad disagreement is `40.1 mV`, while directional-residual vs native is `21.9 mV` and vs transistor is `37.4 mV`.
- On short-high cases, the best transistor-pad ngspice flow is often not the best native-IBIS flow, so pad-level conclusions are reference-dependent.
- Pure short-high native-IBIS Ku is partial, not full-table replay: Ku peaks are `0.0466`, `0.0746`, `0.5432` for 0.5/1/2 ns high pulses.
- The existing `double_toggle_1ps` case is not a pure 1 ps glitch because it ends with a sustained final high. Native Ku peak `1.0024` is therefore not enough to prove full-table commitment from the first glitch.
- Coefficient RMSE still has value for matching HSPICE native IBIS, but it should no longer be treated as transistor-level truth without qualification.
- Follow-up pad-recovery timing shows the transistor `io_buf.sp` pad returns much sooner than native-IBIS Kd recovery on short-high pulses: transistor pad 50% return is `0.158 / 0.176 / 0.264 ns` after the reverse edge for `0.5 / 1 / 2 ns`, while native-IBIS Kd 50% recovery is `1.851 / 2.057 / 2.329 ns`.

## Best ngspice Pad Match by Reference

| Case | Reference | Best ngspice flow | RMSE mV | Native-vs-transistor RMSE mV |
|---|---|---|---:|---:|
| edge_1ps_base_50r_2pf | native_ibis | ngspice_value_match_v2 | 5.211 | 525.498 |
| edge_1ps_base_50r_2pf | transistor_sp | ngspice_legacy | 464.959 | 525.498 |
| short_pulse_500ps_high | native_ibis | ngspice_two_state_directional_residual_recover_fast | 13.506 | 30.529 |
| short_pulse_500ps_high | transistor_sp | ngspice_value_match_v2 | 36.728 | 30.529 |
| short_pulse_1ns_high | native_ibis | ngspice_two_state_directional_residual | 21.914 | 40.136 |
| short_pulse_1ns_high | transistor_sp | ngspice_value_match_v2 | 37.049 | 40.136 |
| short_pulse_2ns_high | native_ibis | ngspice_two_state_directional_residual | 93.587 | 399.310 |
| short_pulse_2ns_high | transistor_sp | ngspice_value_match_v2 | 421.595 | 399.310 |
| double_toggle_1ps | native_ibis | ngspice_value_match_v2 | 566.841 | 233.892 |
| double_toggle_1ps | transistor_sp | ngspice_value_match_v2 | 288.091 | 233.892 |
| short_pulse_500ps_low | native_ibis | ngspice_two_state_directional_residual_recover_fast | 366.386 | 612.609 |
| short_pulse_500ps_low | transistor_sp | ngspice_value_match_v2 | 600.236 | 612.609 |
| short_pulse_1ns_low | native_ibis | ngspice_two_state_directional_residual_recover_fast | 366.836 | 546.148 |
| short_pulse_1ns_low | transistor_sp | ngspice_value_match_v2 | 486.064 | 546.148 |
| short_pulse_2ns_low | native_ibis | ngspice_two_state_directional_residual_recover_fast | 15.048 | 540.937 |
| short_pulse_2ns_low | transistor_sp | ngspice_two_state_directional_residual_recover_fast | 424.633 | 540.937 |

## Short-High Pad Timing

| Case | Flow | Pad peak V | Peak time ns | Peak from reverse ns | Ku peak | Kd min |
|---|---|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | hspice_native_ibis | 0.0478 | 7.2829 | 1.7824 | 0.0466 | -0.0225 |
| short_pulse_500ps_high | hspice_transistor_sp | 0.0426 | 5.0010 | -0.4995 |  |  |
| short_pulse_500ps_high | ngspice_two_state_directional_residual | 0.1048 | 7.9343 | 2.4338 | 0.0613 | -0.0167 |
| short_pulse_500ps_high | ngspice_two_state_directional_residual_recover_mean | 0.0923 | 7.4750 | 1.9745 | 0.0613 | 0.0143 |
| short_pulse_1ns_high | hspice_native_ibis | 0.0616 | 6.4909 | 0.4904 | 0.0746 | -0.0632 |
| short_pulse_1ns_high | hspice_transistor_sp | 0.1291 | 6.0712 | 0.0707 |  |  |
| short_pulse_1ns_high | ngspice_two_state_directional_residual | 0.0370 | 6.4499 | 0.4494 | 0.0697 | -0.0187 |
| short_pulse_1ns_high | ngspice_two_state_directional_residual_recover_mean | 0.0370 | 6.4499 | 0.4494 | 0.0697 | -0.0117 |
| short_pulse_2ns_high | hspice_native_ibis | 0.8251 | 7.4247 | 0.4242 | 0.5432 | -0.0720 |
| short_pulse_2ns_high | hspice_transistor_sp | 1.2147 | 7.0735 | 0.0730 |  |  |
| short_pulse_2ns_high | ngspice_two_state_directional_residual | 0.9760 | 7.5421 | 0.5416 | 0.7200 | -0.0701 |
| short_pulse_2ns_high | ngspice_two_state_directional_residual_recover_mean | 0.9760 | 7.5421 | 0.5416 | 0.7200 | -0.0701 |

## Double-Toggle Commitment Check

| Flow | Pad peak V | Pad peak time ns | Ku peak | Ku peak time ns | Kd min |
|---|---:|---:|---:|---:|---:|
| hspice_native_ibis | 1.5447 | 7.9503 | 1.0024 | 6.9836 | -0.0064 |
| hspice_transistor_sp | 1.5027 | 7.9950 |  |  |  |
| ngspice_legacy | 1.2020 | 8.0029 | 1.0000 | 5.0107 | -0.0016 |
| ngspice_value_match_v2 | 1.2018 | 8.0030 | 0.9973 | 10.7813 | -0.0015 |
| ngspice_two_state_directional_residual | 1.1986 | 8.0028 | 0.9945 | 12.5000 | -0.0001 |
| ngspice_two_state_directional_residual_recover_mean | 1.1986 | 8.0028 | 0.9945 | 12.5000 | -0.0001 |
| ngspice_two_state_directional_residual_recover_fast | 1.1986 | 8.0028 | 0.9945 | 12.5000 | -0.0001 |

## Interpretation

- The previous no-false-pass discipline was still correct, but the reference hierarchy needs to be explicit: native IBIS is the coefficient reference, while transistor `io_buf.sp` is the pad-level physics reference.
- The short-high pad errors are already comparable to, or smaller than, native-vs-transistor disagreement in some cases. Past that point, coefficient matching may be matching HSPICE IBIS playback internals rather than silicon behavior.
- The double-toggle result does not prove full-table commitment by itself because the final input state is sustained high. A separate pure-glitch test would be needed to test scheduler commitment directly.
- The short-high native-IBIS coefficient peaks are partial, so HSPICE native IBIS is not simply replaying a full Ku table for every short pulse. The pad-recovery timing check now makes the remaining concern sharper: the native-IBIS Kd recovery/hold is not visible in the transistor pad response under the present setup, so treat that Kd hold as native-IBIS playback behavior until the large native-vs-transistor setup gap is explained.

Files:

- `pad_rescore_vs_references.csv`
- `pad_ranking_by_reference.csv`
- `short_high_pad_timing.csv`
- `double_toggle_commitment.csv`
- `plots/*_pad_reference_overlay.png`
- `plots/double_toggle_full_table_commitment.png`
- `pad_recovery_timing/pad_recovery_timing.csv`
- `pad_recovery_timing/plots/pad_recovery_timing_vs_width.png`
- `pad_recovery_timing/plots/*_pad_recovery_timing.png`
