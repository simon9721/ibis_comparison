# ex2 with the measured C_comp: the model gets worse

*2026-09-08*

`gate_physics_2026-09-08` measured ex2's pad capacitance at 1.50–1.75 pF from the
Ku-vs-gate loop, against a declared 5.0 pF, with the minimum width-independent
across five widths. This applies the correction the way a user would — edit the
`.ibs`, rebuild ours, rerun native — and scores both against the transistor at two
stressed widths and the 10 ns control. The transistor's Ku is re-solved with the
same C_comp each time so the coefficient comparison is like for like.

---

## Result

| case | C_comp | ours: peak err | lag | RMSE | native: peak err | lag | RMSE | Ku ratio ours / native |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 858 ps | 5.0 (declared) | +244 mV | +236 ps | 336 mV | +263 | +263 | 374 | 1.13 / 1.15 |
| 858 ps | **1.7 (measured)** | **+289** | **+268** | **382** | +342 | +300 | 435 | 1.39 / 1.53 |
| 975 ps | 5.0 | +20 | +121 | 201 | +18 | +141 | 233 | 1.08 / 1.09 |
| 975 ps | 1.7 | +52 | +149 | 243 | +75 | +172 | 283 | 1.09 / 1.16 |
| control | 5.0 | −4 | — | 1.2 | −3 | — | 0.3 | |
| control | 1.7 | −4 | — | 2.1 | −3 | — | 0.3 | |

**Every stressed metric gets worse with the correct capacitance, for both models.
The control does not move.**

## Why, and why this is not a contradiction

The loop measurement is a statement about the **device**: the transistor's Ku is a
static function of its gate only when the displacement current is removed with
~1.7 pF, and that number does not depend on pulse width. Nothing here disputes it.

The pad result is a statement about the **model**. Its dominant stressed defect is
that it enters the reversal with the pull-up fully on and turns it off late
(`cross_device_stress_2026-09-08`: +71 % too tall at 50 % depth). Excess pad
capacitance slows the simulated pad's rise and lowers that peak. So the declared
5 pF was quietly **compensating** a third of the gate-dynamics error. Remove the
compensation and the underlying defect shows in full.

This is the same structure the io_buf work found in
`residual_rescale_time_2026-09-04`: an oversized residual was propping up a peak
deficit, and removing it exposed the deficit. Two independently wrong parameters
whose errors partially cancel look better together than either does alone.

## What this means

* The `.ibs` C_comp for ex2 should still be corrected — but **not on its own**.
  Until the gate turn-off timing is fixed, 5 pF scores better than the truth.
* Any "improvement" measured after a single-parameter change on this model has to
  be read against the possibility that a compensating error just moved. The
  transistor-derived Ku ratio going from 1.13 to 1.39 is the honest number: with
  the reference corrected, our coefficient is 39 % high over the event.
* The control being flat at both values confirms C_comp is a stressed-case lever
  only — at full swing the pad is settled when it matters.

## Caveats

* Two widths, one buffer. The 975 ps case moves less because it is less stressed
  (91 % depth), consistent with the compensation scaling with the defect.
* `ours` is the shipped `InputDrivenTwoStateGateDelayCommandFull` build with no
  corrections applied.
* The IBIS edit changes only the `C_comp` line; the V-T tables are the recorded
  waveforms and are unaffected, but every coefficient derived from them changes.
