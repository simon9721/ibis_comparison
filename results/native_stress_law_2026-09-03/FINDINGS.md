# How native IBIS and pybis handle stressed pulses — measured, not assumed

Pure analysis of waveforms already on disk. Two families: the **width sweep**
(`stress_method_matrix_2026-08-20`) and the **depth-target** family
(`_baseline_edgecmd`), the latter being the one defect B was quoted on.

## The headline: native can miss a stressed event entirely

`io_buf short_low`, dip depth below the high plateau:

| width | transistor | native | pybis | native responds? |
|---|---:|---:|---:|---|
| 163 ps | 0.697 | **−0.037** | 1.116 | **no — flat** |
| 180 ps | 0.790 | **−0.009** | 1.166 | **no — flat** |
| 191 ps | 0.858 | **0.040** | 1.202 | **no — flat** |
| 209 ps | 0.954 | 0.111 | 1.246 | yes |
| 242 ps | 1.101 | 0.238 | 1.285 | yes |
| 281 ps | 1.247 | 0.396 | 1.319 | yes |
| 325 ps | 1.370 | 0.568 | 1.346 | yes |

Below about 200 ps **native IBIS does not react to the pulse at all.** The raw
trace makes it unambiguous — on `w163ps` the transistor dips from 1.507 to 0.820
and recovers, while native sits flat at 1.545 through the entire event. Above the
threshold it responds but under-dips heavily (0.568 against 1.370 at 325 ps).

pybis responds at every width and **over**-dips, converging on the transistor as
the pulse lengthens (1.116 vs 0.697 at 163 ps; 1.346 vs 1.370 at 325 ps).

## But it is device- and direction-dependent, not one behaviour

`short_low`, dip depth:

| device | transistor | native | pybis | who over/under |
|---|---:|---:|---:|---|
| io_buf (163 ps) | 0.697 | −0.04 | 1.12 | native **under**, pybis over |
| ex2 (688 ps) | 0.768 | 1.47 | 1.55 | **both over**, native less |
| inv_chain (110 ps) | 0.707 | 1.28 | 1.44 | **both over**, native less |

On io_buf native under-responds; on ex2 and inv_chain it **over**-responds — and
there it is *closer* to the transistor than pybis is.

`short_high` is more consistent: pybis is closer on 9/9 (io_buf), 5/5
(inv_chain) and 4/5 (ex2).

Across both families and all devices: **pybis closer on 41 of 53 cases.** Real,
but not the clean sweep the io_buf-only view suggested.

## Corrections to what I said earlier

1. ~~"Native systematically under-swings under stress."~~ True only of io_buf. On
   ex2 and inv_chain it over-swings, by up to +615 mV on inv_chain short_high.
2. ~~"Native's error follows a law: error proportional to how much of the
   transition never happened."~~ The per-device correlations are strong
   (|r| = 0.94–0.999) but the slope **reverses sign** between devices, so there is
   no cross-device law and no universal correction factor.
3. ~~"Native's coefficients are frozen across widths."~~ Native's Kd min/max were
   identical across six widths, but that is both cases hitting the same clamp
   limits (−0.458, 1.025). The waveforms do differ, by 42–173 mV.

Each of these came from generalising a single device. Testing out of sample is
what caught them.

## Measurement lesson

Two versions of my excursion measure were wrong before this one. `short_low` is
not a downward transition — the pad rises to a plateau, dips briefly, then
recovers — so `min()` over the trace returns the initial rest level, and a
naive "first crossing" measure picks up a pre-event artifact. The dip has to be
measured inside the event window relative to the local plateau. **Any stressed
metric needs the raw trace inspected before it is trusted**, which is how the
"native is flat" result surfaced at all.

## Also visible: pybis rings

On `io_buf short_low w163ps` pybis's recovery oscillates — 0.621, 0.962, 0.436,
0.896, 1.190, 1.347 — rather than recovering monotonically like the transistor.
Related to the Ku transition ringing seen in the lag localization. Not chased.

## Still not measured

- `short_high` for the depth-target family beyond the two io_buf cases.
- inv_chain depth cases show an identical transistor excursion (1.429) for both
  `depth28` and `depth91`, so that parameterisation does not appear to have
  produced different stress levels for that device. Worth checking before those
  cases are used for anything.
- Why native's threshold sits near 200 ps on io_buf, and whether it scales with
  the buffer's own edge rate.

## Files

- `scripts/stress_amplitude_survey.py` — both families, direction-aware
- `scripts/native_stress_law.py` — the cross-device law test that failed
