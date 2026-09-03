# Coefficient-State Interrupted Switching Demo

This demo uses `short_pulse_1ns_high` to inspect the experimental `InputDrivenCoeffState` algorithm against HSPICE native IBIS and legacy pybis.

The input rises at about 5 ns and falls again at about 6 ns, before the normal output transition settles.

## Figures

- `figures/01_interrupted_event_timeline.png`: input, pad, Ku/Kd, and CoeffState target/state diagnostics.
- `figures/02_ku_kd_state_difference.png`: focused Ku/Kd comparison for the interrupted event.
- `figures/03_pad_consequence.png`: how the coefficient behavior maps into pad waveform error.
- `figures/04_control_vs_interrupted.png`: normal full-toggle control versus interrupted switching.
- `figures/05_short_pulse_summary.png`: all short-pulse widths from the coefficient-state sweep.

## Key Numbers

- Settled high from the normal full-toggle bench: `1.545 V`.
- At the reverse command, HSPICE pad is only `-0.009 V`, so the output is not settled.
- HSPICE Ku peak: `0.075`.
- Legacy pybis Ku peak: `1.013`.
- CoeffState Ku peak: `0.361`.
- HSPICE pad peak: `0.062 V`.
- Legacy pybis pad peak: `1.516 V`.
- CoeffState pad peak: `0.219 V`.
- Legacy pad RMSE: `634.1 mV`.
- CoeffState pad RMSE: `95.3 mV`.
- Legacy max Ku/Kd RMSE: `0.489`.
- CoeffState max Ku/Kd RMSE: `0.364`.

## Interpretation

The new algorithm fixes the worst legacy failure mode: Ku no longer plays a full transition after a very short pulse. The pad pulse is much smaller and closer to HSPICE.

However, it is still not correct enough to become the default. In this 1 ns case, CoeffState Ku is still higher than HSPICE, and Kd recovers smoothly instead of reproducing HSPICE's sharper dip/recovery shape.

The control-vs-interrupted figure also shows the tradeoff: the branch-state model helps interrupted pulses, but the full-toggle case regresses compared with legacy pybis. The next algorithm should therefore be hybrid or event-aware: keep legacy behavior for complete edges, and use coefficient-state correction only when a retrigger is detected before the previous transition settles.
