# Phase 1 Plan: Direct-Load PRBS7 History Study

## Objective

Measure whether the three buffer representations preserve waveform and internal-state history under a realistic repeated bit stream before a channel is introduced.

## Fixed Electrical Setup

- Devices: `io_buf`, `inv_chain`, and `ex2`.
- IBIS input: fast-edge model for each device.
- PRBS: deterministic PRBS7, polynomial `x^7 + x^6 + 1`, 127 bits.
- Runtime edge: 50 ps.
- UI sweep: 2 ns, 1 ns, 500 ps, and 250 ps.
- Load: direct `50 ohm || 2 pF`.
- HSPICE simulates two full PRBS periods.
- ngspice simulates and analyzes the first 31 PRBS7 bits plus recovery.
- Those 31 bits contain all eight possible previous/current/next-bit contexts.
- The bounded ngspice window is required because longer gate-state runs exposed a reproducible numerical stall.

## Flows

1. HSPICE transistor reference.
2. HSPICE native IBIS.
3. ngspice full gate-state model.
4. ngspice legacy-normal/gate-on-reversal hybrid.

## Evidence

- Absolute-time pad, Ku, and Kd agreement.
- Independently optimized eye height, eye width, and sample delay.
- Three-bit (`previous/current/next`) history classes.
- Worst-bit waveform windows.
- Full numeric waveforms behind every case.

## Interpretation Boundary

No transmission line is used in Phase 1. This intentionally isolates buffer and switching-state behavior. A matched line belongs in Phase 2 after this direct-load baseline is understood.

The bounded ngspice window contains every three-bit context. Longer-stream failure attempts remain in `solver_attempts.csv`; they are evidence, not discarded runs.
