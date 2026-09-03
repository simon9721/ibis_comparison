# Three-Buffer PRBS Hybrid V2

Hybrid V2 keeps legacy Ku(t)/Kd(t) during normal operation. At an interrupted reversal it samples the continuously tracked directional gate-map coefficients once, then advances independent normalized legacy Ku(t) and Kd(t) transition shapes from those sampled values.

## Execution

- Completed ngspice cases: `1/1`.
- HSPICE simulations run by this study: `0`. All references come from the cached Phase 1 numeric waveforms.
- Cases improving pad, Ku, and Kd together versus the old hybrid: `0`.
- Mixed cases: `1`.
- Numeric failures: `0`.
- Captured Hybrid V2 replay events: `8`.

## Interpretation

A useful result must improve coefficients as well as pad voltage. Large start-error or coefficient-step values mean the gate-map initialization itself is discontinuous; long active fractions mean the replay still behaves like a mode takeover under dense PRBS.

## Files

- `metrics.csv`: pad/Ku/Kd errors, eye metrics, active fraction, coefficient steps, and old-hybrid deltas.
- `hybrid_v2_events.csv`: every replay event with direction, duration, sampled coefficients, and event-window errors.
- `waveforms/`: complete aligned numeric data, including V2 samples, progress, replay, and active state.
- `plots/00_hybrid_v2_metric_summary.png`: matrix-level comparison.
- `plots/cases/`: one detailed evidence figure per case.
