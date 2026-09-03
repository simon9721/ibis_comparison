# Hybrid V3 Aligned-Replay Pilot Findings

## Question

Can Hybrid V2 be repaired by sampling the visible coefficient state at a reversal, mapping `Ku` and `Kd` independently onto the opposite complete-transition tables, and replaying those tables with a fresh timer?

## What Was Corrected

- The old `HNX` timer is not used by V3 replay. `V3ELAPSED` is a dedicated, monotonic coordinate.
- The pre-reversal visible `Ku/Kd` values are latched once. A hidden gate-state anchor is accepted only if both gate-derived coefficients are within `0.02` of the visible values.
- `Ku` and `Kd` receive independent latest-crossing table starts. The replay correction is exactly continuous at entry and decays to zero by the original table endpoint.
- A 100 ps handoff guard covers the two 20 ps latch stages and solver settling. Legacy `InputDriven` and old Hybrid V2 are unchanged.

## Structural Result

The implementation repair succeeded:

- 6/6 ngspice cases completed.
- 6/6 detected exactly one interrupted event.
- 6/6 entry handoffs stayed within `0.02` for both coefficients.
- No V3 elapsed-time or table-argument backstep occurred.
- Five cases stayed inside the `[-0.2, 1.2]` active coefficient range. `ex2` short-low did not (`Ku=1.2823`, `Kd=-0.2339`).

See `v3_structural_diagnostics.csv` for the measured anchors, start times, backsteps, and ranges.

## Accuracy Result

The repaired mechanism is not general enough:

| Buffer | Direction | Pad RMSE | Ku RMSE | Kd RMSE | Ku/Kd start disagreement |
|---|---|---:|---:|---:|---:|
| io_buf | short-high | 27.16 mV | 0.1353 | 0.3820 | 1.528 ns |
| io_buf | short-low | 259.63 mV | 0.6844 | 0.3716 | 4.557 ns |
| inv_chain | short-high | 635.35 mV | 0.5759 | 0.7165 | 0.181 ns |
| inv_chain | short-low | 909.36 mV | 0.6060 | 0.3530 | 3.127 ns |
| ex2 | short-high | 590.17 mV | 0.5029 | 0.7059 | 0.098 ns |
| ex2 | short-low | 914.95 mV | 0.6620 | 0.2597 | 0.231 ns |

Compared with the full gate-state model, V3 improves pad, Ku, and Kd in only 2/6 cases each. It severely regresses the previously strong `ex2` short-high case: pad RMSE changes from `31.36 mV` to `590.17 mV`.

## Root Cause

The old Hybrid V2 had implementation bugs, but those were not its only limitation. A current pair `(Ku, Kd)` does not uniquely identify one physically correct time point on the opposite complete-transition tables.

- Large start disagreement is direct evidence of ambiguity. For `io_buf` short-low, `Ku` and `Kd` imply starts separated by `4.557 ns`.
- Correct initial state is not sufficient. `inv_chain` short-high begins very close to native IBIS (`Ku=0.00032`, `Kd=1.00229`) yet diverges strongly during replay.
- Small start disagreement is also not sufficient when the pre-reversal model state is already wrong. `ex2` short-high has only `0.098 ns` start disagreement but large post-reversal errors.
- `io_buf` short-high is still a pad-only partial success: pad RMSE is low, while Kd RMSE remains `0.3820`.

The missing information is transition history/internal state, not merely a cleaner timer or one better matched table index.

## Decision

Do not run the full 90/80/70/60/50% sweep with V3. The six-case, three-buffer pilot passes the implementation gate but fails the model-quality gate. Preserve V3 as a negative/diagnostic baseline for aligned table replay, not as the next production hybrid.

No HSPICE simulation was launched for this retry. All reference waveforms came from the cached August 14 stress study.
