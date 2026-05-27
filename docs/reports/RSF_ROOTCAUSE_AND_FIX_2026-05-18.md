# RSF Root Cause And Fix — 2026-05-18

## Summary

The bad `ngspice_pybis` rise-steady-fall behavior was a real model bug, not a bench artifact and not a "flat time too short" problem.

The immediate failure was:

- input commanded high for many ns
- converted IBIS-SPICE briefly rose
- then collapsed back near 0 V while the input was still high

That behavior is now fixed in:

- [ngspice_pybis/driver_OutputInput_Typical.sub](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/driver_OutputInput_Typical.sub)

## Root Cause

The broken model file was not using the original state-aware selector logic from `pybis2spice/subcircuit.py`.

Instead, the emitted `.sub` had a later smoothed selector/handoff block that chose the `Ku/Kd` family mainly from `N2` polarity and removed the explicit `NI` state term.

Broken selector pattern in the old generated model:

- `B24..B29` used smoothed `tanh(...)` gates
- steady-high hold depended too strongly on `N2`
- once `N2` decayed toward zero after a rising edge, the selector drifted toward the falling-family hold path

Observed consequence:

- `KUR0` and `KUF0` tables themselves were sane
- but final `Ku` followed the falling family during the commanded high hold
- `Kd` returned high while input was still high
- output collapsed low during the intended high interval

## Validation That Isolated The Bug

### 1. Longer flat time did not help

The long-hold RSF bench still failed before the fix:

- [ngspice_pybis/tb_validation_rsf_longhold_ngspice_pybis_batch.sp](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/tb_validation_rsf_longhold_ngspice_pybis_batch.sp)

Before the fix, during the long high interval:

- `Ku ~ 0.0004`
- `Kd ~ 1.0019`
- `pad ~ 0.0003 V`

So this was not a data-rate or insufficient-hold-time issue.

### 2. Internal debug nodes showed wrong-family selection

Debug bench:

- [ngspice_pybis/tb_validation_rsf_longhold_debug_ngspice_pybis_batch.sp](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/tb_validation_rsf_longhold_debug_ngspice_pybis_batch.sp)

Key observation from the broken model:

- `KUR0` rose as expected
- `KUF0` decayed as expected
- final `Ku` was tracking `KUF0` in steady high

That directly identified the selector/handoff logic as the bug.

### 3. Generator source and emitted model had diverged

Generator source still had the original state-aware ternary logic:

- [pybis2spice/subcircuit.py](C:/Users/simom/Desktop/spice/pybis2spice/pybis2spice/subcircuit.py:287)

But the emitted model file being simulated had a different smoothed selector.

So the practical fix was to regenerate the model from the Python source and promote that regenerated file back into the comparison project.

## Fix Applied

Regenerated the model from the current `pybis2spice` source and replaced the broken canonical model:

- regenerated diagnostic copy:
  - [ngspice_pybis/driver_OutputInput_Typical_regen.sub](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/driver_OutputInput_Typical_regen.sub)
- promoted canonical model:
  - [ngspice_pybis/driver_OutputInput_Typical.sub](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/driver_OutputInput_Typical.sub)

The fixed selector block is now the state-aware ternary form:

- `B24 NKUF ... (V(NI) > 0 || V(N2) < -0.1) ? 1 : V(KUF0)`
- `B26 NKUR ... (V(NI) > 0 && V(N3) < 0.1) ? V(KUR0) : 0`
- `B28 Ku ... (V(NI) > 0 && V(N2) > -0.1) ? V(NKUR) : V(NKUF)`
- `B29 Kd ... (V(NI) > 0 && V(N2) > -0.1) ? V(NKDR) : V(NKDF)`

## Result After The Fix

The catastrophic wrong-state behavior is gone.

### pybis long-hold RSF after the fix

Raw:

- [ngspice_pybis/tb_validation_rsf_longhold_ngspice_pybis_batch.raw](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/tb_validation_rsf_longhold_ngspice_pybis_batch.raw)

Representative points:

- `5.0007 ns`: `pad=1.4176 V`, `Ku=0.9340`, `Kd=0.00513`
- `9.9987 ns`: `pad=1.4965 V`, `Ku=0.9957`, `Kd=0.000885`
- `14.9995 ns`: `pad=1.4965 V`, `Ku=0.9957`, `Kd=0.000885`
- `19.9994 ns`: `pad=1.4965 V`, `Ku=0.9957`, `Kd=0.000885`
- `22.9989 ns`: `pad=0.00112 V`, `Ku=0.000728`, `Kd=0.000560`

This shows the model now:

- rises
- holds high while the input is high
- falls after the commanded falling edge

### pybis short RSF after the fix

Raw:

- [ngspice_pybis/tb_validation_rfr_ngspice_pybis_12n_batch.raw](C:/Users/simom/Desktop/IBIS_Comparison/ngspice_pybis/tb_validation_rfr_ngspice_pybis_12n_batch.raw)

Representative points:

- `3.0007 ns`: `pad=0.3024 V`
- `5.0007 ns`: `pad=1.4176 V`
- `8.4996 ns`: `pad=1.4965 V`
- `9.4988 ns`: `pad=1.5196 V`
- `10.9988 ns`: `pad=0.00112 V`

## Updated Plots

Short separate overlay:

- [plots/validation/refspice_vs_pybis_rsf_pad_separate.png](C:/Users/simom/Desktop/IBIS_Comparison/plots/validation/refspice_vs_pybis_rsf_pad_separate.png)
- [plots/validation/refspice_vs_pybis_rsf_load_separate.png](C:/Users/simom/Desktop/IBIS_Comparison/plots/validation/refspice_vs_pybis_rsf_load_separate.png)
- [plots/validation/refspice_vs_pybis_rsf_kukd_separate.png](C:/Users/simom/Desktop/IBIS_Comparison/plots/validation/refspice_vs_pybis_rsf_kukd_separate.png)

Long-hold separate overlay:

- [plots/validation/refspice_vs_pybis_rsf_longhold_pad_separate.png](C:/Users/simom/Desktop/IBIS_Comparison/plots/validation/refspice_vs_pybis_rsf_longhold_pad_separate.png)
- [plots/validation/refspice_vs_pybis_rsf_longhold_load_separate.png](C:/Users/simom/Desktop/IBIS_Comparison/plots/validation/refspice_vs_pybis_rsf_longhold_load_separate.png)

Long-hold plotting script:

- [scripts/plot_refspice_vs_pybis_rsf_longhold_from_separate.py](C:/Users/simom/Desktop/IBIS_Comparison/scripts/plot_refspice_vs_pybis_rsf_longhold_from_separate.py)

## What The Remaining Difference Means

After the selector fix, the converted model behavior matches the IBIS waveform timing much more closely than the transistor reference does under this compact validation load.

Examples:

### IBIS falling waveform (`V_fixture=0`, typical)

From [models/io_buf.ibs](C:/Users/simom/Desktop/IBIS_Comparison/models/io_buf.ibs:4615):

- `0.4985 ns` after the fall start: `Vtyp = 1.51 V`
- `1.0030 ns` after the fall start: `Vtyp = 0.304 V`
- `1.5015 ns` after the fall start: `Vtyp ≈ 1.01 mV`

The fixed converted model shows nearly the same shape:

- about `0.494 ns` after the fall start: `pad ≈ 1.520 V`
- about `1.994 ns` after the fall start: `pad ≈ 1.12 mV`

### IBIS rising waveform (`V_fixture=0`, typical)

From [models/io_buf.ibs](C:/Users/simom/Desktop/IBIS_Comparison/models/io_buf.ibs:599):

- `2.0000 ns` after the rise start: `Vtyp = 0.351 V`
- `4.0000 ns` after the rise start: `Vtyp = 1.463 V`
- `6.0000 ns` after the rise start: `Vtyp = 1.537 V`

The fixed converted model is in the same regime:

- about `1.996 ns` after the rise start: `pad ≈ 0.302 V`
- about `3.996 ns` after the rise start: `pad ≈ 1.418 V`
- about `8.994 ns` after the rise start: `pad ≈ 1.496 V`

## Conclusion

The main pybis bug is fixed.

What was wrong:

- wrong runtime selector/handoff logic in the generated `.sub`
- falling-family `K` values were being selected during steady-high hold

What is true now:

- the converted ngspice model no longer collapses to the wrong state
- the simple RSF validation behaves sensibly
- remaining mismatch against `refspice` is now mostly a correlation question between the transistor reference and the IBIS model, not a fundamental runtime-control bug in the converted model
