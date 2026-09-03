# inv_chain and ex2 Value-Matched Replay

This extends the corrected V2 coefficient-value-matched replay experiment beyond `io_buf`. HSPICE reference waveforms were reused from existing CSVs; no HSPICE simulations were run.

## Scope

- Devices: `inv_chain`, `ex2`.
- IBIS profiles: slow 1 ns and fast 5 ps characterization models.
- Runtime input edges: 1 ps, matching the original io_buf value-match experiment.
- `inv_chain` cases: long control plus 50/100/200 ps short-high and short-low pulses.
- `ex2` cases: long control plus 500 ps/1 ns/2 ns short-high and short-low pulses.
- Policies: balanced, Ku-only, Kd-only, and separate Ku/Kd starts.

## Headline Counts

- Completed value-match rows: `112`.
- Replay-active rows: `48`.
- Rows classified table-retiming ambiguous: `20`.
- Numeric failures: `0`.

## Findings

- `inv_chain`: balanced replay activated in 6 short-high runs; all pad/Ku/Kd RMSE values improved together in `5` of them. The fast 200 ps case regressed because its sampled state mapped near inconsistent table endpoints.
- `ex2`: balanced replay activated in 6 short-high runs; all three metrics improved together in `0`. The 500 ps cases can improve pad and Ku while worsening Kd, which is a coefficient-level false pass.
- Split Ku/Kd starts did not materially rescue the failing ex2 cases. Therefore the failure is not only the shared average; current Ku/Kd values do not encode pending transport delay or complete hidden state.
- Most short-low cases did not activate replay because the existing rise-after-fall detector is state-gated while fall-after-rise is command-age-gated. This is an implementation asymmetry, not evidence that value matching solved short-low behavior.
- The method is numerically stable in this campaign but is not a general retrigger solution. It is useful as a baseline that demonstrates why coefficient-value retiming is underdetermined.

## Important Interpretation

The implementation matches current `Ku/Kd` values, not pad voltage. The two independently inferred opposite-table times often disagree; that disagreement is the central test of whether a single replay coordinate exists.

## Files

- `IMPLEMENTATION_WALKTHROUGH.md`: exact offline/runtime implementation.
- `metrics.csv`: coefficient, pad, inferred-start, ambiguity, and activation metrics.
- `balanced_vs_legacy_summary.csv`: one concise row per short-pulse case with sampled values, inferred starts, and metric deltas.
- `reference_manifest.csv`: cached HSPICE waveform provenance.
- `generated_models/`: exact generated subcircuits.
- `runs/`: exact ngspice decks, models, raw files, and logs.
- `waveform_data/`: aligned numeric data behind the plots.
- `plots/`: waveform overlays and split-start diagnostics.

## Figures

- `plots/value_match_cross_buffer_evidence.png` (compact representative comparison)
- `plots/inv_chain/slow_1ns/edge_1ps_base_50r_2pf.png`
- `plots/inv_chain/slow_1ns/edge_1ps_base_50r_2pf_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_50ps_high.png`
- `plots/inv_chain/slow_1ns/short_pulse_50ps_high_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_100ps_high.png`
- `plots/inv_chain/slow_1ns/short_pulse_100ps_high_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_200ps_high.png`
- `plots/inv_chain/slow_1ns/short_pulse_200ps_high_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_50ps_low.png`
- `plots/inv_chain/slow_1ns/short_pulse_50ps_low_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_100ps_low.png`
- `plots/inv_chain/slow_1ns/short_pulse_100ps_low_diagnostics.png`
- `plots/inv_chain/slow_1ns/short_pulse_200ps_low.png`
- `plots/inv_chain/slow_1ns/short_pulse_200ps_low_diagnostics.png`
- `plots/inv_chain/fast_5ps/edge_1ps_base_50r_2pf.png`
- `plots/inv_chain/fast_5ps/edge_1ps_base_50r_2pf_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_50ps_high.png`
- `plots/inv_chain/fast_5ps/short_pulse_50ps_high_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_100ps_high.png`
- `plots/inv_chain/fast_5ps/short_pulse_100ps_high_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_200ps_high.png`
- `plots/inv_chain/fast_5ps/short_pulse_200ps_high_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_50ps_low.png`
- `plots/inv_chain/fast_5ps/short_pulse_50ps_low_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_100ps_low.png`
- `plots/inv_chain/fast_5ps/short_pulse_100ps_low_diagnostics.png`
- `plots/inv_chain/fast_5ps/short_pulse_200ps_low.png`
- `plots/inv_chain/fast_5ps/short_pulse_200ps_low_diagnostics.png`
- `plots/ex2/slow_1ns/edge_1ps_base_50r_2pf.png`
- `plots/ex2/slow_1ns/edge_1ps_base_50r_2pf_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_500ps_high.png`
- `plots/ex2/slow_1ns/short_pulse_500ps_high_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_1ns_high.png`
- `plots/ex2/slow_1ns/short_pulse_1ns_high_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_2ns_high.png`
- `plots/ex2/slow_1ns/short_pulse_2ns_high_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_500ps_low.png`
- `plots/ex2/slow_1ns/short_pulse_500ps_low_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_1ns_low.png`
- `plots/ex2/slow_1ns/short_pulse_1ns_low_diagnostics.png`
- `plots/ex2/slow_1ns/short_pulse_2ns_low.png`
- `plots/ex2/slow_1ns/short_pulse_2ns_low_diagnostics.png`
- `plots/ex2/fast_5ps/edge_1ps_base_50r_2pf.png`
- `plots/ex2/fast_5ps/edge_1ps_base_50r_2pf_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_500ps_high.png`
- `plots/ex2/fast_5ps/short_pulse_500ps_high_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_1ns_high.png`
- `plots/ex2/fast_5ps/short_pulse_1ns_high_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_2ns_high.png`
- `plots/ex2/fast_5ps/short_pulse_2ns_high_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_500ps_low.png`
- `plots/ex2/fast_5ps/short_pulse_500ps_low_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_1ns_low.png`
- `plots/ex2/fast_5ps/short_pulse_1ns_low_diagnostics.png`
- `plots/ex2/fast_5ps/short_pulse_2ns_low.png`
- `plots/ex2/fast_5ps/short_pulse_2ns_low_diagnostics.png`
