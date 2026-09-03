# ex2 Slow/Fast IBIS and Gate-State Experiment

## Headline Findings

- The original `ex2/buffer.ibs` is a valid native-IBIS artifact but is not usable for reliable pybis Ku/Kd extraction: its falling solve is singular and its rising solve is strongly ill-conditioned.
- Controlled regeneration with complementary `50 ohm to 0 V` and `50 ohm to 3.3 V` fixtures removes the singularity for both 1 ns and 5 ps input-edge models.
- The corrected tables have clean settled endpoints in both profiles; unlike fast `io_buf`, ex2 does not show a boundary-sample coefficient impulse.
- The directional-residual reconstruction still misses the strict normal-table gate in both profiles. Gate-state transient results are therefore diagnostic, not production-ready.
- The dual-residual reversal hybrid timed out on the slow-profile complete-edge control after collapsing to tiny timesteps near the falling edge. Its partial raw/log artifacts are preserved as a numerical-failure result; it was not repeated across the matrix.
- The original fast-profile full gate-state model times out because roundoff near a settled state repeatedly switches between unequal directional PWL maps.
- A stable-selector diagnostic keeps the same fit and state equations but selects direction from the delayed command target. It completes all fast-profile cases without timestep collapse.
- `ex2` has a shared final-stage gate (`n4`) for both PMOS and NMOS networks, so structurally it is closer to `inv_chain` than to the independently gated tri-state `io_buf` output stage.
- Slow profile: legacy is best for the complete edge (`5.6 mV` pad RMSE), while gate-state is much better for 1 ns interrupted high/low pulses (`24.8/28.4 mV` versus legacy `670.7/426.2 mV`).
- Slow profile: that improvement does not extend to every width. At 500 ps high, gate-state still has `239.9 mV` pad RMSE and Ku/Kd RMSE `0.264/0.293`; at 50 ps high the small pad error hides a large Kd error (`0.461`).
- Fast profile: legacy remains strong for complete and 2 ns pulses (`7.0-16.2 mV` pad RMSE), but fails 50-500 ps pulses by replaying a nearly full edge.
- Fast profile: stable gate-state improves the 1 ns high pulse from `207.4 mV` to `22.3 mV` pad RMSE and Ku/Kd RMSE from `0.302/0.059` to `0.060/0.044`.
- Fast profile: the stable result is not general. At 50 ps high its `12.6 mV` pad RMSE hides `0.442` Kd RMSE; at 1 ns low Kd improves but Ku and pad do not.
- The fast native-IBIS complete edge is much closer to transistor timing than the slow native-IBIS edge (`36.1 mV` versus `777.7 mV` pad RMSE). The characterization slew is therefore materially encoded in this model's V-T timing.

## Test Bench

- Supply: `3.3 V`; temperature: `27 C`.
- Direct load: `50 ohm || 2 pF`; no channel or transmission line.
- Under this heavy load, the transistor output settles near `1.545 V`, sourcing about `30.9 mA`; this corresponds to an effective pullup resistance of about `56.8 ohm`.
- Digital stimulus edge: `1 ps` in every comparison.
- HSPICE transistor reference: `ex2/buffer.sp` plus `ex2/hspice.mod`.
- HSPICE native IBIS reference and every ngspice model use the same PWL command and load.

## Offline Gate

| Profile | Worst RMSE | Worst max error | Gate |
|---|---:|---:|---|
| slow_1ns | 0.029643 | 0.091650 | FAIL |
| fast_5ps | 0.038153 | 0.115506 | FAIL |

## Relation To io_buf And inv_chain

| Property | inv_chain | ex2 | io_buf |
|---|---|---|---|
| Final-stage control | Shared inverter gate | Shared `n4` gate | Separate pullup `n2` and pulldown `n3` gates |
| Fast fitted state tau | About `0.020-0.038 ns` | About `0.177-0.262 ns` | Fast extraction has corrupted boundary state; slow tau spans `0.237-1.284 ns` |
| Normal reconstruction | PASS for slow and fast | FAIL for slow and fast | Slow residual PASS; fast model invalid for this fit |
| Main interpretation | Fast, clean single-state behavior | Shared-gate topology but slower and more waveform-structured | Independent tri-state paths and strongly asymmetric internal timing |

`ex2` is structurally closer to `inv_chain`, but dynamically it is an intermediate case. Its hidden state is much slower than `inv_chain`, while its endpoints are cleaner and its output control is less independent than `io_buf`.

## Clean Outputs

- `<profile>/plots/01_legacy_vs_hspice_ibis/`: pad, Ku, and Kd.
- `<profile>/plots/02_gate_full_vs_hspice_ibis/`: full directional-residual model.
- `<profile>/plots/02b_gate_stable_vs_hspice_ibis/`: stable-selector directional-residual diagnostic.
- `<profile>/plots/03_dual_hybrid_vs_hspice_ibis/`: present only for completed optional hybrid runs.
- `<profile>/plots/04_all_pad_references/`: native IBIS, transistor, and completed ngspice pad traces.
- `<profile>/waveform_data/`: aligned numeric CSV behind the plots.
- `cross_profile_plots/`: direct slow-IBIS, fast-IBIS, transistor, and legacy profile comparisons.
- `numeric_failures.csv`: preserved hybrid/fast-gate timeout classifications and partial-raw sizes.
- `metrics.csv`: all profile/case/flow metrics.

## Selected Metrics

| Profile | Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |
|---|---|---|---:|---:|---:|
| slow_1ns | edge_1ps_base_50r_2pf | legacy | 5.603 | 0.01549 | 0.01302 |
| slow_1ns | edge_1ps_base_50r_2pf | gate_full | 21.161 | 0.05707 | 0.04057 |
| slow_1ns | short_pulse_50ps_high | legacy | 1042.100 | 0.68376 | 0.78121 |
| slow_1ns | short_pulse_50ps_high | gate_full | 14.876 | 0.03315 | 0.46068 |
| slow_1ns | short_pulse_500ps_high | legacy | 1080.687 | 0.66568 | 0.49470 |
| slow_1ns | short_pulse_500ps_high | gate_full | 239.853 | 0.26385 | 0.29260 |
| slow_1ns | short_pulse_1ns_high | legacy | 670.727 | 0.42526 | 0.26908 |
| slow_1ns | short_pulse_1ns_high | gate_full | 24.787 | 0.06615 | 0.06154 |
| slow_1ns | short_pulse_2ns_high | legacy | 14.751 | 0.04882 | 0.01521 |
| slow_1ns | short_pulse_2ns_high | gate_full | 23.419 | 0.06112 | 0.04216 |
| slow_1ns | short_pulse_50ps_low | legacy | 861.035 | 0.59377 | 0.45486 |
| slow_1ns | short_pulse_50ps_low | gate_full | 133.705 | 0.26201 | 0.04392 |
| slow_1ns | short_pulse_500ps_low | legacy | 692.596 | 0.47855 | 0.49685 |
| slow_1ns | short_pulse_500ps_low | gate_full | 330.841 | 0.35239 | 0.09940 |
| slow_1ns | short_pulse_1ns_low | legacy | 426.205 | 0.27584 | 0.38019 |
| slow_1ns | short_pulse_1ns_low | gate_full | 28.403 | 0.05423 | 0.04192 |
| slow_1ns | short_pulse_2ns_low | legacy | 8.258 | 0.02261 | 0.02744 |
| slow_1ns | short_pulse_2ns_low | gate_full | 20.907 | 0.05197 | 0.03530 |
| fast_5ps | edge_1ps_base_50r_2pf | legacy | 7.003 | 0.02695 | 0.01680 |
| fast_5ps | edge_1ps_base_50r_2pf | gate_stable | 30.233 | 0.06449 | 0.03431 |
| fast_5ps | short_pulse_50ps_high | legacy | 903.306 | 0.59881 | 0.71825 |
| fast_5ps | short_pulse_50ps_high | gate_stable | 12.589 | 0.02995 | 0.44229 |
| fast_5ps | short_pulse_500ps_high | legacy | 944.007 | 0.66339 | 0.48568 |
| fast_5ps | short_pulse_500ps_high | gate_stable | 175.800 | 0.23188 | 0.31420 |
| fast_5ps | short_pulse_1ns_high | legacy | 207.410 | 0.30185 | 0.05876 |
| fast_5ps | short_pulse_1ns_high | gate_stable | 22.272 | 0.06014 | 0.04439 |
| fast_5ps | short_pulse_2ns_high | legacy | 7.505 | 0.02899 | 0.01758 |
| fast_5ps | short_pulse_2ns_high | gate_stable | 30.347 | 0.06734 | 0.04101 |
| fast_5ps | short_pulse_50ps_low | legacy | 800.686 | 0.52532 | 0.45740 |
| fast_5ps | short_pulse_50ps_low | gate_stable | 220.372 | 0.39608 | 0.04809 |
| fast_5ps | short_pulse_500ps_low | legacy | 525.952 | 0.40832 | 0.46350 |
| fast_5ps | short_pulse_500ps_low | gate_stable | 302.971 | 0.31916 | 0.17580 |
| fast_5ps | short_pulse_1ns_low | legacy | 50.143 | 0.04678 | 0.20346 |
| fast_5ps | short_pulse_1ns_low | gate_stable | 58.096 | 0.11760 | 0.04308 |
| fast_5ps | short_pulse_2ns_low | legacy | 16.171 | 0.05885 | 0.03870 |
| fast_5ps | short_pulse_2ns_low | gate_stable | 27.924 | 0.06248 | 0.03365 |

## Interpretation

A low pad error alone is not a pass. The regenerated IBIS must first support a stable Ku/Kd solve, then a candidate must preserve normal Ku/Kd and improve interrupted pad, Ku, and Kd together. Neither gate-state profile passes that full claim yet.

HSPICE reference records: `36`.