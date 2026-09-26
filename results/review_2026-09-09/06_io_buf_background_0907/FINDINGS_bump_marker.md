# Reading the corrected model's shape out to +3 ns

*2026-09-07*

Extending the comparison window past the fall exposes a second event that the
1 ns view cut off: after the pad collapses to zero at about +1.2 ns it comes back
up to a **secondary bump of ~52 mV at +1.8 ns**. Kd runs 0 -> 1 straight through
it, so the bump is **the pull-down being commanded on**.

It is the best timing marker in the whole record — well separated from the
reversal, large enough to measure, and present in all four traces. Three findings
came out of it, and one of them is bigger than the corrections themselves.

Figures: `../meeting_deck_2026-09-04/figures/correction_bump.png`,
`correction_shapes.png`, `correction_tail.png`.

---

## 1. The accumulating shift is a **command-timing** error, not a coefficient error

Bump peak time, measured from each case's own reversal:

| width | transistor | native | ours, before | ours, corrected |
|---|---:|---:|---:|---:|
| 2354 | 1.905 | 1.905 | 2.014 | 1.994 |
| 1989 | 1.850 | 1.884 | 2.010 | 1.998 |
| 1792 | 1.803 | 1.878 | 2.015 | 1.995 |
| 1505 | **1.700** | 1.848 | **2.014** | **1.994** |
| **total movement** | **205 ps** | **68 ps** | **7 ps** | **6 ps** |

Our Kd trajectory through the bump is identical to three decimal places at every
width (0.0987 / 0.0996 / 0.0998 at +1.90 ns for 2354 / 1792 / 1505). That is not
a tuning error — `PDCMDLVL` is an OR of two **fixed delays off the input edge**,
so relative to the reversal it *cannot* move. The model is structurally incapable
of this behaviour.

What the transistor's bump time actually tracks:

| | vs input width W | vs pad peak reached |
|---|---:|---:|
| transistor | R2 = 0.931 | **R2 = 0.979** |
| native | R2 = 0.917 | R2 = 0.939 |
| ours, before | R2 = 0.059 | R2 = 0.044 |
| ours, corrected | R2 = 0.140 | R2 = 0.120 |

**The next event fires when the state left behind says it should, and the pad
voltage is a good proxy for that state.** That is precisely why native — whose
coefficients are solved at runtime indexed by pad voltage — recovers a third of
the effect, and we recover none of it. Same conclusion as
`v_indexed_prototype_2026-09-04`, now visible in event *timing* rather than
coefficient amplitude.

Neither derived correction touches this. The corrected bump timing improves by a
flat ~20 ps (that is the `pu_off` change) and the width-dependence is untouched.

**This is the accumulating half of the timing shift, isolated at one feature.**

## 2. The FRAC law is directionally right and about 2.4x too steep

Measured over the window where the Kd residual dominates (+90 to +400 ps).
`needed` = transistor Kd / shipped Kd; `applied` = what the peak-hold delivers.

| width | peak V | needed | applied | applied − needed |
|---|---:|---:|---:|---:|
| 2354 | 1.220 | 0.681 | 0.707 | +0.027 |
| 2226 | 1.154 | 0.640 | 0.655 | +0.016 |
| 2090 | 1.074 | 0.640 | 0.626 | −0.014 |
| 1989 | 1.009 | 0.615 | 0.585 | −0.030 |
| 1853 | 0.914 | 0.600 | 0.507 | −0.094 |
| 1792 | 0.868 | 0.606 | 0.475 | −0.131 |
| 1666 | 0.755 | 0.590 | 0.384 | −0.206 |
| 1634 | 0.723 | 0.588 | 0.365 | −0.222 |
| 1505 | 0.569 | 0.549 | 0.279 | **−0.270** |

The factor the data demands barely moves — **0.681 to 0.549, a 19% change** while
the pad peak halves. GUP at the reversal moves **0.707 to 0.279, a 61% change**.
So the law has the right sign and roughly **2.4x too much slope**, crossing zero
error at about 2100 ps: we under-correct above it and over-correct below.

The correction was accepted on evidence from 1792 ps, where the two happened to
sit within 0.13 of each other.

## 3. The bump amplitude loss is self-inflicted, and it localises the over-reach

Bump amplitude, transistor against the rest:

| width | transistor | native | ours, before | ours, corrected |
|---|---:|---:|---:|---:|
| 2354 | 51.7 mV | 47.6 | 46.8 | 23.8 |
| 1792 | 51.6 | 47.8 | 46.8 | 17.7 |
| 1505 | 51.7 | 47.5 | 46.9 | **13.2** |

**The transistor's bump is 51.6 mV at every width.** So is native's (47.6) and so
is ours-before (46). It does not scale with truncation *at all*. Only the
corrected model scales it — and that is proof the scaling does not belong there.

Two things combine to cause it:

* the residual table spans ~10 ns on `HNX`, so `KURES_F` is still ~0.036 at
  +1.9 ns and is essentially the entire Ku at the bump;
* the peak-hold leaks with a 5 ns time constant, so FRAC is still 0.29–0.51 there
  (measured as the corrected/shipped Ku ratio at +1.90 ns).

The truncation argument only justifies scaling the residual **during the
truncated fall**, a few hundred ps. Past that the residual is doing an unrelated
job and FRAC has no business multiplying it.

## 4. 1505 ps is not an edge case

Fitting the other eight widths and predicting 1505:

| quantity | predicted | actual | miss |
|---|---:|---:|---:|
| bump timing error, before | 270 ps | 314 | 44 |
| bump timing error, corrected | 250 ps | 294 | 45 |
| bump amplitude error, corrected | −37.4 mV | −38.5 | −1.1 |

The amplitude error is exactly on trend. The timing error is mildly super-linear
— 45 ps out of 294, about 15% — which is expected, since the underlying quantity
it tracks (the pad peak) falls away faster than the width does at the short end.

Every column in every table above is monotone in width. **1505 is the end of a
smooth trend, not a break.** It looks worse because it is where a systematic law
error that is present at every width grows large enough to see.

## 5. Open hypothesis: the falling residual may be too large everywhere

Two independent parameterisations of the needed factor agree:

```
needed ~ 0.434 + 0.203 * (pad peak)      residual <= 0.023 over nine widths
needed ~ 0.463 + 0.308 * FRAC
```

The full-swing transistor pad peak is **1.588 V**, which puts both extrapolations
at **~0.76, not 1.0**. If that holds, the shipped falling residual is ~30% too
large on a *complete* transition too, and FRAC = 1 at full swing is merely the
safe choice rather than the correct one. Consistent with the unstressed model
still carrying 29.9 mV RMSE after both corrections.

**Not proven.** It is a 40% extrapolation, and the two x-variables are strongly
correlated so the agreement is weaker evidence than it looks. The decisive test
is cheap: run the two-fixture solve on a full-swing transistor case and measure
the needed factor directly. No such solved coefficient set exists yet — the stress
matrix only carries `silicon_ku` / `silicon_kd` for stressed cases.

## What this changes

* The residual scaling should be **flattened** (slope roughly /2.4) and **fenced
  in time** so it cannot reach the next event. Both are measurable, not tuned.
* The accumulating shift needs a different kind of fix entirely: the command
  chain must take its timing from state, not from a fixed delay off the input
  edge. Nothing in the current correction set addresses it.
* The pad peak deficit is real but ours-corrected is **better than native** at
  every width (−70 mV against native's −99 at 1792; −92 against −116 at 1505).
  The shipped model beat both, by cancelling it against a 2x Kd error.

## Caveats

* io_buf short-high only.
* The transistor's own coefficients are unreliable within tens of ps of the
  reversal (the two-fixture solve going ill-conditioned), so the `needed` ratios
  start at +90 ps.
* `needed` is a ratio of two models' Kd and so absorbs any other Kd error present,
  including the residual's over-long tail. It is a good measure of the *slope* of
  the law and a weaker one of its absolute level — which is exactly why section 5
  is flagged as unproven.
