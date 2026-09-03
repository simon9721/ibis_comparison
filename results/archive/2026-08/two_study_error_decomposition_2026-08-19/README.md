# Three-buffer stress evidence, split into two studies

The two references disagree about what a stressed short pulse is, and they
disagree in opposite directions depending on the buffer:

- `inv_chain` and `ex2` native IBIS **over-responds**. A native-anchored width
  is short, and at that width the transistor has moved 0-20%.
- `io_buf` native IBIS **under-responds**. A native-anchored width is long, and
  at that width the transistor is at 68-102%.

So there is no single axis that stresses both references across all three
buffers, and the evidence is split by question rather than forced onto one.
The one place they do overlap usefully is `io_buf` short-high, where a
native-anchored sweep leaves the transistor at 68-98% -- both references are
meaningfully stressed and that column of Study B is also a silicon result.

Never compare a target percentage across the two studies: the same nominal
figure is a different pulse width in each.

## Full-edge baseline

On a complete, uninterrupted edge native IBIS tracks the transistor closely.
This is what makes Study A's split meaningful -- the stressed-case gap is a
statement about interrupted transitions, not about the IBIS models being poor
in general.

| device | native IBIS vs transistor | swing ratio |
| ------ | ------------------------: | ----------: |
| `io_buf` | 71.14 mV | 0.9731 |
| `inv_chain` | 21.65 mV | 0.9977 |
| `ex2` | 18.98 mV | 0.9964 |

## Study A -- silicon accuracy

**Question:** does the flow predict silicon?  
**Anchor:** HSPICE transistor, so silicon is genuinely stressed.  
**Reference:** HSPICE transistor.

The total error is split into the part IBIS contributes and the part pybis
contributes:

```text
transistor --[IBIS format gap]-- native IBIS --[pybis gap]-- pybis
```

Across 29 cases, mean IBIS format gap is **316 mV** and mean pybis gap is **241 mV**. Where the first
dominates, no amount of pybis work can close the remaining distance.

**The two gaps do not add.** They are RMSEs of signed errors that can point
in opposite directions. On `inv_chain` short-high the total against silicon is
*smaller* than either contribution, because pybis error partly cancels IBIS
error -- the model is closer to silicon than the reference it was fitted to,
by luck rather than by merit. The figure groups the three quantities rather
than stacking them for exactly this reason.

Data: [study_a_silicon_accuracy.csv](./study_a_silicon_accuracy.csv)  
Figure: [plots/01_study_a_error_decomposition.png](./plots/01_study_a_error_decomposition.png)

> **1 case(s) are absent.** `io_buf`'s fast IBIS was regenerated at
> a 50 ps characterization edge on 2026-08-19. These cases did not complete in
> the refreshed sweep -- the gate-state model hit an ngspice timestep collapse
> -- and are reported as missing rather than back-filled from the superseded
> 5 ps file, whose fitted endpoints and delays are invalid. A pre-regeneration
> number placed in this column would not be comparable with the rest of it.

> Affected: `io_buf/short_high/70%`

## Study B -- algorithm fidelity

**Question:** does pybis reproduce the IBIS algorithm in ngspice?  
**Anchor:** HSPICE native IBIS, so the graded reference is genuinely stressed.  
**Reference:** HSPICE native IBIS.

This is the question pybis can actually be held to: it converts an `.ibs` file
into an ngspice subcircuit and owns nothing upstream of that. It says nothing
about silicon accuracy -- the transistor is nearly static in these cases, as
the `transistor_swing_percent` column records.

Data: [study_b_algorithm_fidelity.csv](./study_b_algorithm_fidelity.csv)  
Figure: [plots/02_reference_disagreement.png](./plots/02_reference_disagreement.png)

## Regenerating

```powershell
py -3.14 scripts/build_two_study_error_decomposition.py
```

Cached data only; no simulator is launched.
