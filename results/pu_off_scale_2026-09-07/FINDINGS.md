# What native actually does, and why `pu_off` cannot be derived

*2026-09-07*

Five experiments, run to put a measurement behind every claim in the structural
account. Two of them retract earlier conclusions — one from
`residual_rescale_time_2026-09-04`, one from my own re-derivation of it.

---

## 1. CONFIRMED — native's stored trajectory *is* the offline two-fixture solve

`scripts/native_st_vs_solved_k.py`, io_buf at full swing, native's `St_pu` /
`St_pd` exposed with `xv_pu` / `xv_pd` against `solve_k_params_output`:

| edge | quantity | max abs diff | best lag | **residual after aligning** |
|---|---|---:|---:|---:|
| Rising | Ku | 0.0802 | +14 ps | **0.004** |
| Rising | Kd | 0.0618 | +14 ps | **0.002** |
| Falling | Ku | 0.4105 | +52 ps | **0.003** |
| Falling | Kd | 0.4435 | +52 ps | **0.003** |

Same curve to 0.4% of span, offset by a small fixed delay. The large `max abs
diff` on the falling edge is entirely that offset acting on a very steep curve.

**So there is no mystery in the trajectory.** Native holds exactly what the
offline solve produces, indexed by time since the edge — the same kind of object
we hold.

## 2. CONFIRMED — the documented pad-voltage rule is dormant here

The manual's rule (`primesim_continuum_elements.pdf`) selects waveform tables
*by initial voltage*, bracketing `V(out)` before the transition. `io_buf_fast_50ps.ibs`
carries **exactly two rising and two falling tables**, differing by fixture
(`V_fixture` 0 and 3.3), not by initial pad voltage. One pair per edge, nothing
to select between.

**Retracted:** "native re-solves the coefficient at runtime from the pad voltage."
It does not. The two fixtures make the solve *determined*; the pad voltage plays
no part in it, and the one place it is documented to enter cannot engage on this
file.

## 3. Both models enter the fall at the same place

Ku at the reversal:

| width | native | ours |
|---|---:|---:|
| 2354 | 0.7124 | 0.7043 |
| 1792 | 0.4842 | 0.4756 |
| 1505 | 0.3135 | 0.2920 |

Within 0.02 at every width. **The entry value is not where we differ.**

Neither model replays its stored curve from the start (which would jump to 1.0).
Fitting "enter the stored curve where you already sit" over +0..+400 ps:

| | rms vs that ideal |
|---|---:|
| native | 0.093 |
| **transistor** | **0.158** |
| ours, corrected | 0.167 |
| ours, before | 0.206 |

Note the transistor is *further* from that ideal than native is. **The ideal
describes native's behaviour, not physical truth** — chasing it exactly would not
give us the transistor. Being more native-like is not the same as being right.

## 4. NEW — Kd is solved; Ku is not

Against the **transistor**, over +90..+400 ps from the reversal (nearer than that
the solved coefficients are dominated by the `C_comp dV/dt` finite difference and
do not converge with the grid — see section 6 and the verification pass), mean
over nine widths:

| | Ku rms | Ku ratio to transistor | Kd rms |
|---|---:|---:|---:|
| native | 0.0167 | 1.07 | 0.0107 |
| ours, shipped | 0.1358 | 1.93 | 0.0411 |
| ours, corrected (x0.70) | 0.0903 | 1.59 | **0.0148** |

**Kd is essentially fixed** — 0.0148 against native's 0.0107, down from 0.0411.
**Ku is not** — still 1.6x the transistor where native is 1.07x.

## 5. NEW — the Ku excess is entirely the gate part, and the rate is right

Decomposing our Ku into `KUGATE_BASE(GUP) + KURES_TABLE(HNX)` over the same
window (`scripts/ku_excess_decompose.py`):

| width | transistor | our Ku | gate part | residual | gate/transistor |
|---|---:|---:|---:|---:|---:|
| 2354 | 0.1611 | 0.2365 | 0.2250 | 0.0011 | 1.39 |
| 1792 | 0.1037 | 0.1738 | 0.1653 | 0.0008 | 1.56 |
| 1505 | 0.0724 | 0.1308 | 0.1245 | 0.0007 | 1.63 |

**The residual is already dead there (0.001).** All of the excess is the gate part.

And it is not the decay rate. Log-linear fit over the same window:

| | transistor | native | our Ku | gate part | our GUP |
|---|---:|---:|---:|---:|---:|
| tau, ps | 116.2 | 113.9 | 111.8 | 111.9 | 112.2 |

Within 4 ps of each other. **Retracted:** the open item "our gate decays more
slowly than native's, tau ~121 vs ~106" — measured here, the rates agree. The
error is in the **level** the decay starts from, not the rate.

## 6. RETRACTED — `PU_OFF_SCALE = 0.70` was derived against an artifact

`residual_rescale_time_2026-09-04` set `pu_off` so that our turn-around would land
on "the transistor's Ku turn-around at 47–50 ps", and dismissed x0.25 as tuned.
Both halves of that are wrong.

**First error — the reference is an artifact.** Measuring the peak of the
transistor's own stressed Ku:

| width | transistor Ku peak | value | native Ku peak | value |
|---|---:|---:|---:|---:|
| 2354 | 47 ps | 0.9988 | 49 ps | 0.7310 |
| 1792 | 49 ps | **1.2892** | 48 ps | 0.5079 |
| 1505 | 51 ps | **1.1604** | 49 ps | 0.3727 |

A pull-up that entered the fall at 0.48 does not reach Ku = 1.29.

**The reason is the `C_comp dV/dt` finite difference, not ill-conditioning** — the
first version of this section said ill-conditioning and was wrong; `cond(M)` there
is 1.4–2.7. The peak value simply does not converge with the differentiation grid
(1.35 union / 1.06 at 1 ps / 0.88 at 5 ps / 0.78 at 10 ps), which is what noise
does and a physical quantity does not. Full working in
`../silicon_kukd_conditioning_2026-09-07/`.

Either way **the transistor's stressed Ku peak time cannot anchor anything** — and
this project had already recorded a caveat about that region and then used it as a
reference anyway.

**Second error — it compared different quantities.** Our "turn-around" was
measured on `KUGATE_BASE`, whose peak is where GUP *starts falling*. The
transistor's is the peak of its Ku *overshoot*. Different events.

**Third error — the input edge ramp is double-counted.** The turn-around moves 1:1
with `pu_off` on a constant +28.5 ps offset (`pu_off` 67.7 → 96–98 ps;
47.4 → 75–78 ps). That offset is the deck's own 50 ps falling edge, seen by the
command at +25 ps. Setting `pu_off` equal to an observed turn-around counts it
twice.

## 7. …and my re-derivation of x0.29 is not right either

Correcting for the ramp gives `pu_off` ~19.5 ps, scale 0.29. Tested against 0.70
and 0.25 (`scripts/pu_off_scale_derivation.py`, nine widths plus the control):

| | x0.70 | x0.29 | x0.25 | reference |
|---|---:|---:|---:|---|
| gate turn-around | 76–79 ps | **47–50** | 44–48 | — |
| Ku ratio to transistor | 1.59 | **1.21** | 1.18 | native 1.07 |
| Ku rms vs transistor | 0.0903 | **0.0365** | 0.0323 | native 0.0167 |
| Kd rms vs transistor | 0.0148 | 0.0154 | 0.0154 | native 0.0107 |
| stress pedestal, mean | 40 ps | **6 ps** | 5 ps | — |
| unstressed RMSE | 29.89 mV | **21.22** | 20.64 | — |

Every coefficient measure improves sharply. But:

| | transistor | native | x0.70 | x0.29 | x0.25 |
|---|---:|---:|---:|---:|---:|
| full-swing reversal overshoot | +64.9 mV | +83.8 | +45.0 | **+0.3** | +0.3 |
| stressed pad peak err @1792 | — | −98.5 | **−69.5** | −110.3 | −115.0 |
| stressed pad peak err @1505 | — | −115.6 | **−92.2** | −131.3 | −135.4 |

**x0.29 destroys the reversal overshoot** — a real +65 mV feature the transistor
has and native over-predicts at +84 mV — and drops the stressed pad peak below
native's.

## 8. NEW — why: `pu_off` is doing two unrelated jobs

Probing the full-swing reversal directly:

```
x0.70 at +70 ps:  gate 0.9955 (still full) + residual 0.1824  ->  Ku 1.1621
x0.29 at +70 ps:  gate 0.7679 (already falling) + residual 0.1823 -> Ku 0.9925
```

The residual spike exists to reproduce a **real** feature: the solved Ku genuinely
rises to ~1.18 at the start of a fall (section 1 — both curves show it). For that
to work the spike must land while the gate is still full.

So `pu_off` sets two things at once:

1. **when the gate state starts decaying** — the stressed coefficient fit wants
   this short (~19 ps);
2. **the phase between the gate and the residual spike** — preserving the
   full-swing Ku overshoot wants it long (~47 ps).

One parameter, two requirements, opposite directions. **`pu_off` is not
derivable** — any single value is a compromise, and both "derivations" were
picking which requirement to satisfy while believing they had measured something.

Confirming the conflict is structural, at full swing:

| | native | x0.70 | x0.29 | x0.25 |
|---|---:|---:|---:|---:|
| Ku peak time | 83 ps | 71 | 67 | 37 |
| Ku peak value | 1.1943 | 1.1641 | 1.0102 | 0.9951 |

x0.70 reproduces native's full-swing Ku overshoot best; x0.29 matches native's
stressed Ku best. Neither does both.

## 9. And one more instance of the same structural gap

Native's own Ku peak time **moves with stress**: 83 ps at full swing → 48–49 ps
stressed, a 35 ps advance. Ours barely moves — x0.70 goes 71 → 70–81, x0.29 goes
67 → 58–68.

Same shape as the bump result in `../bump_marker_2026-09-07/`: the reference
reschedules its events according to the state left behind, and we do not.

## What follows

* **Separate the two jobs.** The gate turn-off and the residual's firing time are
  currently the same parameter. They are different physical statements and need
  independent controls before either can be measured.
* **Stop using the transistor's coefficients near the reversal.** The window must
  start at +90 ps. Native is the reliable reference there, and it tracks the
  transistor to 1.07x once past the ill-conditioned region.
* **Kd needs no further work on io_buf.** 0.0148 against native's 0.0107.
* The remaining Ku error is the gate part's level, not its rate.

## Caveats

* io_buf short-high only, plus its full-swing control.
* The full-swing Ku comparison uses native as the reference because no solved
  transistor Ku exists at full swing — the stress matrix carries `silicon_ku`
  only for stressed cases. Generating one is the obvious gap to close.
* Section 3's "enter partway" construct is a fit, not a mechanism claim; it is
  reported because it separates native from replay-from-zero by 4x, not because
  native is known to implement it.

---

## Verification pass, 2026-09-07

Each claim above was re-tested against the specific way it could be wrong. One
mechanism was falsified; the rest held.

### Section 6's mechanism was wrong — corrected in `../silicon_kukd_conditioning_2026-09-07/`

"Ill-conditioned solve" is **false**: cond(M) on the stressed two-fixture runs is
1.4-2.7 throughout, only 1.4-1.8x its own baseline at the reversal.

The real mechanism is the `C_comp dV/dt` finite difference. Re-solving at
different grids, the Ku peak at 1792 ps runs 1.3488 (union) / 1.0605 (1 ps) /
0.9307 (2 ps) / 0.8831 (5 ps) / 0.7808 (10 ps). It **does not converge** -- it
grows as the grid refines, which is what differentiation noise does and what a
physical quantity does not. The conclusion (unusable near the reversal, cannot
anchor a delay) stands on a better footing than before.

### The +90 ps window is independently validated

Grid spread by slice at 1792 ps: 0.0304 over 0-50 ps, 0.0375 over 50-100,
**0.0012 over 90-140**, 0.0004 by 350-400. A 30x collapse at exactly the boundary
chosen before the test was run. Inside the window all five grids agree with the
matrix CSV to rms 0.003 (Ku) and 0.002 (Kd).

### Section 5's decay constants are a valid fit

R2 of the log-linear fit over +90..+400 ps: transistor 0.992-0.997, native
0.984-0.993, our gate part 0.993-0.996. The decay really is exponential there, so
comparing tau is meaningful.

### Section 8 proven by sweep, not argued from three points

Ten values of the scale, two objectives, each against its own reference
(`scripts/pu_off_conflict_sweep.py`):

| scale | pu_off | Ku rms vs transistor | Ku ratio | full-swing overshoot |
|---:|---:|---:|---:|---:|
| 0.10 | 6.8 ps | **0.0175** | **1.07** | 0.2 mV |
| 0.20 | 13.5 | 0.0263 | 1.14 | 0.3 |
| 0.29 | 19.6 | 0.0345 | 1.21 | 0.3 |
| 0.40 | 27.1 | 0.0470 | 1.30 | 6.3 |
| 0.50 | 33.8 | 0.0598 | 1.40 | 20.5 |
| 0.70 | 47.4 | 0.0877 | 1.60 | 45.0 |
| 0.85 | 57.5 | 0.1069 | 1.75 | **63.8** |
| 1.00 | 67.7 | 0.1286 | 1.94 | 75.3 |

Both objectives are **strictly monotone and opposite**. Best scale for Ku: 0.10.
Scale reproducing the transistor's +64.9 mV overshoot: 0.86. No interior optimum
exists, so no single value satisfies both. The claim is now proven rather than
inferred.

**And a result worth its own line:** at scale 0.10 our Ku reaches rms **0.0175**
and ratio **1.07** against the transistor -- native's own numbers are 0.0167 and
1.07. Our coefficient can be made native-quality. The price is the entire
reversal overshoot.

### Section 2 confirmed against the primary source

The manual was read in full rather than from one quoted paragraph
(`hspice_manuals/primesim_continuum_elements.pdf`, pp. 272-275):

* the selection example requires **three** rising waveforms (0 v, 0.2 v, 0.4 v) to
  have anything to choose between;
* "for ramp_rwf=2, if **more than two** rising waveforms are available, the
  solution uses the first two found" -- with exactly two it takes those two;
* "use rwf_tune only when ramp_rwf is 0 or 1" -- confirming the earlier retraction
  in `../native_waveform_count_2026-09-04/`, since the one-waveform mode runs a
  different algorithm rather than the same one degraded;
* if a mode cannot be satisfied it decrements and warns "unless the nowarn option
  is set" -- relevant to ex2's silent failure.

io_buf's `.ibs` has exactly two per edge. The rule is dormant, from the source.
