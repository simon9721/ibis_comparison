# Realistic-Pulse Experiment Design

## Why The Old Stress Was Too Aggressive

The earlier reversal studies used a `1 ps` runtime input edge. The three transistor references are 0.18 um-class circuits:

- `io_buf`: TSMC-style 0.18 um BSIM3 devices, with deliberately long output-device channel lengths.
- `inv_chain`: HL18G 180 nm devices in an eight-stage tapered chain.
- `ex2`: TSMC-style 0.18 um extracted multistage buffer.

A 1 ps rail-to-rail command is therefore an impulse-like numerical and circuit stress. It is useful as a limiting experiment but not as the main evidence for realistic pulse handling.

## Runtime Slews

The new primary runtime slews are:

- `100 ps`: aggressive realistic stress.
- `250 ps`: moderate realistic input.

A `50 ps` edge is retained only in the transistor normal-transition characterization so the report can show sensitivity to input slew. It is not used as the primary pulse campaign.

The runtime input slew is separate from the `1 ns` or `5 ps` transition setting used when the IBIS file was characterized. Both IBIS profiles are tested with the same 100 ps and 250 ps runtime commands.

The transistor libraries do not provide a board-interface slew specification, so `100 ps` and `250 ps` are engineering stress points, not claimed datasheet limits. Their reasonableness is checked against each circuit's measured loaded transition: roughly `1.45-1.48 ns` for `io_buf`, `58-93 ps` for `inv_chain`, and `365-444 ps` for `ex2`.

## Full-Amplitude Pulse Definition

The input is a full-amplitude trapezoid, with the minimum-width case becoming a full-swing triangle whose rising and falling ramps meet at the supply rail. Pulse width is measured between the 50% points of the rising and falling command edges. The minimum tested pulse width equals the input edge duration. This avoids calling a truncated, reduced-amplitude command a normal digital pulse.

## Adaptive Width Selection

The campaign does not assume that the same pulse width has the same physical meaning for every buffer.

1. Run a long-pulse HSPICE transistor simulation.
2. Measure loaded low/high levels, 50% propagation delay, and 10-90% output transition time.
3. Build a buffer-specific coarse pulse grid from those measurements.
4. Run transistor-only short-high and short-low sweeps.
5. Interpolate and rerun around 20%, 55%, and 85% output excursion.
6. Select the nearest measured cases and record whether the target was actually attainable.

The three targets mean:

- `visible`: the transistor responds, but only weakly.
- `mid_transition`: the output is near the middle of its loaded swing.
- `near_settled`: the output is close to its final value but has not fully settled.

If the minimum full-amplitude pulse already produces more than 95% output excursion, the result is labeled `NO_PARTIAL_REGION_AT_MIN_FULL_AMPLITUDE_PULSE`. The pipeline does not invent a shorter partial case.

## Internal Transistor Evidence

The transistor decks also save the final output-stage control nodes:

- `io_buf`: separate pullup and pulldown control nodes `n2` and `n3`.
- `inv_chain`: `VOUT7`, the gate command of the eighth output inverter.
- `ex2`: `n4`, the shared gate command of the output stage.

These nodes help distinguish:

- partial pad voltage caused only by load inertia;
- a genuinely partial output-stage command;
- a pulse that a multistage circuit regenerates into a nearly complete internal transition.

## Comparison Matrix

Selected cases are compared using:

- HSPICE transistor circuit: pad and internal control truth.
- HSPICE native IBIS: pad plus native `Ku/Kd` diagnostics.
- ngspice full gate-state model: gate-state path always active.
- ngspice hybrid model: legacy replay for normal operation, gate state during detected reversal.

The ngspice models use dual Ku/Kd directional residuals. Numeric failures and timeouts are preserved as results.

## Interpretation

No single waveform is sufficient:

- Transistor pad agreement tests circuit-level output behavior.
- Native-IBIS `Ku/Kd` agreement tests whether pybis reproduces the native IBIS instance.
- Internal transistor nodes test whether a case really interrupts the output-stage command.
- Hybrid detector activity and coefficient continuity test the handoff itself.

Native-IBIS `Ku/Kd` are not transistor-internal truth because the transistor reference has no corresponding coefficient nodes.
