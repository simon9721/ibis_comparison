# The residual scaled by depth — the 12/12 law as a rule

*2026-09-09*

Every buffer showed the transistor's falling residual shrinking in proportion to
how far the output got, while ours is a full-transition constant. The io_buf
correction (`FRAC`, GUP held at the reversal) scaled it by the *gate*, and was
measured 2.4× too steep. This scales it by the *pad*: peak held, divided by the
model's own full-swing plateau, so the scale is 1 at full swing by construction.

Three builds per case — shipped, `frac_gup`, `frac_depth` — scored against the
transistor. `scripts/residual_depth_rule.py`, `<variant>/results.csv`.

---

## io_buf: as good as FRAC on the residual, and it inherits FRAC's one defect

| width | build | peak % | lag ps | Kd rms | Kd min (transistor) | bump mV (transistor 51.8) |
|---:|---|---:|---:|---:|---|---:|
| 2354 | shipped | 2.1 | 63 | 0.027 | −0.137 (−0.087) | 46.8 |
| 2354 | frac_gup | −0.2 | 49 | 0.006 | −0.098 | 24.1 |
| 2354 | frac_depth | 0.2 | 52 | 0.011 | −0.109 | 27.7 |
| 1505 | shipped | −3.5 | 65 | 0.034 | −0.111 (−0.056) | 46.9 |
| 1505 | frac_gup | −11.5 | 34 | 0.018 | −0.035 | 13.6 |
| 1505 | frac_depth | −13.1 | 28 | 0.022 | −0.024 | 11.3 |

Both scalings bring the residual onto the transistor's (Kd rms 0.03 → 0.01–0.02)
and cut the lag by a third. Neither is clearly better than the other on those.
And **both halve the +1.8 ns bump** (46 → 11–28 mV against the transistor's
51.8) — the peak-hold leaks over 5 ns and the residual table spans 10 ns, so the
scale is still applied where it does not belong. The steepness of the law was not
the leftover; the **time fence** is.

## inv_base8 and ex2_base: no effect, as predicted

Peak, lag, Kd rms unchanged to within 2 % on every case (inv 65.1 → 62.8 % at
50 %, ex2 70.9 → 68.2 %). The residual is a minor term on these buffers; their
defect is the entry level (`gate_ramp_prototype_2026-09-09`,
`gate_cascade_prototype`). This is the regime split, confirmed by trying the
io_buf remedy on them.

## What it settles

* A depth-based scale is a valid replacement for the gate-based one and needs no
  gate probe — but it is not an improvement on its own.
* The remaining io_buf residual defect is *where in time* the scale applies, not
  how big it is. The scale must stop before the pull-down turn-on at +1.8 ns.
* Nothing residual-side helps the eleven.

## Caveats

* The pad peak-hold uses the model's own plateau; on a different load the
  plateau changes and the constant with it.
* Short-high only; the mirrored rule for short-low is untested.

---

## Addendum: the time fence closes the io_buf residual defect

Added the same day. The scale is gated on the model's stopwatch since the last
input edge: `FRAC = (HNX < T) ? pad-peak/plateau : 1`, so it applies only during
the truncated fall and is 1 by the time the pull-down turns on.

| width | build | peak % | lag ps | Kd rms | bump mV (transistor 51.8) |
|---:|---|---:|---:|---:|---:|
| 2090 | frac_depth | −1.5 | 52 | 0.010 | 24.0 |
| 2090 | **fenced 0.8 / 1.2 ns** | −1.4 | 52 | 0.010 | **46.7** |
| 1666 | frac_depth | −7.9 | 38 | 0.018 | 15.7 |
| 1666 | fenced | −7.8 | 39 | 0.018 | **46.5** |
| 1505 | frac_depth | −13.1 | 28 | 0.022 | 11.3 |
| 1505 | fenced | −13.0 | 28 | 0.022 | **46.9** |

Residual, lag and peak unchanged; the bump comes back to within 5 mV of the
transistor. 0.8 and 1.2 ns give the same result, so any fence before ~1.3 ns
works. (A first pass of this test showed no effect at all — a stale-cache bug in
the runner, which keyed on the deck alone while only `driver.sub` had changed;
fixed in `gate_ramp_prototype.run_ours` and the affected directories rerun.)

What remains on io_buf's residual side is the deep-stress peak (−13 % at 1505 ps),
which every residual scaling costs and which is the same trade seen since
`residual_rescale_time_2026-09-04`.
