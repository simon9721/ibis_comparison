# Legacy-Normal / Gate-State-on-Reversal Comparison

This study evaluates a new opt-in pybis mode that uses original elapsed-time `Ku(t)/Kd(t)` replay during normal complete transitions, while continuously tracking hidden `GUP/GDN` states. An unsettled reverse edge selects directional-residual `Ku(GUP)/Kd(GDN)` until the commanded state settles, then returns to legacy replay.

## Headline

- Matrix: `28` device/IBIS/case combinations across `io_buf` and `inv_chain`, slow and fast IBIS.
- Normal controls preserved: `0/4`.
- Short/control cases that activated the gate-state path: `19/24`.
- Activated cases improving pad, Ku, and Kd with continuous takeover/handoff: `12/19`.
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
2. `GUP/GDN`, direction-specific coefficient maps, and independent Ku/Kd residuals run continuously in the background.
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
| io_buf | slow | short_pulse_1ns_high | SHORT_IMPROVED_DISCONTINUOUS | 6.000 | 15.512 | 0.01479 | 0.29056 |
| io_buf | slow | short_pulse_2ns_high | SHORT_CHECK | 6.000 | 73.029 | 0.05435 | 0.15167 |
| io_buf | slow | short_pulse_1ns_low | SHORT_IMPROVED_DISCONTINUOUS | 6.999 | 390.889 | 0.27729 | 0.00884 |
| io_buf | slow | short_pulse_2ns_low | SHORT_CHECK | 5.999 | 13.295 | 0.01541 | 0.00748 |
| io_buf | fast | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| io_buf | fast | short_pulse_1ns_high | NONPHYSICAL_COEFFICIENT_RANGE | 5.010 | 540.949 | 0.14276 | 0.32682 |
| io_buf | fast | short_pulse_2ns_high | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| io_buf | fast | short_pulse_1ns_low | NONPHYSICAL_COEFFICIENT_RANGE | 5.010 | 829.417 | 0.60350 | 0.34029 |
| io_buf | fast | short_pulse_2ns_low | NONPHYSICAL_COEFFICIENT_RANGE | 5.010 | 340.538 | 0.21433 | 0.31045 |
| inv_chain | slow | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| inv_chain | slow | short_pulse_50ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 11.043 | 0.01762 | 0.02714 |
| inv_chain | slow | short_pulse_100ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 14.031 | 0.01354 | 0.01591 |
| inv_chain | slow | short_pulse_200ps_high | SHORT_IMPROVED_CONTINUOUS | 1.070 | 14.496 | 0.01402 | 0.01569 |
| inv_chain | slow | short_pulse_1ns_high | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 10.517 | 0.01457 | 0.01363 |
| inv_chain | slow | short_pulse_50ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 46.992 | 0.06490 | 0.01090 |
| inv_chain | slow | short_pulse_100ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 21.932 | 0.02529 | 0.01398 |
| inv_chain | slow | short_pulse_200ps_low | SHORT_IMPROVED_CONTINUOUS | 1.070 | 15.785 | 0.01546 | 0.01515 |
| inv_chain | slow | short_pulse_1ns_low | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 11.170 | 0.01502 | 0.01408 |
| inv_chain | fast | edge_1ps_base_50r_2pf | NUMERIC_FAIL | n/a | n/a | n/a | n/a |
| inv_chain | fast | short_pulse_50ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 10.421 | 0.01813 | 0.02749 |
| inv_chain | fast | short_pulse_100ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 16.956 | 0.01410 | 0.01719 |
| inv_chain | fast | short_pulse_200ps_high | SHORT_IMPROVED_CONTINUOUS | 0.470 | 13.257 | 0.01429 | 0.01360 |
| inv_chain | fast | short_pulse_1ns_high | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 10.823 | 0.01490 | 0.01377 |
| inv_chain | fast | short_pulse_50ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 63.474 | 0.08096 | 0.01683 |
| inv_chain | fast | short_pulse_100ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 10.666 | 0.01357 | 0.00960 |
| inv_chain | fast | short_pulse_200ps_low | SHORT_IMPROVED_CONTINUOUS | 0.470 | 11.968 | 0.01406 | 0.01259 |
| inv_chain | fast | short_pulse_1ns_low | LEGACY_PATH_NO_INTERRUPTION | 0.000 | 11.301 | 0.01517 | 0.01432 |

## Interpretation

`NORMAL_PRESERVED` requires no hybrid activation and no more than 5 mV pad / 0.02 coefficient RMS change from cached legacy pybis. `SHORT_IMPROVED_CONTINUOUS` requires the activated hybrid to improve pad, Ku, and Kd versus legacy and keep both takeover and handoff coefficient steps at or below 0.02. `SHORT_IMPROVED_DISCONTINUOUS` records useful shape improvement that still fails the continuity requirement. Pad-only improvement is never counted.

See `comparison_summary.csv` for side-by-side legacy/hybrid reductions, `metrics.csv` for all errors and takeover/handoff diagnostics, `waveform_data` for the plotted numeric data, `numeric_failure_diagnostics.csv` for timeout locations, `legacy_unchanged_verification.csv` for the opt-in legacy-body check, and `source_provenance.csv` for exact cached/fresh artifact hashes. Large partial raw files from timed-out runs are intentionally removed after their last-time/size diagnostics are recorded.

## Dual-Residual Extension

- The previous hybrid corrected only `Kd`; this candidate independently adds `Ku` rise/fall table residuals and a `dGUP/dt` residual while retaining the established `Kd` residual.
- Comparable completed A/B cases: `23`.
- Using a 1% material-change threshold, Ku improves in `8/23` cases and worsens in `5/23`.
- Pad improves in `5/23` cases and worsens in `9/23`.
- Only `1/23` cases improve pad, Ku, and Kd together by more than 1%; `0` improve all three by more than 5%.
- The dual residual is **not preferred over the Kd-only hybrid**. It regresses the previously continuous slow-`io_buf` 2 ns-low result, and three fast-`io_buf` cases violate the allowed coefficient range.
- `inv_chain` remains strong, but the new Ku term mostly makes small changes: all 12 activated cases retain their continuous-improvement status, with individual A/B changes generally only a few percent.
- Slow `io_buf` 2 ns-low regresses from pad/Ku RMSE `11.244 mV / 0.01235` to `13.295 mV / 0.01541`. Fast `io_buf` 1 ns-high improves Ku RMSE from `0.35595` to `0.14276`, but worsens pad/Kd to `540.949 mV / 0.32682` and violates coefficient bounds.
- Offline complete-edge reconstruction passes for `4/4` device/IBIS variants. Fast `io_buf` improves offline worst RMSE from `0.4642751664544503` to `0.0015870891684544078`.
- That offline pass does not transfer to interrupted runtime: fast `io_buf` reaches Ku/Kd residual magnitudes `0.6994417470846954` / `0.8709495402651186`. The complete-edge residual is still elapsed-time-indexed and is not a valid general correction at an arbitrary hidden state.
- Dual-candidate status counts: `{'NUMERIC_FAIL': 5, 'SHORT_IMPROVED_CONTINUOUS': 12, 'LEGACY_PATH_NO_INTERRUPTION': 4, 'NONPHYSICAL_COEFFICIENT_RANGE': 3, 'SHORT_IMPROVED_DISCONTINUOUS': 2, 'SHORT_CHECK': 2}`.
- HSPICE references were reused from cache; this extension ran only the new ngspice candidate.

Additional evidence:

- `dual_vs_kd_only_summary.csv`: direct numeric A/B comparison.
- `residual_fit_summary.csv`: independently fitted Ku/Kd rate gains and observed residual magnitudes.
- `plots/07_kd_only_vs_dual_residual`: native IBIS, transistor pad, Kd-only hybrid, and dual-residual hybrid.
- `plots/08_dual_residual_diagnostics`: `GUP/GDN` plus separate Ku/Kd residual contributions.
