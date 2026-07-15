# Command-Age Kd Hold Held-Out Validation

This diagnostic tests whether the short-high Kd recovery hold law is real or just a two-parameter line through three points. It trains on the existing 0.5 ns, 1 ns, and 2 ns high-pulse cases, then predicts a held-out 1.5 ns high-pulse HSPICE reference.

## Headline Finding

- Training law: `T_hold50 = 1.7153 + 0.3119 * command_age` ns.
- Training RMS: `21.5 ps`.
- Held-out 1.5 ns predicted T_hold50: `2.1832 ns`.
- Held-out 1.5 ns measured T_hold50: `2.1338 ns`.
- Held-out error: `+49.4 ps` with tolerance `+/-30 ps`.
- Verdict: `FAIL`.
- Held-out HSPICE reference source: `run`.

## Measurements

| Case | Role | Age ns | T_hold50 ns | Kd min ns | Tau10-90 ns |
|---|---|---:|---:|---:|---:|
| short_pulse_500ps_high | train | 0.5000 | 1.8514 | 5.8725 | 0.1737 |
| short_pulse_1ns_high | train | 1.0000 | 2.0571 | 6.3866 | 0.1887 |
| short_pulse_2ns_high | train | 2.0000 | 2.3293 | 7.5387 | 0.1857 |
| short_pulse_1p5ns_high | heldout | 1.5000 | 2.1338 | 6.8725 | 0.1882 |

## Implementation Spec If Verdict Passes

- Add an opt-in mode named `InputDrivenTwoStateGateDirectionalResidualCommandAgeHold`.
- Keep directional maps, Kd residual, and normal long-pulse behavior unchanged.
- On the rising input edge, launch an NMOS-off command-age clock independent of the delayed `GDN` node.
- On a falling reverse edge during short-high interrupted turn-off, latch `AGE = t_reverse - t_turn_off_command`.
- Compute `T_hold = A + B * clamp(AGE, 0.5 ns, 2.0 ns)` using the validated constants above.
- Release Kd recovery at `reverse_edge + T_hold`, then use the existing fixed fast recovery shape/rate.
- The new path must fire only for short-high interrupted turn-off. Long-pulse, short-low, and unrelated cases must remain unchanged to three significant figures versus directional-residual.

## Interpretation Rule

- If the held-out test passes, command-age is a causally usable latch variable and the next candidate is worth implementing.
- If the held-out test fails, stop adding hold-law variants and report the ceiling: the two-state model captures directionality, residual undershoot, and fixed recovery rate, but interrupted-turn-off recovery needs command-phase information not exposed by IBIS.

Files:

- `command_age_hold_training_and_heldout.csv`
- `command_age_hold_validation_summary.csv`
- `command_age_hold_heldout_validation.png`
