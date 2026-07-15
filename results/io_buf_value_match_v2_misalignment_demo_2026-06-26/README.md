# Value-Matched Replay v2 Misalignment Demo

This is the v2 version of `io_buf_value_match_misalignment_demo_2026-06-25`.
It uses cached/generated artifacts only; no HSPICE or ngspice simulation is rerun.

## Core Finding

- V2 fixes the confirmed v1 timer/latch bug: active `VMARG` backstep is `0 ns`.
- V2 completes `short_pulse_2ns_high`, while v1 value-match had a numeric failure.
- V2 now latches a pre-edge-like coefficient state. At the falling edge the coefficient state is about `Ku=0.264`, `Kd=0.053`; the v2 latch captures `Ku=0.279`, `Kd=0.064` with source errors `+0.007` / `+0.010`.
- That latched state is still incompatible with one shared falling-table replay start: `TF_KU=0.847 ns`, `TF_KD=2.498 ns`, disagreement `1.652 ns`.
- Coefficient result remains wrong: v2 `Ku` peak is `0.282` while HSPICE native IBIS peaks at `0.543` for this 2 ns case.
- Therefore the implementation bugs are fixed, but value-matched table replay is still not a good short-pulse model.

## Figures

- `01_event_context.png`: same context style as the old demo: input, pad, Ku, and Kd overlays.
- `02_rising_state_snapshot.png`: the corrected v2-latched state, with explicit source-error annotation.
- `03_inverse_mapping_to_falling_tables.png`: the same state maps to badly separated falling-table start times.
- `04_forced_shared_midpoint.png`: a single shared replay start creates coefficient value errors.
- `05_time_domain_consequence.png`: v2 hold/timer diagnostics plus Ku/Kd consequence. This plot shows the important distinction: target hold and `VMARG` are now stable, but the coefficients are still wrong.
- `06_misalignment_summary.png`: one-slide presentation summary.
- `value_match_v2_misalignment_summary.csv`: numeric values used by the figures.

## Interpretation

V2 did what it was supposed to do as a diagnostic: it separated implementation bugs from a real modeling limitation.
The old v1 failure had a timer/latch bug, and the first v2 demo still sampled after the legacy replay path had switched.
The corrected v2 result removes the active `VMARG` backstep, keeps the target on the pending state until match activation, and samples a pre-edge-like state. What remains is the important limitation: that state still maps to incompatible Ku/Kd falling-table start times.

That means the next algorithm should not keep trying to force one replay time onto both coefficients.
A better direction is an independent hidden-state or gate-charge model where Ku and Kd each carry their own continuous state.
