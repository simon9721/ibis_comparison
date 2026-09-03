# inv_chain Slow/Fast IBIS Comparison Ladder

This package repeats the same controlled comparison phases for the two s2ibispy-generated `inv_chain` models.

## Controlled Bench

- Supply: `1.8 V`
- Load in HSPICE and ngspice: `50 ohm || 2 pF`
- Applied input stimulus edge: `1 ps`
- Temperature: `27 C`
- Direct buffer-to-load connection; no channel.
- HSPICE transistor references are restored from the unchanged reference cache.

## Models

- `slow_1ns`: `tr=tf=1 ns`, `results\inv_chain_s2ibispy_slow_fast_2026-07-27\slow_1ns\inv_chain_slow_1ns.ibs`.
- `fast_5ps`: `tr=tf=5 ps`, `results\inv_chain_s2ibispy_slow_fast_2026-07-27\fast_5ps\inv_chain_fast_5ps.ibs`.

## Headline Normal-Edge Numbers

| Model | Reconstruction gate | HSPICE IBIS vs transistor | legacy pybis vs HSPICE IBIS | gate-state vs HSPICE IBIS |
|---|---:|---:|---:|---:|
| slow IBIS (1 ns source edges) | PASS | 383.230 mV | 11.364 mV | 18.082 mV |
| fast IBIS (5 ps source edges) | PASS | 13.822 mV | 11.408 mV | 17.383 mV |

## Findings

- Both files pass the offline directional-residual reconstruction gate. The slow model's worst table RMSE/max error is `0.01945/0.06636`; the fast model's is `0.01990/0.06946`.
- The edge setting changes fitted onset delay, not the underlying fitted time constants. Pullup-on delay changes from `0.865 ns` to `0.268 ns`, while pullup-off tau remains `0.026 ns` in both models.
- Complete and settled pulses still favor legacy pybis. On the normal edge it is about `11.4 mV` from native HSPICE IBIS, versus `17-18 mV` for gate state.
- Interrupted 50/100/200 ps pulses reverse that result. For the slow IBIS, legacy pad RMSE spans `365.5-564.8 mV`, while gate state spans `17.4-39.6 mV`.
- For the fast IBIS, legacy pad RMSE spans `121.1-294.3 mV`, while gate state spans `16.6-45.1 mV`.
- The slow IBIS is not a good transistor-timing model under this 1 ps bench: normal pad RMSE is `383.2 mV`, mainly from its delayed transition. The fast IBIS reduces that to `13.8 mV`.
- Fast source waveforms do not reproduce the transistor chain's minimum-pulse filtering. For a 50 ps high input the transistor pad stays essentially at `0 V`, while native HSPICE reaches about `0.448 V` with the fast IBIS (`0.466 V` with the slow IBIS).
- Therefore the conclusions are separate: gate state strongly improves native-IBIS interrupted-coefficient playback; the fast IBIS is the closer transistor approximation, but is still not transistor-accurate for the shortest pulses.

## Figure Guide

- `slow_1ns/plots/` and `fast_5ps/plots/`: identical phase-by-phase comparison folders.
- `plots/05_hspice_native_slow_vs_fast/`: direct HSPICE native-IBIS pad/Ku/Kd comparison.
- `plots/06_pad_rmse_summary.png`: the same error measure across every case and phase.
- `metrics.csv`: all pad/Ku/Kd metrics with a `variant_id` column.
- `waveform_data/` inside each variant: aligned numeric source data.

## Interpretation Rule

The transistor comparison is pad-only. `Ku/Kd` comparisons are native-HSPICE-IBIS playback checks. A gate-state result is not validated unless its offline reconstruction gate passes and its transient pad and coefficient behavior both remain accurate.
