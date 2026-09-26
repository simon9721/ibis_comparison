# The transistor's own gate: what Ku really is, and a C_comp diagnostic that falls out

*2026-09-08*

The stress-matrix transistor runs recorded an internal predriver node on every
base buffer — io_buf `n2` (gates the five output PMOS, `mx24–28`) and `n3` (the
NMOS), inv_chain `vout7` (the last predriver stage), ex2 `n4` (the shared output
gate). That is the real device's "gate state", measured, so two questions become
answerable without a model in the loop:

1. Is the transistor's Ku a **static function of its own gate voltage**?
2. How far does the real gate actually get under stress?

Ku/Kd from the two-fixture solve at 5 ps; io_buf runs are on `hspice.mod`.

---

## 1. Ku is nearly a static map of the gate — on two of three buffers

"Hysteresis" = mean |Ku_rising − Ku_falling| at matched gate voltage over the
event (0 = single-valued map).

| buffer | gate node | hysteresis at declared C_comp | reading |
|---|---|---:|---|
| io_buf | n2 | 0.07–0.11 | nearly static |
| inv_chain | vout7 | 0.09–0.10 | nearly static |
| ex2 | n4 | **0.47–0.75** | **not** a function of the gate |

On io_buf and inv_chain the gate-map architecture (`Ku = f(GUP)`) is physically
right to within ~0.1. On ex2 it is not — until section 3.

## 2. How far the real gate gets

| buffer | gate excursion / supply, 50%→90% depth | Ku at pad peak |
|---|---|---|
| io_buf n2 | **0.42 → 0.63** — truncated by the pulse | 0.17 → 0.45 |
| inv_chain vout7 | 0.91 → 1.03 — **always completes**, but arrives late | 0.25 → 0.64 |
| ex2 n4 | 0.67 → 0.72 — ~70% regardless of W | 0.29 → 0.68 |

Three different physical situations behind the same "stressed" label:

* **io_buf**: the predriver itself is truncated. Ku tracks n2. This is the buffer
  where a partial gate state is the right picture — and where our GUP (τ_rise
  1.13 ns) is *also* partial, which is why io_buf's entry excess is modest.
* **inv_chain**: the internal node swings fully every time; what is truncated is
  *time*. At the transistor's pad peak its Ku is already falling (0.25–0.64)
  because vout7 is on its way back. Our Ku is still ~1.0 there. The "entry
  excess" measured in `cross_device_stress_2026-09-08` is, on inv, our pull-up
  being late to turn off, not entering at the wrong level.
* **ex2**: n4 reaches ~70% whatever the width, so the entry is set by the
  predriver's own speed, not the pulse. Ours enters at 0.96–1.14.

## 3. ex2's hysteresis is the declared C_comp, and the loop measures it

Theory: the solve subtracts `C_comp·dV/dt` before dividing by `I_pu(V)`. If C_comp
is wrong, the leftover displacement current is assigned to Ku — and `dV/dt`
flips sign between rise and fall, so the error opens a **loop** in Ku-vs-gate.
The C_comp that closes the loop is the one the device has.

Re-solving with C_comp swept (`scripts/ku_gate_hysteresis_ccomp.py`):

| buffer | declared | loop at declared | **loop-minimising C_comp**, per width | spread |
|---|---:|---:|---|---|
| ex2 | 5.00 pF | 0.47–0.75 | **1.50, 1.75, 1.75, 1.75, 1.75** (mean 1.70) | tight |
| inv_chain | 0.468 | 0.09–0.10 | 0.50, 0.60, 0.60, 0.60, 0.60 (mean 0.58) | tight |
| io_buf | 1.20 | 0.07–0.11 | 0.30–1.10 (mean 0.62) | shallow |

**ex2's declared C_comp is ~3× too large.** At 1.7 pF the loop is 0.09 and Ku
becomes a near-static function of n4 like the other two; and the "Ku overshoot
above 1" on ex2 (1.14–1.26 at the declared value) falls to 0.82–0.97 — most of it
was displacement current mis-booked as pull-up. A physical capacitance must not
depend on pulse width, and the minimum does not (1.50–1.75 across five widths).

inv_chain's declared value is close (0.47 vs 0.58). io_buf's curves are too
shallow to decide — its slow gate keeps `dV/dt` small against device current — but
the direction agrees with the direct C-V extraction (`cv_capacitance_2026-09-04`:
0.25 pF high-Z, 0.68 pF driven mean, declared 1.20).

Both IBIS models simulate with the declared value, and every Ku/Kd table in the
ex2 `.ibs` was solved with it. So ex2 carries a 3 pF error in its output stage
*and* inflated coefficients — a model defect independent of the coefficient
story, on the buffer family where our stressed peak is worst.

**io_buf caveat (added 2026-09-09 after re-viewing the figure).** The bottom-left
panel's excursion at 0.75-1.0 V is the near-reversal differentiation-noise zone
(`silicon_kukd_conditioning_2026-09-07`). That noise *is* the C_comp dV/dt term,
so a smaller C_comp in the solve shrinks it -- which biases io_buf's shallow
minimum toward small values. io_buf's loop result is therefore contaminated and
stays "undecided" for a reason, not merely for lack of contrast; inv_chain's and
ex2's minima are sharp and width-independent and are not affected in the same way
(their event windows are dominated by the converged region).

## What this changes

* The gate-map architecture is physically justified on io_buf and inv_chain
  (hysteresis ≤ 0.1) and on ex2 once C_comp is right. The place our model is wrong
  is the **gate dynamics** (when it turns, how far it gets), not the map.
* "Stressed" hides three mechanisms: a truncated predriver (io_buf), a late but
  complete one (inv_chain), a speed-limited one (ex2). Any one correction that
  treats them alike will fit one and miss two.
* Ku-vs-gate hysteresis is a usable C_comp check wherever an internal gate node
  is available. It needs no C-V run.
* **But do not apply the corrected C_comp on its own.** Tested in
  `../ex2_ccomp_correction_2026-09-08/`: editing the ex2 `.ibs` to 1.7 pF makes
  every stressed metric worse for both models (ours at 858 ps: +244 → +289 mV,
  lag +236 → +268 ps) while the control is unchanged. The declared 5 pF was
  compensating about a third of the gate-dynamics error by slowing the simulated
  pad. Fix the gate turn-off first; then the true capacitance helps.

## Caveats

* Requires an internal node; the variant campaigns did not probe one, so this is
  the three base buffers only.
* The hysteresis metric is over the event only and uses the 5 ps solve; io_buf's
  value at the two shortest widths sits partly in the differentiation-noise zone.
* io_buf `n3` was also probed; it barely moves except at the shortest pulses and
  is not the pull-up gate.
