# Study notes: Leventhal & Green, *Semiconductor Modeling* (Springer, 2006)

769 pages, the canonical IBIS / behavioural-buffer reference. These notes cover
what bears on this project. Text via `pdftotext -layout`; the PDF has no embedded
outline and the OCR renders C_comp variously as Ccomp / C comp / Cjcomp.

## Chapters that matter to us

| ch | topic | why |
|---|---|---|
| 4.5 | IBIS models | keyword reference |
| **11.8** | **Experiment 2: Ccomp loading** | **C_comp doctrine -- see correction** |
| 11.11 | V-T data versus a ramp | why V-T beats ramp |
| 12.9-12.10 | Golden waveforms, common-errors checklist | validation practice |
| **13** | **Creating/validating IBIS from SPICE** | **this is what s2ibispy does** |
| **16.5** | **Verifying IBIS models** | **the I-V identity + FOM practice** |
| **17.14** | **IBIS golden waveforms** | **better validation than we have used** |

---

## 1. C_comp double-counting -- and why it does NOT apply to pybis

Section 11.8.1, as established doctrine:

> the effect of Ccomp on dV/dt or V-T is ALREADY INCLUDED in the dV/dt and V-T
> data. Wrong answers will be calculated if a simulator uses the Ccomp data as
> an additional load on the output and adjusts the initial ramp rate
> accordingly. This will be DOUBLE-COUNTING the effect of Ccomp. On the receiver
> side, the problem of double-counting Ccomp's effect does not arise.

Section 11.8.2, *Is Ccomp Being Double-Counted?*, gives the diagnostic:

> Varying C_comp is supposed to have NO EFFECT on driver rise and fall as
> opposed to adding a variable capacitance across the output. One way to test
> this is to reduce Ccomp to nearly zero and then raise it to a very large
> value, say 50 pF. ... If the buffer rise time changes as C_comp is varied,
> then C_comp may be getting double counted in the simulation.

**CORRECTION (see results/archive/2026-09/golden_waveform_test_2026-09-03).** I originally read
this as pybis failing the test. It does not apply to pybis: 11.8.2 describes a
simulator that uses V-T/ramp data *directly* and also hangs C_comp on the output.
pybis back-solves Ku with the C_comp current removed, so its Ku is C_comp-free
and the explicit C_comp is the required other half -- the edge is *supposed* to
move with C_comp. The golden-waveform test settles it: nominal C_comp beats
C_comp=0 on all four tables. **pybis handles C_comp correctly.** The sweep below
is kept as the measurement, not as a verdict:

| pybis C_comp | pad lag vs native |
|---:|---:|
| 0.468 pF (nominal) | 9.9 ps |
| 0.234 pF | 5.7 ps |
| 0.100 pF | 3.3 ps |
| 0 | 1.6 ps |

Rise time moves with C_comp, monotonically, to near zero at C_comp = 0. Under
pybis's decomposition that is expected, not a defect: Ku is C_comp-free, so the
pad edge genuinely depends on the C_comp in the circuit. Native IBIS does not
show the same sensitivity because it uses the V-T data directly, where C_comp is
already baked in -- two different, individually self-consistent schemes.

One consequence:

1. **C_comp scaling is wrong**, for a simpler reason than I first gave:
   nominal C_comp is already the best value against the model's own golden data,
   so scaling it away can only hurt. The rule below applies to V-T-replay
   simulators, not to pybis:

   The book's stronger rule (varying C_comp must have *no* effect on rise/fall,
   so the driver path must not take C_comp as an extra output load) applies to
   V-T-replay simulators, not to pybis's back-solved decomposition.

## 2. Golden waveforms -- a better test than any we have run

12.9.6 / 17.14:

> When provided in an IBIS model, the V-T waveform tables can be reproduced to
> verify the accuracy of the simulator... Since the load conditions that
> produced the tables should be provided, the simulator should be able to
> reproduce those waveforms using the specified loads.

And 16.5.1: *the test circuit load should match the load specified in the V-T
table being verified.*

**We have now run this** (`results/archive/2026-09/golden_waveform_test_2026-09-03`), and it is
what settled the C_comp question. Originally: Everything we did compared pybis to native and to
the transistor into an *arbitrary* load (50 ohm + 2 pF). The golden-waveform
test is self-contained: simulate the model into the exact fixture its
[Rising Waveform] table specifies (50 ohm to 0 V, 50 ohm to VCC) and check the
pad reproduces the table. No transistor, no native IBIS, no confounds -- and it
would settle the C_comp question outright.

Caveat the book adds: this verifies the *simulator*, not the *model*. Verifying
the model needs correlation to SPICE or measurement -- our transistor
comparison.

## 3. Figure of Merit -- comparison is time-aligned FIRST

> Waveform comparison usually has two phases. First, the waveform is SHIFTED,
> and then a visual comparison or Figure of Merit calculation is made... the
> shifted and unshifted waveforms will have a poor FOM unless the two waveforms
> are aligned in time.

IBIS Accuracy Handbook curve-overlay metric:

    FOM(%) = 100% x sum |X_i(golden) - X_i(DUT)| / (dx * N)

**This corrects how we have been reporting.** Our headline numbers were raw RMSE
without alignment, which turns a few ps of timing into tens of mV. We saw it
directly: pybis-vs-native RMSE is 17.3 mV as-is, 2.3 mV after a -9 ps shift --
87% was the shift. Standard practice removes the shift first.

Report two numbers, not one: the **time shift** (lag) and the **post-alignment
FOM** (genuine shape error). A single unaligned RMSE conflates them -- exactly
what made the gap look like a separate defect from the lag, when the 93 mV is
just 4.9 ps x an 18.5 mV/ps slew.

## 4. The I-V identity -- confirms our open-drain diagnosis

16.5.1, the DC check a validator applies:

    I_up    = [Pullup]   + [POWER Clamp] + [GND Clamp]
    I_dn    = [Pulldown] + [POWER Clamp] + [GND Clamp]
    I_recvr =              [POWER Clamp] + [GND Clamp]

This is what ibischk enforced when it rejected our ex2 open-drain: the spurious
51 mA in [GND Clamp] summed with [Pulldown], so the implied DC point disagreed
with the model's own waveform tables. Our upstream fix (hold the sole driver off
during clamp extraction) restores the identity -- 51 mA to 0.8 nA, model valid.

## 5. Smaller points worth keeping

- **Corner semantics** (13.3): min = low-current transistors, max = high-current,
  and *it is possible for an I/O to have its fastest edge rate at some other
  statistical corner* -- fastest edge is not automatically max.
- **Die temperature** (13.3): characterisation TEMP is typically ~50 C die, not
  27 C ambient. We run 27 C throughout -- self-consistent, but not the
  convention.
- **Column order** (11.10.1): IBIS files are typ-min-max left-to-right while data
  books are min-typ-max -- a documented translation-error source.
- **Line length** (12.10): lines over 80 ASCII chars are on the IBIS
  common-errors checklist. Worth checking what s2ibispy emits.
- **C_comp tracks slew rate** (11.8.1): *in a real device C_comp will be
  interdependent with slew rate... making the area of a driver larger increases
  current drive; this also increases Ccomp.* So editing C_comp in a file is a
  what-if, not a physical variant -- another caution against C_comp scaling.

## What to do next, per the book

1. ~~Run the golden-waveform test~~ **DONE** -- it showed nominal C_comp beats
   C_comp=0 on all four tables, so pybis's C_comp handling is correct.
2. **Report shift + post-alignment FOM** instead of raw RMSE.
3. **Re-frame the C_comp fix** as *the driver transient path must not take
   C_comp as an extra output load*, not *scale C_comp*.

## Not yet studied in depth

Ch 1-3 (workplace, modelling concepts, device physics), 5-10 (statistics,
selection guides, data sheets, model selection), 14-15 (sources, library
management), 17.15+ (BJT history, EMC), 18+ (accuracy vs practicality),
appendices.
