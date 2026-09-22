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
| rising R=50 V=1.8 | zero | 0.74 | 54.3 | 798 | -4.0 |
| rising R=50 V=0 | **nominal** | **0.41** | 10.9 | 74 | +6.0 |
| rising R=50 V=0 | zero | 0.60 | 38.0 | 711 | -4.0 |
| falling R=50 V=1.8 | **nominal** | **0.09** | 4.4 | 49 | +6.0 |
| falling R=50 V=1.8 | zero | 0.64 | 39.8 | 368 | -6.0 |
| falling R=50 V=0 | **nominal** | **0.18** | 9.3 | 66 | +4.0 |
| falling R=50 V=0 | zero | 0.74 | 46.8 | 459 | -6.0 |

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

## Correction: there is no falling-edge defect

An earlier run of this test reported falling edges reproducing far worse than
rising (FOM 0.44 / 0.84, worst 658-766 mV). **That was an artifact of the test,
not of pybis.**

The InputDriven model initialises with the pulldown on and establishes state only
on the first detected *edge*, so a level the input is merely *held* at is not a
settled state. The falling replay held the input high from t=0 and stepped it low
-- giving the model no rising edge -- so it entered the transition from the wrong
initial level and spent the first tens of picoseconds climbing into the golden
trace. Driving a real rising edge first, letting it settle, then falling gives:

  falling V=1.8   FOM 0.44 -> **0.09**,  worst 658 -> **49 mV**
  falling V=0     FOM 0.84 -> **0.18**,  worst 766 -> **66 mV**

Falling now reproduces *better* than rising. This is the second time this same
initialisation property has produced a false finding (the first was the open-drain
bench), so it is worth stating as a rule: **any bench for this model must begin
with a real edge, never a held level.**

## What is actually left

- **A consistent +4 to +6 ps alignment shift** on every table. That is the whole
  of the residual, and it matches the ~5 ps model lag measured against native IBIS
  in the engine/model decoupling. Real, small, and not C_comp.
- Aligned shape error is now 0.09-0.41% FOM (49-74 mV worst) across all four
  tables -- pybis reproduces its own golden data closely once timing is removed.

Appendix E of the book explains where the residual shift most likely comes from.
The canonical IBIS simulator architecture is: *"an IBIS output driver sends a
voltage wave, provided by the model file's [Ramp] or V-T data lookup tables, down
a network... The reflections at each IBIS Input/Output are calculated with the use
of the model file's I-V data lookup tables."* That is, V-T drives the wave and I-V
handles reflections. pybis instead reconstructs the wave from I-V scaled by Ku(t).
Both are defensible, but they are different architectures, and that difference --
not C_comp -- is the remaining candidate for the few-ps lag.

## Files

- `golden_waveform_test.png` -- all four tables, golden vs nominal vs zero
- `<table>_<tag>/` -- each replay run and its deck
- `scripts/golden_waveform_test.py`
