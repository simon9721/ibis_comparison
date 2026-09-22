# Golden-waveform test across all three buffers — and what it says about defect B

The book's prescribed simulator verification (Leventhal & Green 12.9.6, 17.14,
16.5.1), now run on every buffer in the study: replay each model's own
`[Rising Waveform]` / `[Falling Waveform]` into the fixture that produced it,
time-aligned first, scored with the curve-overlay FOM.

No transistor and no native IBIS are involved, so neither the SPICE engine nor a
reference implementation can confound the answer.

## Results — pybis reproduces all three, closely

Nominal C_comp, all four tables per buffer:

| buffer | C_comp | FOM % (range) | worst mV | alignment shift |
|---|---:|---:|---:|---:|
| inv_chain `base8` | 0.468 pF | 0.09 – 0.41 | 49 – 74 | +4 to +6 ps |
| `io_buf` | 1.2 pF | **0.05 – 0.17** | 7 – 280 | +6 to +8 ps |
| `ex2` | 5.0 pF | **0.03 – 0.28** | 8 – 13 | +4 ps |

Per-table detail for io_buf and ex2:

| table | C_comp | FOM % | RMSE mV | worst mV | shift ps |
|---|---|---:|---:|---:|---:|
| io_buf rising V=0 | **nominal** | **0.05** | 1.1 | 6.9 | +8 |
| io_buf rising V=0 | zero | 0.19 | 5.1 | 46 | −44 |
| io_buf rising V=3.3 | **nominal** | **0.08** | 1.8 | 6.7 | +6 |
| io_buf rising V=3.3 | zero | 0.24 | 11.4 | 80 | −42 |
| io_buf falling V=0 | **nominal** | **0.17** | 17.8 | 280 | +8 |
| io_buf falling V=0 | zero | 0.55 | 36.5 | 335 | −52 |
| io_buf falling V=3.3 | **nominal** | **0.13** | 3.3 | 12.8 | +6 |
| io_buf falling V=3.3 | zero | 0.27 | 10.9 | 69 | −44 |
| ex2 rising V=0 | **nominal** | **0.11** | 2.4 | 8.2 | +4 |
| ex2 rising V=0 | zero | 1.00 | 52.5 | 391 | −156 |
| ex2 rising V=3.3 | **nominal** | **0.09** | 2.2 | 10.3 | +4 |
| ex2 rising V=3.3 | zero | 1.16 | 98.0 | 741 | −140 |
| ex2 falling V=0 | **nominal** | **0.03** | 1.4 | 9.8 | +4 |
| ex2 falling V=0 | zero | 1.06 | 79.9 | 633 | −124 |
| ex2 falling V=3.3 | **nominal** | **0.28** | 6.8 | 12.8 | +4 |
| ex2 falling V=3.3 | zero | 0.82 | 37.0 | 219 | −178 |

## 1. What this does and does not say about defect B

**io_buf reproduces its own V-T tables to 0.05-0.17% FOM with an alignment shift
of only +6 to +8 ps.**

**Scope correction.** An earlier version of this note claimed that therefore
"defect B is not in the model". That was too strong, because this test does not
exercise the build or the conditions defect B lives in:

| | defect B | this test |
|---|---|---|
| build | **gate-state** (GUP / GUPCMD command layer) | **InputDriven** (plain) |
| stimulus | **stress cases**, truncated pulses at 90/80/70/60/50% width | **full swing** |
| reference | HSPICE transistor | the model's own V-T tables |

Defect B is the falling 50% crossing running 69-99 ps late against the transistor
on the five stress targets, where native IBIS is 5-26 ps early.

What the test legitimately establishes is narrower but still useful: **the
underlying reconstruction is sound.** The I-V + Ku(t) + C_comp machinery that
both builds share replays a full-swing edge to within 8 ps on io_buf's own data.
So a 70-100 ps error is not coming from that layer.

That leaves defect B in one of:

- the **gate-state command layer** (GUP/GUPCMD), which the earlier work already
  showed is where the *offset* defect is born -- untested here;
- the **stress condition itself** (a truncated pulse never reaches a settled
  state, and the golden tables only describe full swing);
- the **study bench or comparison method** -- notably, the study's timing numbers
  were taken without the time alignment the book prescribes.

A golden-waveform test cannot settle it, because IBIS provides golden data only
for full swing. Defect B needs its own experiment on the gate-state build under
stress.

## 2. C_comp is handled correctly, on all twelve tables

Nominal C_comp beats C_comp = 0 on **every table of every buffer**, and the
margin grows with the size of the die capacitance:

- base8 (0.468 pF): zero needs a −4 to −6 ps shift and 4× worse FOM.
- io_buf (1.2 pF): zero needs a −42 to −52 ps shift.
- ex2 (5.0 pF): zero needs a **−124 to −178 ps** shift and 4–12× worse FOM.

That scaling is the proof. If C_comp were being double-counted, removing it would
*help*, and it would help most where C_comp is largest. The opposite happens: on
ex2, whose C_comp is 5 pF, removing it is catastrophic. pybis's explicit C_comp is
doing real and correct work.

## 3. The residual is one small, universal shift

Every buffer, every table, needs a small **positive** alignment shift: +4 ps (ex2),
+4 to +6 ps (base8), +6 to +8 ps (io_buf). Consistent in sign and magnitude across
three different silicons, three different C_comp values and both edges.

That matches the ~5 ps model lag measured against native IBIS in the engine/model
decoupling, and it is what Appendix E predicts: canonical IBIS *"sends a voltage
wave, provided by the model file's [Ramp] or V-T data lookup tables"* and uses the
I-V tables for reflections, whereas pybis reconstructs the wave from I-V scaled by
Ku(t). Two different architectures; the few-ps offset is the price of the second.

## Loose end

io_buf falling V=0 shows a worst-case departure of 280 mV despite a good 0.17%
FOM — a localized spike rather than a broad error, unlike its other three tables
(7–13 mV). Not chased yet.

## Files

- `golden_waveform_test.png` in this directory and in
  `../golden_waveform_ex2_2026-09-03/`
- `scripts/golden_waveform_test.py` (parameterized: `--ibis --model --component
  --supply --ccomp`; enable polarity is auto-detected from the generated
  subcircuit, since driving EN to the wrong rail silently disables the buffer)
