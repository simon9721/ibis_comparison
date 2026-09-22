# Decoupling the SPICE engine from the IBIS implementation

Every "native IBIS vs pybis" comparison in this project changes two variables at
once: the SPICE engine (HSPICE vs ngspice) and the IBIS implementation (HSPICE's
native B-element vs pybis's generated subcircuit). A difference could be either.
The convergence work already caught one instance -- ~half of the reported 9.9 ps
"model lag" was ngspice running unconverged at a 1 ps step, an engine artifact.

To separate them, the *same* pybis model has to run in *both* engines. pybis
emits ngspice-only syntax, so `scripts/pybis_subckt_to_hspice.py` translates its
InputDriven subcircuit into HSPICE: drop the `params:` keyword, strip `{}` param
braces, `B ... V=`/`I=` become `E ... VOL=`/`G ... CUR=`, and the 100+ point pwl
tables -- which overflow HSPICE's behavioural-expression buffer -- become native
`G ... PWL(1)` lookup elements. Verified faithful at the edges: same-model
ngspice and HSPICE agree to 0.0-0.5 ps on both.

## The 2x2 (base8, 50 ohm + 2 pF, converged: ngspice 0.2 ps reltol 1e-5)

|                        | 50% crossing |
|------------------------|---:|
| pybis model, ngspice   | 5.3371 ns |
| pybis model, HSPICE    | 5.3375 ns |
| native IBIS, HSPICE    | 5.3319 ns |

- **Engine** (same pybis model, ngspice vs HSPICE): **-0.5 ps rising, -0.0 ps falling.**
- **Model** (same HSPICE engine, pybis vs native): **+5.6 ps.**

## Conclusion

Once the solver is converged, the two engines running the identical model agree
to within half a picosecond. **The SPICE engine is not the source of the
pybis-vs-native difference.** The ~5.6 ps is a genuine IBIS-implementation
difference: pybis reconstructs the pad from Ku(t) x I_pu(V) + explicit C_comp,
HSPICE's B-element from the V-T tables, and those diverge by ~5.6 ps at full
C_comp (reducible by C_comp scaling -- see the converged C_comp sweep).

This also corrects the earlier record: the original 9.9 ps was model (~5.6 ps)
plus an unconverged-ngspice artifact (~4 ps at the 1 ps step). At converged
accuracy the model difference alone is ~5.6 ps.

## Caveat on the translation

HSPICE's `PWL(1)` extrapolates beyond the table ends using the end slope, where
ngspice's `pwl()` clamps. When an idle-state node briefly runs off the table the
HSPICE run shows a large spurious spike (-4394 V at t=2.7 ns here) that ngspice
does not. It does not touch the edges -- both 50% crossings and the edge shapes
agree -- so the decoupling result stands, but whole-record RMSE is polluted.
Making the translation faithful everywhere means clamping each PWL(1) control to
its table range (or using HSPICE's extrapolation-limit option). Not needed for
the timing decoupling; noted for reuse.

## Files
- `../../scripts/pybis_subckt_to_hspice.py` -- the translator
- `base8_driver_hspice.sub` -- the translated base8 model
