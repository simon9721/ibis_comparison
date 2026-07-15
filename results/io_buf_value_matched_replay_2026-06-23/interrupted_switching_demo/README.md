# io_buf Value-Matched Replay Baseline

This study tests whether interrupted transitions can be improved by sampling current `Ku/Kd`, mapping those values onto the opposite IBIS coefficient table, and replaying from the inferred table time.

## Headline

- Long-pulse control pad RMSE delta versus legacy: `n/a mV`.
- Long-pulse control max Ku/Kd RMSE delta versus legacy: `n/a`.
- ValueMatchedHybrid coefficient-first improvements versus legacy: `2` / `6` interrupted cases.
- ValueMatchedHybrid table-retiming ambiguity observed in `2` / `6` interrupted cases.
- ValueMatchedHybrid status across required cases: `CHECK=3, failed=5`.
- ValueMatchedFull diagnostic status across required cases: `CHECK=1, failed=7`.
- Long-pulse control ValueMatchedHybrid status: `failed` (ngspice vm_hybrid return code -999).
- `ValueMatchedReplayFull`, `KuOnly`, and `KdOnly` are diagnostic-only variants.
- HSPICE is validation only; inverse maps and weights come only from IBIS/pybis coefficient tables.

## Current Interpretation

- The baseline is implemented and produces the right diagnostic visibility, but value-matched table retiming is not sufficient as a replacement candidate.
- The most important short-high demo still replays almost full `Ku`, so it fails for the same physical reason as legacy pybis.
- Several low-pulse and long-control value-matched variants hit ngspice timeout/stiffness, so the method is not robust enough without additional hidden-state constraints.
- Charge-limited gate-state remains the better current direction for short-high behavior because it limits the available pullup charge instead of just retiming table playback.

## short_pulse_1ns_high Specific Numbers

- HSPICE Ku peak: `0.0746`
- legacy Ku peak: `1.0125`
- ChargeLimitedHybrid Ku peak: `0.0586`
- ValueMatchedHybrid Ku peak: `1.0122`
- HSPICE Kd min: `-0.0632`
- legacy Kd min: `-0.0718`
- ValueMatchedHybrid Kd min: `-0.0718`
- HSPICE pad peak: `0.0616 V`
- legacy pad peak: `1.5155 V`
- ChargeLimitedHybrid pad peak: `0.0893 V`
- ValueMatchedHybrid pad peak: `1.5151 V`

## How To Read The Figures

- `*_01_input_pad_overlay.png`: input command and pad waveform.
- `*_02_ku_only.png` / `*_02_kd_only.png`: coefficient overlays.
- `*_03_vm_*_value_match_diagnostics.png`: sampled values, inferred table times, match errors, and ambiguity.
- `high_vs_low_pulse_comparison.png`: mirrored 1 ns short-high and short-low comparison.
- `short_pulse_summary_bars.png`: RMSE, peak, and ambiguity summary.

## Output Files

- `candidate_metrics.csv`: detailed per-case/per-variant metrics.
- `metrics_by_case.csv`: compact case comparison.
- `interrupted_switching_demo/demo_metrics.csv`: short-pulse-focused metrics.
