# io_buf State-Continuous pybis Retrigger Study

This study compares HSPICE native IBIS against two ngspice pybis models:

- Legacy `InputDriven`: edge restarts evaluate Ku/Kd from elapsed time since the latest input edge.
- Experimental `InputDrivenStateContinuous`: input edges reverse a continuous `PSTATE` and smooth Ku/Kd toward `KUTARGET/KDTARGET`.

## Headline

- Completed cases: `13` / `13`.
- The implemented `InputDrivenStateContinuous` algorithm is **not valid**.
- It reduces pad RMSE in some very short pulses by suppressing drive, not by matching HSPICE `Ku/Kd` switching coefficients.
- Sharp complete-edge regressions: `1`, especially `double_toggle_1ps`.
- Earlier short-pulse `PASS` labels were pad-only false passes and should not be used as acceptance evidence.

## Outputs

- `metrics_by_case.csv`
- `legacy_vs_state_continuous_summary.csv`
- `plots/summary_pad_rmse_legacy_vs_state.png`
- `plots/cases/*_legacy_vs_state_continuous.png`
- `common/legacy/driver_OutputInput_Typical.sub`
- `common/state_continuous/driver_OutputInput_Typical.sub`

## Case Summary

| Case | Kind | Legacy | State | Legacy pad RMSE mV | State pad RMSE mV | Pad reduction % | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| edge_1ps_base_50r_2pf | sharp_complete | GOOD | GOOD | 5.289 | 2.405 | 54.5 | PASS |
| edge_5ps_50r_2pf | slow_edge | WARN | GOOD | 7.934 | 2.104 | 73.5 | INFO |
| edge_50ps_50r_2pf | slow_edge | WARN | WARN | 11.375 | 11.466 | -0.8 | INFO |
| edge_500ps_50r_2pf | slow_edge | CHECK | CHECK | 134.834 | 135.898 | -0.8 | INFO |
| edge_2ns_50r_2pf | slow_edge | CHECK | CHECK | 393.169 | 393.643 | -0.1 | INFO |
| load_25r_2pf | sharp_complete | GOOD | GOOD | 3.223 | 1.441 | 55.3 | PASS |
| load_50r_0pf | sharp_complete | GOOD | GOOD | 5.770 | 3.329 | 42.3 | PASS |
| load_50r_10pf | sharp_complete | GOOD | GOOD | 4.543 | 3.669 | 19.2 | PASS |
| load_100r_2pf | sharp_complete | GOOD | GOOD | 8.922 | 3.612 | 59.5 | PASS |
| double_toggle_1ps | sharp_complete | GOOD | CHECK | 5.713 | 475.746 | -8227.3 | REGRESSION |
| short_pulse_2ns_high | short_pulse | CHECK | CHECK | 361.362 | 270.960 | 25.0 | NOT_ENOUGH_IMPROVEMENT |
| short_pulse_1ns_high | short_pulse | CHECK | CHECK | 653.256 | 26.652 | 95.9 | FALSE_PASS_PAD_ONLY |
| short_pulse_500ps_high | short_pulse | CHECK | CHECK | 678.863 | 19.707 | 97.1 | FALSE_PASS_PAD_ONLY |

## Interpretation Guide

`PASS` for sharp complete cases only means the experimental state model did not materially regress those normal edges.

The short-pulse pad improvements are not valid passes. The coefficient plots show the algorithm can keep `Kd` near 1 and `Ku` near 0 while HSPICE turns `Kd` off and produces a small partial pulse. Coefficient agreement must be a hard gate for retrigger work.

This implementation should not replace the default `InputDriven` mode. It is useful only as a negative result showing that a single normalized `PSTATE` is the wrong abstraction.
