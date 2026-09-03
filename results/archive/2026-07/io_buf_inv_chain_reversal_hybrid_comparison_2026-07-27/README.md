# Legacy-Normal / Gate-State-on-Reversal Comparison

This study evaluates a new opt-in pybis mode that uses original elapsed-time `Ku(t)/Kd(t)` replay during normal complete transitions, while continuously tracking hidden `GUP/GDN` states. An unsettled reverse edge selects directional-residual `Ku(GUP)/Kd(GDN)` until the commanded state settles, then returns to legacy replay.

## Headline

- Matrix: `28` device/IBIS/case combinations across `io_buf` and `inv_chain`, slow and fast IBIS.
- Normal controls preserved: `0/4`.
- Short/control cases that activated the gate-state path: `19/24`.
- Activated cases improving pad, Ku, and Kd with continuous takeover/handoff: `13/19`.
- Activated cases improving all three RMS errors but failing continuity: `2/19`.
- Numeric failures: `5/28`.
- HSPICE was not rerun. Native-IBIS and transistor references are copied/read from the prior clean comparison packages; only the new ngspice hybrid was simulated.
- Legacy `InputDriven` was regenerated and checked against the pre-experiment models. The netlist bodies are identical; only the IBIS filename provenance header differs.

## Main Finding

- The experiment is **not production-ready**: none of the four complete rise/fall controls passed because the always-tracked gate-state circuitry drove ngspice into extremely small timesteps near the normal falling transition.
- The corrected detector handles both directions. It activates for inv_chain 50/100/200 ps short-high and short-low pulses, while the 1 ns settled controls remain on legacy replay.
- All 12 activated inv_chain cases improve pad, Ku, and Kd together and keep measured takeover/handoff steps below 0.02. Their RMS-error reductions are typically about 81%-98% for pad and 65%-97% for coefficients.
- Slow io_buf remains asymmetric: short-high Ku improves while Kd recovery is still weak; short-low Kd is good while Ku/output recovery can remain weak.
- Fast io_buf is the clearest rejection case: normal and 2 ns-high runs fail numerically, while completed interrupted cases retain large coefficient errors and takeover steps.

## Algorithm

1. Legacy `Ku(t)/Kd(t)` remains the normal selected path.
2. `GUP/GDN`, direction-specific coefficient maps, and the Kd residual run continuously in the background.
3. A falling-after-rising or rising-after-falling command inside the globally derived transition window asserts `HHYBRIDACTIVE`.
4. Final coefficients track the gate-state path through the interruption and recovery.
5. A model-derived `delay + 5*tau` recovery interval keeps the gate path active, then selection returns to legacy replay.

## Bench

- `io_buf`: 3.3 V, direct `50 ohm || 2 pF` load, 1 ps input edges, 27 C.
- `inv_chain`: 1.8 V, direct `50 ohm || 2 pF` load, 1 ps input edges, 27 C.
- No channel or transmission line.
- Slow IBIS uses s2ibispy `tr=tf=1 ns`; fast IBIS uses `tr=tf=5 ps`.

## Figure Sets

Each `device/variant/plots` folder contains:

- `01_hspice_ibis_vs_transistor`: pad-only reference comparison.
- `02_hspice_ibis_vs_legacy`: pad/Ku/Kd baseline.
- `03_hspice_ibis_vs_reversal_hybrid`: pad/Ku/Kd new result.
- `04_hspice_ibis_hybrid_transistor`: three-way pad comparison.
- `05_native_legacy_hybrid`: direct baseline-to-new comparison.
- `06_hybrid_diagnostics`: input, activation, GUP/GDN, and selected coefficient paths.

## Result Table

| Device | IBIS | Case | Status | Active ns | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|---:|
| io_buf | slow | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| io_buf | slow | short_pulse_1ns_high | SHORT_IMPROVED_DISCONTINUOUS | 6.000 | 12.606 | 0.01284 | 0.29056 |
| io_buf | slow | short_pulse_2ns_high | SHORT_CHECK | 6.000 | 73.839 | 0.05508 | 0.15167 |
| io_buf | slow | short_pulse_1ns_low | SHORT_IMPROVED_DISCONTINUOUS | 6.999 | 392.180 | 0.27744 | 0.00884 |
| io_buf | slow | short_pulse_2ns_low | SHORT_IMPROVED_CONTINUOUS | 5.999 | 11.244 | 0.01235 | 0.00748 |
| io_buf | fast | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| io_buf | fast | short_pulse_1ns_high | SHORT_CHECK | 5.010 | 425.333 | 0.35595 | 0.17405 |
| io_buf | fast | short_pulse_2ns_high | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| io_buf | fast | short_pulse_1ns_low | SHORT_CHECK | 5.010 | 802.204 | 0.52696 | 0.33273 |
| io_buf | fast | short_pulse_2ns_low | SHORT_CHECK | 5.010 | 625.607 | 0.42320 | 0.31045 |
| inv_chain | slow | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| inv_chain | slow | short_pulse_50ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 11.136 | 0.01792 | 0.02714 |
| inv_chain | slow | short_pulse_100ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 14.302 | 0.01374 | 0.01591 |
| inv_chain | slow | short_pulse_200ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 14.589 | 0.01409 | 0.01569 |
| inv_chain | slow | short_pulse_1ns_high | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 10.517 | 0.01457 | 0.01363 |
| inv_chain | slow | short_pulse_50ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 44.970 | 0.06299 | 0.01090 |
| inv_chain | slow | short_pulse_100ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 20.950 | 0.02534 | 0.01398 |
| inv_chain | slow | short_pulse_200ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 15.307 | 0.01548 | 0.01566 |
| inv_chain | slow | short_pulse_1ns_low | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 11.170 | 0.01502 | 0.01408 |
| inv_chain | fast | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| inv_chain | fast | short_pulse_50ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 10.458 | 0.01847 | 0.02749 |
| inv_chain | fast | short_pulse_100ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 17.249 | 0.01423 | 0.01719 |
| inv_chain | fast | short_pulse_200ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 13.298 | 0.01426 | 0.01360 |
| inv_chain | fast | short_pulse_1ns_high | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 10.823 | 0.01490 | 0.01377 |
| inv_chain | fast | short_pulse_50ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 61.297 | 0.07814 | 0.01683 |
| inv_chain | fast | short_pulse_100ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 10.147 | 0.01411 | 0.00960 |
| inv_chain | fast | short_pulse_200ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 12.110 | 0.01510 | 0.01281 |
| inv_chain | fast | short_pulse_1ns_low | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 11.301 | 0.01517 | 0.01432 |

## Interpretation

`NORMAL_PRESERVED` requires no hybrid activation and no more than 5 mV pad / 0.02 coefficient RMS change from cached legacy pybis. `SHORT_IMPROVED_CONTINUOUS` requires the activated hybrid to improve pad, Ku, and Kd versus legacy and keep both takeover and handoff coefficient steps at or below 0.02. `SHORT_IMPROVED_DISCONTINUOUS` records useful shape improvement that still fails the continuity requirement. Pad-only improvement is never counted.

See `comparison_summary.csv` for side-by-side legacy/hybrid reductions, `metrics.csv` for all errors and takeover/handoff diagnostics, `waveform_data` for the plotted numeric data, `numeric_failure_diagnostics.csv` for timeout locations, `legacy_unchanged_verification.csv` for the opt-in legacy-body check, and `source_provenance.csv` for exact cached/fresh artifact hashes. Large partial raw files from timed-out runs are intentionally removed after their last-time/size diagnostics are recorded.
