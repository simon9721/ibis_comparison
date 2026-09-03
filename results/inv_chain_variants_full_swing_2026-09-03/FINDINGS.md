# Do the models track silicon when the silicon changes?

Item 1 of `0902_plan.md`, the part it exists for. Four inverter-chain variants,
each changing one property, run three ways on an identical bench:

    transistor    HSPICE on the variant netlist -- ground truth, moves with the silicon
    native IBIS   HSPICE reading the generated .ibs -- the bar
    pybis         ngspice on the subcircuit pybis builds from the same .ibs

Bench: 1 ps input edges at 5 and 15 ns, 50 ohm in parallel with 2 pF, 22 ns —
the same bench the July sanity checks used. Full swing only. Each variant uses
the IBIS model `select_s2ibispy_parameters.py` chose for it, so this is also the
first end-to-end test of whether item 3's procedure pays off downstream.

## The measurements

| variant | build | RMSE | worst | rise shift | fall shift |
|---|---|---:|---:|---:|---:|
| `base8` | native IBIS | 3.85 mV | 91.9 mV | −0.0 ps | +3.7 ps |
| | pybis | 11.25 mV | 188.7 mV | +9.3 ps | +7.9 ps |
| `stage4` | native IBIS | 3.22 mV | 83.4 mV | +0.9 ps | +3.4 ps |
| | pybis | 10.95 mV | 179.0 mV | +9.5 ps | +7.5 ps |
| `skewp` | native IBIS | 1.95 mV | 40.6 mV | −2.8 ps | +1.4 ps |
| | pybis | 6.40 mV | 115.2 mV | +7.1 ps | +5.9 ps |
| `weak` | native IBIS | 1.92 mV | 36.5 mV | −3.3 ps | +0.0 ps |
| | pybis | 5.47 mV | 64.5 mV | +7.2 ps | +4.3 ps |

**Both models track every silicon.** Nothing breaks, nothing diverges, no
variant defeats either model. That is the headline answer, and it was not
guaranteed — these are four different devices.

## 1. Model error is set by pad slew rate, not by the silicon

The variants fall into two groups, and the grouping is not by what was changed:

| variant | pad 20–80% | max dV/dt | native RMSE | pybis RMSE |
|---|---:|---:|---:|---:|
| `base8` | 63.9 ps | 17.87 V/ns | 3.85 | 11.25 |
| `stage4` | 66.1 ps | 17.85 V/ns | 3.22 | 10.95 |
| `skewp` | 104.4 ps | 10.75 V/ns | 1.95 | 6.40 |
| `weak` | 102.9 ps | 10.16 V/ns | 1.92 | 5.47 |

Full-drive variants sit at ~18 V/ns and ~3.5 / 11 mV. Weakened variants sit at
~10 V/ns and ~1.9 / 6 mV. **A 1.7x reduction in slew buys a 2.0x reduction in
native error and a 1.8x reduction in pybis error** — close to proportional.

So it is not that some silicons are harder to model. **Faster pad edges are
harder to model, and drive strength sets the pad edge.** That is a more useful
statement than a per-device error budget, because it predicts: any buffer strong
enough to slew this load quickly will show the same error, whatever its
internals look like.

It also reframes io_buf. Its problems have been treated as io_buf pathologies;
this says a large part of any buffer's error is simply how hard it drives.

## 2. pybis is a constant multiple of native IBIS

| variant | pybis / native |
|---|---:|
| `base8` | 2.9x |
| `stage4` | 3.4x |
| `skewp` | 3.3x |
| `weak` | 2.8x |

Across four different silicons spanning 1.9 to 11.3 mV of absolute error, the
ratio stays between 2.8 and 3.4. **The gap between pybis and native IBIS is a
property of the implementation, not of the device.** A silicon-dependent defect
would not hold that ratio.

That is worth knowing before chasing pybis accuracy on any particular buffer:
the target is a systematic ~3x, and it should be attacked as one thing rather
than four.

## 3. pybis is consistently late, and it is not the characterization edge

pybis runs **+7.1 to +9.5 ps late on the rising edge** on every variant, where
native IBIS sits between −3.3 and +0.9 ps.

Every one of these models was characterized at `tr = 1 ps`, which by the
0.70 x tr law from item 3 builds in about **0.7 ps** of lateness. The observed
7–9 ps is an order of magnitude larger, and native IBIS reading the *same file*
does not show it.

**So this lateness belongs to pybis, not to the IBIS file.** It is the same sign
as the unexplained 70–100 ps io_buf falling-edge lateness (defect B), an order
of magnitude smaller and on a buffer with none of io_buf's complications. If
defect B has a component that is simply "pybis is late", this is that component
in isolation.

## 4. The deliberate asymmetry did not break anything asymmetrically

`skewp` has a PMOS at half its usual strength relative to the NMOS — rise slows,
fall does not. The expectation was that a model might fail asymmetrically.

It does not. pybis is +7.1 ps on rise and +5.9 ps on fall; native IBIS −2.8 and
+1.4. Both edges behave, and `skewp` is among the *best* variants, not the
worst.

This is a useful negative result for the dead-zone story. io_buf's 1.76 ns gap
between pullup-off and pulldown-on has been the most distinctive thing about it,
and deliberately weakening a pullup does **not** reproduce it. Whatever produces
io_buf's dead zone, it is not simply an imbalanced output stage.

## 5. Item 3's procedure holds up downstream

`base8` is characterized on parameters the selector measured (0.623 ns window,
1 ps edge) rather than the shipped 6 ns / 5 ps, and its native IBIS lands at
**3.85 mV** here against **11.04 mV** for the shipped model on the earlier
bench. Two independent decks, consistent conclusion.

## What this does not cover

Full swing only, by design. Nothing here says anything about interrupted
pulses, reversals, or the gate-state model — the pybis build used is the plain
`InputDriven` subcircuit, not gate-state. Those are the next question, and they
are only worth asking now that the clean-edge case is known to hold across four
silicons.

## Files

- `full_swing_comparison.csv` — the table above
- `plots/<variant>_full_swing.png` — rising and falling edge close-ups, all
  three builds
- `<variant>/{transistor,native_ibis,pybis}/` — the three runs, decks and raw
- generated by `scripts/compare_variants_full_swing.py`
