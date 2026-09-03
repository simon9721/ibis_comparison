# Three-Buffer PRBS Hybrid V2

Hybrid V2 keeps legacy Ku(t)/Kd(t) during normal operation. At an interrupted reversal it freezes the continuously tracked directional gate-map coefficients in capacitor-backed sample/hold nodes, then advances independent normalized legacy Ku(t) and Kd(t) transition shapes from those anchors.

## Headline Finding

- The exact sampled-start proposal is **not viable in its current form**.
- A relative RMSE improvement is not a pass: the handoff must also be continuous, coefficients must remain physical, and the output eye must remain usable.
- The main failure is coordinate mismatch at handoff: the directional gate-map value can be far from the currently visible legacy coefficient at the same reversal. Freezing that value preserves the mismatch rather than fixing it.
- Independent normalized Ku/Kd progress preserves the table's relative transition shape, but it cannot repair a wrong starting anchor.

## Execution

- Completed ngspice cases: `10/12`.
- HSPICE simulations run by this study: `0`. All references come from the cached Phase 1 numeric waveforms.
- Cases improving pad, Ku, and Kd together versus the old hybrid: `2`.
- Cases passing all Hybrid V2 validity gates: `0`.
- Completed cases with an actual Hybrid V2 trigger: `6`.
- Triggered cases with invalid coefficient range: `5`.
- Triggered cases with a handoff jump above 0.02 but otherwise valid range: `1`.
- Mixed cases: `3`.
- Numeric failures: `2`.
- Captured Hybrid V2 replay events: `47`.

## Interpretation

A useful result must improve coefficients as well as pad voltage. `comparison_class` is relative to the old hybrid; `validation_class` is the actual safety result. Large event-start error or handoff jump means the gate-map initialization is discontinuous. A long active fraction means the replay has become a sustained alternate mode rather than a brief retrigger correction.

## Runtime Sequence

1. Legacy Ku(t)/Kd(t) drive the output while hidden GUP/GDN states track every command.
2. A detected reversal opens a 20 ps sample window and freezes Ku(GUP)/Kd(GDN).
3. After 25 ps, separate normalized Ku(t) and Kd(t) progress coordinates advance from the frozen anchors toward the new endpoints.
4. Outside that replay interval, control returns to legacy Ku(t)/Kd(t).

## Files

- `metrics.csv`: pad/Ku/Kd errors, eye metrics, active fraction, coefficient steps, and old-hybrid deltas.
- `hybrid_v2_events.csv`: every replay event with direction, duration, sampled coefficients, and event-window errors.
- `waveforms/`: complete aligned numeric data, including V2 samples, progress, replay, and active state.
- `plots/00_hybrid_v2_metric_summary.png`: matrix-level comparison.
- `plots/cases/`: one detailed evidence figure per case.
- `../three_buffer_prbs_hybrid_v2_continuous_anchor_2026-07-31/`: archived moving-anchor approximation; retained as diagnostic evidence only.

## Failures

- `io_buf / prbs7_ui_2ns_edge_50ps`: `NUMERIC_FAIL`
- `io_buf / prbs7_ui_1ns_edge_50ps`: `NUMERIC_FAIL`
