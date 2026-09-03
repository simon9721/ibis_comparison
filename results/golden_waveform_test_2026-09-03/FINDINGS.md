# Golden-waveform test: pybis handles C_comp correctly

**This result overturns the earlier conclusion in
`results/pybis_ccomp_validation_2026-09-03/FINDINGS.md`, which said pybis
over-applies C_comp. It does not.**

## The test

The book's prescribed simulator verification (Leventhal & Green 12.9.6, 17.14,
16.5.1): an IBIS model carries its `[Rising Waveform]` / `[Falling Waveform]`
tables together with the fixture that produced them, so a correct simulator
driving that same fixture must reproduce the table.

It is decisive for C_comp precisely because the fixture is the *characterization*
fixture. pybis extracts Ku/Kd from these tables with the C_comp displacement
current subtracted out (`solve_k_params_output`: `i1 = ... - i_c_comp`).
Replaying into the same fixture, the simulated dV/dt equals the recorded dV/dt,
so that subtraction and the explicit C_comp in the netlist must cancel. No
transistor and no native IBIS are involved, so neither the engine nor the
reference model can confound it.

Waveforms are time-aligned before scoring, per the book, and reported as the
alignment shift plus the aligned curve-overlay FOM.

## The result

| table | C_comp | FOM % | RMSE mV | worst mV | shift ps |
|---|---|---:|---:|---:|---:|
| rising R=50 V=1.8 | **nominal** | **0.18** | 7.5 | 54 | +6.0 |
| rising R=50 V=1.8 | zero | 0.74 | 54.3 | 798 | −4.0 |
| rising R=50 V=0 | **nominal** | **0.41** | 10.9 | 74 | +6.0 |
| rising R=50 V=0 | zero | 0.60 | 38.0 | 711 | −4.0 |
| falling R=50 V=1.8 | **nominal** | **0.44** | 44.8 | 658 | +6.0 |
| falling R=50 V=1.8 | zero | 1.14 | 90.5 | 1595 | 0.0 |
| falling R=50 V=0 | **nominal** | **0.84** | 62.6 | 766 | +6.0 |
| falling R=50 V=0 | zero | 1.24 | 95.1 | 1422 | 0.0 |

**Nominal C_comp wins on all four tables**, by 1.5x to 4x in FOM, and the figure
shows why: with nominal C_comp pybis lies on the golden trace, while at C_comp=0
it carries a startup transient and a stair-stepped edge that visibly departs from
it.

So pybis's C_comp handling is correct, and removing or shrinking C_comp makes the
model worse against its own golden data.

## Why the earlier conclusion was wrong

The book's 11.8.2 diagnostic -- "if the buffer rise time changes as C_comp is
varied, then C_comp may be getting double counted" -- is **implementation
specific**. It describes a simulator that uses the V-T or ramp data *directly* as
the driver waveform and then *also* hangs C_comp on the output. There, C_comp's
effect is already in the V-T, so adding it again double-counts.

pybis does something different. It back-solves Ku/Kd from the V-T with the C_comp
displacement current explicitly removed, so **its Ku is C_comp-free by
construction** and the explicit C_comp in the netlist is the required other half
of that decomposition. Under that scheme the edge is *supposed* to move with
C_comp. The sensitivity we measured is expected behaviour, not the double-count
signature.

Applying the book's test to pybis was a category error on my part: the right test
for pybis's scheme is whether the two halves cancel where they must -- at the
characterization fixture -- and they do.

## What is actually left, and it is not C_comp

- **A consistent +6.0 ps alignment shift** on every table with nominal C_comp.
  That is the residual model lag, matching the ~5 ps measured against native IBIS
  in the engine/model decoupling. Real, small, and not C_comp.
- **Falling edges reproduce worse than rising** -- FOM 0.44 and 0.84 against 0.18
  and 0.41, with worst-case departures of 658-766 mV against 54-74 mV. This is
  the largest genuine defect the test exposes and is unexplained. It is a
  plausible relative of the Ku edge-transition ringing seen in the lag
  localization, and of the io_buf falling-edge lateness (defect B).

## Files

- `golden_waveform_test.png` -- all four tables, golden vs nominal vs zero
- `<table>_<tag>/` -- each replay run and its deck
- `scripts/golden_waveform_test.py`
