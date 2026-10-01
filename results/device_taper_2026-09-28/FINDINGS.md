# Can the device's own taper replace `x_lin = 0.45`?

*2026-09-28. Plan and pre-recorded hypothesis in `PLAN.md`. Scripts:
`scripts/device_taper_probe.py`, `scripts/device_alpha_extract.py`.*

> **This file was rewritten after its first version was reviewed.** The first version's
> headline — that the velocity-saturated form is "physically right" — was **refuted** by
> measuring the actual devices. The yardstick it used was a long-channel *prediction*, not a
> measurement. What survives is a better result, and the opposite recommendation. Section 7
> lists every claim that changed.

## Answer

**No — and it turns out it should not.** `x_lin = 0.45` is close to the devices' real
saturation boundary. What was wrong was never the number; it was the justification attached
to it.

Measured on the transistors as drawn, `V_D0/V_DD` is **0.23 – 0.42**. Two independent fits
that were never shown the devices land on **0.429** (ex2) and **0.487** (inv_chain). The
pinned **0.45** sits right there. The old rationale pointed at long-channel's 0.77–0.89,
which is the one number in the set that is wrong.

So `x_lin` is not deleted. It is **renamed and made measurable**: it is `V_D0/V_swing`, the
drain saturation voltage, extractable from any model card in one DC sweep.

**And the drain factor should not change at all.** Sakurai–Newton's drive-dependent boundary
looked promising on the gate-domain bench (inv_chain's stressed peak error 0.077 → 0.016 for no
new parameter). **It does not survive the Ku domain** (§8): every four-parameter form fits the
file's Ku(t) within 1–10 %, and the drive-tied boundary is located no better than the constant
— both land at about half the measured value. The one change this study supports is to **pin
`x_lin` per buffer from the model card instead of fitting it or using a universal 0.45.**

---

## 1. The measurement (the part that decides everything else)

`results/model_provenance_2026-09-25/check_xlin.py` compared our `x_lin` against
`1 − VTH0/V_DD`. That is the long-channel Shockley `V_DSAT = V_GS − V_TH` — **a prediction of
the very model we depart from**, and the one the α-power law exists because it fails.

`scripts/device_alpha_extract.py` replaces it with the devices' own numbers, by Sakurai &
Newton's Appendix A procedure in HSPICE: `V_D0` from where the origin tangent meets the
saturation level (the breakpoint of their piecewise model), α from the log-log slope of
saturation current against overdrive.

| device | card | drawn L | **V_D0/V_DD** | **α** |
|---|---|---:|---:|---:|
| ex2 predriver NMOS | `hspice.mod` | 0.6 µm | **0.347** | 1.11 |
| ex2 predriver PMOS | `hspice.mod` | 0.6 µm | **0.420** | 1.39 |
| inv_chain NMOS | `HL18G-S3.7S.lib` | 180 nm | **0.232** | 1.27 |
| inv_chain PMOS | `HL18G-S3.7S.lib` | 180 nm | **0.400** | 1.32 |

| | |
|---|---|
| long-channel prediction (the old yardstick) | 0.66 – 0.89 |
| **measured** | **0.23 – 0.42** |
| `x_lin` today | **0.45** |

**Two errors in the old comparison, both inflating it.** It was a prediction rather than a
measurement; and it used `hspice.mod`'s VTH0 for *every* buffer, when inv_chain runs on
`HL18G-S3.7S.lib` (VTH0 0.464/0.613 against 0.363/0.407). The "1.8 V parts: 0.77/0.80" row was
never inv_chain's device. `check_xlin.py` is corrected.

**α is measured at 1.11 – 1.39, not 2.** That closes an open gap: `p = 1` is well supported on
these devices and `p = 2` is not. The walkthrough listed the α-power law as "a lead, not
evidence" — it is now evidence, for this silicon.

---

## 2. Three independent routes converge on ~0.45

| route | ex2 | inv_chain |
|---|---:|---:|
| measured on the device | 0.347 – 0.420 | 0.232 – 0.400 |
| `x0` free, Sakurai–Newton's model (never saw the device) | **0.429** | **0.487** |
| `x_lin` free, today's form | 0.406 | 0.482 |
| `x_lin` pinned, shipped | 0.45 | 0.45 |

The two fits agree with each other, with the pinned constant, and with the silicon. **0.45 was
right all along.**

Note the parabola variants do *not* do this: they push `x0` to **0.758** and **0.958**, roughly
double the device, compensating for the parabola's gentler taper. **The straight line finds the
physical value and the parabola does not** — and the straight line is what Sakurai–Newton's
model actually uses, so the citable form and the physically-correct form are the same form.

---

## 3. All seven drain factors

One integrator (verified identical to `cl.simulate` to **1.1e-16**), one optimiser budget,
fitted to **full swing only**, then asked to predict the stressed gate. `q` is clipped —
`q̂ = min(q,1)` — on both Heun stages and both directions.

### ex2, K = 3, 3.3 V, 0.6 µm — measured `.758 .797 .838 .880 .936`

| form | n | full rms | mean\|e\| | wave rms | `x_lin`/`x0` | `vt` |
|---|--:|--:|--:|--:|--:|--:|
| `min(1,d/x_lin)` **today** | 4 | 0.0066 | 0.023 | **0.0108** | 0.406 | 0.265 |
| `q(2−q), d/x_lin` | 4 | 0.0057 | 0.030 | 0.0105 | 0.730 | 0.302 |
| `min(1,d/ov)` | 3 | 0.0092 | 0.051 | 0.0211 | — | 0.414 |
| `q(2−q), d/ov` long-channel | 3 | 0.0066 | 0.036 | 0.0277 | — | 0.240 |
| `q(2−q), d/ov^(p/2)` collapsed | 3 | 0.0062 | **0.014** | 0.0161 | — | 0.325 |
| **`min(1,d/(x0·D^(p/2)))` Sakurai–Newton** | 4 | 0.0070 | 0.024 | 0.0204 | **0.429** | 0.262 |
| `q(2−q), d/(x0·D^(p/2))` | 4 | 0.0060 | 0.016 | 0.0188 | 0.758 | 0.286 |

### inv_chain, K = 7, 1.8 V, 180 nm — measured `.879 .935 .972 .992 1.003`

| form | n | full rms | mean\|e\| | wave rms | `x_lin`/`x0` | `vt` |
|---|--:|--:|--:|--:|--:|--:|
| `min(1,d/x_lin)` **today** | 4 | 0.0032 | 0.077 | **0.0079** | 0.482 | 0.507 |
| `q(2−q), d/x_lin` | 4 | 0.0032 | 0.086 | 0.0103 | 1.106 | 0.554 |
| `min(1,d/ov)` | 3 | 0.0032 | 0.027 | 0.0148 | — | 0.496 |
| `q(2−q), d/ov` long-channel | 3 | 0.0035 | 0.034 | 0.0188 | — | 0.392 |
| `q(2−q), d/ov^(p/2)` collapsed | 3 | 0.0033 | 0.020 | 0.0146 | — | 0.466 |
| **`min(1,d/(x0·D^(p/2)))` Sakurai–Newton** | 4 | 0.0032 | **0.016** | 0.0105 | **0.487** | 0.498 |
| `q(2−q), d/(x0·D^(p/2))` | 4 | 0.0032 | 0.013 | 0.0117 | 0.958 | 0.522 |

**Sakurai–Newton's own model on inv_chain: the stressed peak error falls from 0.077 to 0.016 —
4.8× — at identical full-swing rms and essentially the same boundary (0.487 against 0.482).**
The whole gain comes from letting the boundary move with drive. Waveform rms goes 0.0079 →
0.0105, a far smaller cost than any other form paid.

---

## 4. Offset or trend? Per buffer, honestly

Mean |error| flatters a form whose error merely *straddles* zero. The spread across widths is
the harder test.

```
ex2        today   -0.002 -0.015 -0.025 -0.033 -0.038     spread 0.036
           S-N     +0.049 +0.030 +0.011 -0.005 -0.023     spread 0.072    WORSE

inv_chain  today   -0.178 -0.103 -0.059 -0.031 -0.016     spread 0.162
           S-N     +0.026 -0.005 -0.018 -0.017 -0.013     spread 0.044    BETTER
```

**On ex2 the S-N form is an offset shift and its trend is worse. On inv_chain it is better in
both offset and trend.** The earlier draft's "straddles zero" framing overstated the ex2 case
and is withdrawn.

The likely reason for the split is in §1: inv_chain is **180 nm** drawn and strongly
velocity-saturated (measured boundary 0.232), ex2 is **0.6 µm** (0.347–0.420). Drive-dependent
movement is a bigger effect on the shorter device. That is a hypothesis this study supports but
does not establish.

**Statistical weight.** Five widths per buffer are highly correlated — a single stressed
trajectory sampled five times. "4.8× better" rests on **two buffers**, not ten observations.

---

## 5. Why the waveform gets worse

Every moving-boundary form has a boundary of 0.43–0.82 at full drive, so a fully driven stage
spends most of its travel in triode and behaves largely like an RC; it stays current-limited
only under partial drive. That is physically coherent, and partial drive is the stressed case —
but §8 of the walkthrough credits the **ramp shape** for the model's stressed behaviour, so
trading ramp for RC at full swing is a plausible mechanism for the waveform-rms cost. Worth
testing directly rather than assuming.

---

## 6. What this does not show

* **Wrong domain.** This is the §8 bench, fitted against the **probed** gate. Track 1 fits in
  the **Ku domain** through an assumed map. The decisive test has not been run.
* **Not at the pad.** Gate accuracy is not depth accuracy.
* **Two buffers, one direction, one K each.** K was taken from §8 rather than re-selected per
  form; a form that changes the gate's speed could shift the best K, and that interaction is
  untested.
* **`V_TH` in §1 is extracted at 2 % of peak current**, a crude definition. `V_D0` and α do not
  depend on it strongly, but the "Level-1 prediction" column does.
* **The √ arm was post hoc.** `PLAN.md` pre-registered a different fifth variant (a moving
  boundary with its own threshold). The velocity-saturated arm was added *after* seeing the
  long-channel result, and scored on the same stressed data. The §1 measurement is independent
  of it and is what should carry the weight.

## 6b. A committed result no longer reproduces — and it is not this harness

ex2's `linear_const` reproduces the committed §8 numbers; inv_chain's does not (**.701 here
against .672 committed**). Running `cl.fit_chain_shared` — the owner, untouched — beside the
probe:

```
  cl.fit_chain_shared   rms 0.00316  s_up 22.952 s_dn 22.304 vt 0.508 x_lin 0.482
  probe linear_const    rms 0.00316  s_up 22.952 s_dn 22.304 vt 0.508 x_lin 0.482
     104     0.879    0.701    0.701          0.672   <- committed CSV
  same params, both integrators: max diff 1.36e-20
```

**Resolved 2026-10-01:** the cause was the integrator (the CSV predates the Euler → Heun change by thirteen hours) and the table is regenerated in `results/stage_law_doc_2026-10-01/` (K = 7: 0.701 confirmed; K = 5 at 135 ps: 0.869 → 0.810; K = 3 unchanged at zero).

Identical fits. **The committed `inv_chain_chain_shared_K.csv` is stale**, and its K = 5 and
K = 3 rows are presumably stale too — so the whole file needs re-running before any of it is
re-quoted. It is quoted in `stage_law_walkthrough.md` §8 (0.672, "off by 0.21") and
`track1_recipe.md` §5.

---

## 7. Claims withdrawn or corrected

| claim | status |
|---|---|
| "the implied boundary is physically right", vsat 0.822/0.731 vs "real device" 0.77–0.89 | **withdrawn.** The yardstick was a long-channel prediction. Measured is 0.23–0.42, which makes the vsat form the *worst* of the three, not the best |
| "0.45 is off by 0.32–0.44 and cannot be right for both parts" | **withdrawn.** 0.45 is close to the measurement on both |
| "getting the supply ordering right corroborates the form" | **withdrawn.** The long-channel form reproduces the ordering too; any boundary decreasing in `vt` does |
| "the velocity-saturated form is Sakurai–Newton" | **corrected.** It hard-wires their free `x0` to `(1−vt)^(p/2)`. Their model has `x0` measured independently, and uses a straight line. Both now run |
| "straddles zero" | **corrected.** True on inv_chain, an offset shift on ex2 (§4) |
| "one expression in the emitter" | **corrected.** A fractional power needs `max(·, ε)` before the power and the division, or ngspice hits NaN and infinite derivatives at threshold |
| "these are ~0.6 µm devices" (3 documents) | **corrected.** True of ex2; inv_chain is 180 nm drawn on a different card |
| `check_xlin.py`'s 1.8 V row | **corrected.** It used `hspice.mod`'s VTH0 for a buffer that does not use that card |

## 8. The decisive test: the Ku domain cannot choose a drain factor

`scripts/device_taper_ku.py` repeats the comparison in the domain track 1 actually fits in.
The target is `v(x1.kugate_base)` from a full-swing ngspice run of the **shipped pybis2spice
subcircuit**, built from the IBIS file with C_comp rewritten — no transistor anywhere in the
loop. Same cost and optimiser budget as `gate_chain_prototype.fit_chain_ku`.

**Harness validated first.** Pinning `x_lin = 0.45`, as the shipped build does, reproduces the
committed track-1 fit exactly:

| | `s_up` | `s_dn` | `vt` | Ku rms |
|---|--:|--:|--:|--:|
| committed track-1 ex2 build | 2.190 | 2.124 | 0.528 | 0.023 |
| this harness, `x_lin` pinned 0.45 | **2.19** | **2.12** | **0.528** | **0.0233** |

### The result

| ex2, K = 3 | n | Ku rms | `x0`/`x_lin` | | inv_chain, K = 7 | n | Ku rms | `x0`/`x_lin` |
|---|--:|--:|--:|---|---|--:|--:|--:|
| `min(1,d/x_lin)` **today** | 4 | **0.0193** | 0.206 | | `min(1,d/x_lin)` **today** | 4 | **0.0069** | 0.135 |
| `q(2−q), d/x_lin` | 4 | 0.0193 | 0.333 | | `q(2−q), d/x_lin` | 4 | 0.0076 | 0.546 |
| **Sakurai–Newton** | 4 | 0.0195 | 0.218 | | **Sakurai–Newton** | 4 | 0.0069 | 0.147 |
| `q(2−q)` + S-N edge | 4 | 0.0195 | 0.350 | | `q(2−q)` + S-N edge | 4 | 0.0071 | 0.177 |
| collapsed vsat | 3 | 0.0220 | — | | collapsed vsat | 3 | 0.0076 | — |

**1. Every four-parameter form fits Ku(t) the same.** Spread 0.0002 on ex2 (1 %) and 0.0007 on
inv_chain (10 %). The file cannot choose the curve *or* the boundary. This is the §1 degeneracy
for the third time — after K (§7.1) and `vt` (§5), now the drain factor itself.

**2. The drive-tied boundary is no better determined than the constant.** That was the
hypothesis, and it fails outright:

```
                          ex2            inv_chain
measured on silicon       0.347-0.420    0.232-0.400
today, x_lin free         0.206          0.135
Sakurai-Newton, x0 free   0.218          0.147
```

S-N lands within 0.01 of today's value, and **both land at roughly half the device**. Tying the
boundary to drive buys no identifiability.

**3. The gate-domain winner loses here.** The 3-parameter collapsed vsat is 14 % / 10 % worse in
Ku rms, and its `vt` reaches 0.506 and **0.650** — the latter near the 0.7 bound, both opening
the mid-input dead band. Not adoptable.

### So: measure `x0`, do not fit it

The fit, given freedom, puts the boundary at half the physical value. One DC sweep puts it in
the right place. **That removes a *fitted* parameter rather than a parameter** — a better
outcome than either option this study set out to compare, and it is what §2's convergence was
really pointing at.

It also **vindicates the recipe's existing choice to pin `x_lin` rather than fit it**. Pinning
costs 21 % in Ku rms on ex2 (0.0233 against 0.0193) and buys a boundary that is defensible. The
one change worth making is that the pin could be **per buffer and measured** — ex2 ≈ 0.38,
inv_chain ≈ 0.30 — rather than a universal 0.45.

## 9. Next

1. **Do not change the drain factor.** Neither domain supports it: the Ku domain cannot see the
   difference, and the gate-domain gain did not survive.
2. **Pin `x_lin` per buffer from the model card** (`device_alpha_extract.py`) instead of the
   universal 0.45, and score the pad on all 12. This is the only change this study supports, and
   it is cheap.
3. Re-run `current_limited_stage_model.py --shared`; find what moved inv_chain since 09-10.
4. `p` is measured at 1.11–1.39 (§1). The recipe assumes 1. Worth scoring `--p 1.25` at the pad.
5. The identifiability result is the real find: **three separate parameters — K, `vt`, and now
   the drain factor — are all invisible to Ku(t).** That is an argument about what the one
   stressed run has to carry, and it belongs in `docs/stage_law_walkthrough.md` §7.
