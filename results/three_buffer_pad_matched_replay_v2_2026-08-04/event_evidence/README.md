# Pad-Matched Replay Event Evidence

This report rescored cached waveforms only. No HSPICE or ngspice simulation was run by this analysis step.

## Finding

- Sampling pad voltage at reversal is not a sufficient internal-state coordinate across these three buffers.
- The corrected crossing-based inverse exposes repeated pad values at widely separated trajectory times; adding absolute pad slew does not consistently make that mapping unique.
- The pad-matched variants improve pad, Ku, and Kd numerically in `12` short-pulse rows (`3` short-high, `9` short-low).
- `6` rows improve all three by at least 5% (`0` short-high, `6` short-low). Thus no short-high result is a material all-three improvement.
- Several pad waveforms improve while one coefficient does not. Those are pad-only false passes, not model success.
- The short-low result is real directional progress, especially for ex2 at 250 ps and 500 ps. It does not establish a general retrigger model because short-high remains open.
- Long-control audit for `v2`: `0` numeric failures; median/worst of the per-row worst pad/Ku/Kd error ratio is `1.019` / `1.143`.

## Counts

- Short-pulse pad-flow rows: `96`
- Triggered rows: `91`
- Mapping-ambiguous rows: `34`
- `COEFFICIENT_AND_PAD_IMPROVED`: `12`
- `COEFFICIENT_ARTIFACT`: `24`
- `NO_CLEAR_IMPROVEMENT`: `22`
- `PAD_MAPPING_AMBIGUOUS`: `34`
- `PAD_ONLY_FALSE_PASS`: `4`

## Figures

- `event_evidence/plots/01_error_ratio_heatmaps.png`
- `event_evidence/plots/02_outcome_matrix.png`
- `event_evidence/plots/03_reversal_jump_excess.png`

## Data

- `case_outcomes.csv`: per-case error ratios, trigger/ambiguity state, envelope result, and reversal-jump excess.
- `candidate_metrics_rescored.csv`: corrected event-local metrics for every nominal campaign flow.

## Interpretation

A Ku/Kd value outside [0,1] is not automatically wrong. The rejection rule used here is whether the candidate exceeds the native-IBIS envelope or adds a reversal discontinuity beyond both native IBIS and legacy pybis. This avoids clipping legitimate extracted-coefficient overshoot while still detecting algorithm-created spikes.
