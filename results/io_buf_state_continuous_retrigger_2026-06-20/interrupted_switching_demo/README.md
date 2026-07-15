# State-Continuous Interrupted Switching Demo - Negative Result

This folder mirrors the older `io_buf_switching_coeff_sweep_2026-06-19/interrupted_switching_demo`, but adds the experimental state-continuous pybis curve.

**Conclusion: the implemented state-continuous algorithm is not correct.** It can reduce pad-voltage RMSE in very short pulses, but it does that by suppressing the driver state rather than matching HSPICE `Ku/Kd` behavior.

The clearest case is `short_pulse_1ns_high`: the falling command arrives before the pad has settled from the rising command.

## Figures

- `figures/01_short_pulse_1ns_event_timeline.png`: input command, pad waveform, Ku/Kd, and state diagnostics.
- `figures/02_short_pulse_1ns_ku_kd_state_difference.png`: coefficient-state comparison.
- `figures/03_short_pulse_1ns_pad_consequence.png`: waveform consequence of the coefficient behavior.
- `figures/04_short_pulse_2ns_partial_improvement_limit.png`: the 2 ns case where improvement is only partial.
- `figures/05_short_pulse_rmse_summary.png`: compact RMSE summary.

## Key Numbers

| Case | Legacy pad RMSE mV | State pad RMSE mV | Legacy Ku RMSE | State Ku RMSE | Legacy Kd RMSE | State Kd RMSE | HSPICE Ku peak | State Ku peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| short_pulse_1ns_high | 653.3 | 26.7 | 0.470 | 0.028 | 0.504 | 0.635 | 0.075 | 0.004 |
| short_pulse_2ns_high | 362.1 | 271.5 | 0.284 | 0.174 | 0.232 | 0.684 | 0.543 | 0.279 |

## Interpretation

Legacy pybis restarts the switching coefficient waveform on each input edge. In very short pulses, that can let Ku/Kd advance as if the previous transition were a clean full transition.

The experimental state-continuous model used here is wrong because a single `PSTATE` is not a valid substitute for HSPICE's independent `Ku/Kd` event state. In the 1 ns case, HSPICE briefly turns the pulldown coefficient off and produces a small partial output pulse. The state-continuous model keeps `Kd` near 1 and `Ku` near 0, so the pad stays near 0 for the wrong reason.

The apparent pad improvement is therefore a false pass. Coefficient agreement must be a hard gate for any retrigger algorithm, and this implementation fails that gate.

## Root Cause

- `PSTATE * rising_duration_ns` samples the rising table too early for short pulses, so `Ku` remains near zero.
- `(1 - PSTATE) * falling_duration_ns` samples the falling table near its settled endpoint when `PSTATE` is still small, so `Kd` remains near one.
- The algorithm treats IBIS waveform tables like normalized progress curves. They are not; they are event waveforms extracted under a fixture and HSPICE applies its own stateful switching logic.

## Next Direction

The next algorithm should fit or emulate HSPICE `Ku/Kd` trajectories directly. A candidate is a two-state coefficient ODE where each new edge changes the target and time constant from the current `Ku/Kd`, with coefficient continuity as the primary objective and pad waveform as a secondary check.
