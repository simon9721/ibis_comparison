# Looking at the stressed waveform shapes — which we had never done

Every stress-case number in this project has been scalar: a 50% crossing and an
RMSE. Nobody had plotted what the transistor and native IBIS actually *do* under
stress. Doing it surfaces two things the scalars hid.

Source: `results/stress_method_matrix_2026-08-20/delay_cmd/waveforms/`,
io_buf `short_high`, nine pulse widths, columns `silicon_pad` (HSPICE
transistor), `hspice_pad` (native IBIS), `pybis_pad` (our delay_cmd build).

## CORRECTION to section 1 (2026-09-03, same day)

I first wrote that these pulses "never reach half swing", comparing their peaks
against the **3.3 V supply**. That is the wrong reference. **io_buf's pad only
swings to ~1.6 V into the 50 ohm + 2 pF load** -- the 50 ohm divider halves the
supply. Measured from the same bench, the full-swing transistor run goes
-0.013 to 1.588 V, so full swing is 1.601 V and the half-swing level is 0.788 V,
not 1.65 V.

Against the correct reference:

| width | transistor peak | % of the 1.601 V swing | crosses half? |
|---|---:|---:|---:|
| 1505 ps | 0.569 V | 36% | no |
| 1634 ps | 0.722 V | 45% | no |
| 1666 ps | 0.755 V | 47% | no |
| 1792 ps | 0.868 V | 54% | **yes** |
| 1853 ps | 0.914 V | 57% | **yes** |
| 1989 ps | 1.009 V | 63% | **yes** |
| 2090 ps | 1.074 V | 67% | **yes** |
| 2226 ps | 1.154 V | 72% | **yes** |
| 2354 ps | 1.220 V | 76% | **yes** |

**Six of nine do cross half swing.** So the claim that a 50% crossing does not
exist on this family was wrong, and the stronger conclusion drawn from it -- that
the timing measurement is meaningless here -- does not hold. These are still
partial excursions (36-76% of swing rather than 100%), but a half-swing crossing
is well defined for most of them.

What survives unchanged is section 2 below: the peak-amplitude comparison is a
direct trace-to-trace measurement and does not depend on the reference level.

## 2. Native IBIS systematically under-swings; pybis does not

Peak amplitude against the transistor, all nine widths:

| width | transistor | native IBIS | pybis | native error | pybis error |
|---|---:|---:|---:|---:|---:|
| 1505 ps | 0.569 | 0.453 | 0.551 | **−116 mV** | −18 mV |
| 1634 ps | 0.722 | 0.598 | 0.712 | **−124 mV** | −11 mV |
| 1666 ps | 0.755 | 0.634 | 0.746 | **−121 mV** | −9 mV |
| 1792 ps | 0.868 | 0.769 | 0.864 | **−98 mV** | −3 mV |
| 1853 ps | 0.914 | 0.821 | 0.920 | **−92 mV** | +6 mV |
| 1989 ps | 1.009 | 0.923 | 1.023 | **−87 mV** | +14 mV |
| 2090 ps | 1.074 | 0.991 | 1.094 | **−82 mV** | +20 mV |
| 2226 ps | 1.154 | 1.095 | 1.178 | **−60 mV** | +24 mV |
| 2354 ps | 1.220 | 1.160 | 1.249 | **−60 mV** | +29 mV |

**Native IBIS is low on every single width, by 60–124 mV. pybis is within
3–29 mV, and is closer on 9 of 9.**

This inverts the framing the project has been carrying. On clean full-swing edges
native is the better model and we chase it. On these partial excursions **our
model reproduces the transistor's amplitude better than native IBIS does** — and
native's error is systematic, always in the same direction, growing as the pulse
gets shorter.

## 3. What it implies for the timing defect

Defect B is stated as "we are 69–99 ps late, native is 5–26 ps early", both
against the transistor. If native's waveform peaks 60–124 mV low, then it reaches
any fixed threshold at a different time than a correctly-scaled waveform would —
so **part of "native is early" may be an amplitude deficit read as a timing
lead** rather than native genuinely anticipating the transistor. This is a
plausible contribution, not a measured one -- it has not been quantified on
defect B's own cases.

That does not make the timing shift disappear. It does mean the headline number
mixes two effects, and the honest statement is either

- compare timing at a level defined *relative to each trace's own peak*, or
- report amplitude and timing separately, as the book's FOM practice requires
  (align first, then score).

## Scope and a caveat

These nine cases are the `short_high` **pulse-width** sweep, whose `cases.csv`
carries `depth_target = nan`. Defect B was quoted on five **depth targets**
(90/80/70/60/50%). Those may be a different family with different amplitudes, so
the peak-error numbers here should not be transplanted onto defect B's five cases
without re-measuring them there. What *does* carry over is the method point: the
shapes need looking at, and a fixed-level crossing on a partial excursion is not
a safe measurement.

## Files

- `stress_shapes.png` — four widths, all three builds, with the half-swing line
  marked to show it is never reached
- `stress_peak_error.png` — peak error against the transistor across all nine
- `scripts/plot_stress_shapes.py`
