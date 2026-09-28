# Can the device's own taper replace `x_lin = 0.45`?

*2026-09-28. Plan and pre-recorded hypothesis in `PLAN.md`. Script: `scripts/device_taper_probe.py`.*

## Answer

**Yes — but not with the textbook long-channel form. The one that works is the
velocity-saturated boundary.**

`q(2−q)` with `q = d / (u−vt)^(p/2)` costs **one parameter fewer** than today's
`min(1, d/x_lin)`, is **sourced**, fits full swing **as well or better**, and predicts the
stressed gate **peak** substantially better on both buffers. It predicts the stressed gate
*waveform* worse. It has not yet been tested in the Ku domain or at the pad, which is where
track 1 actually lives — so this is a strong candidate, not a decision.

And separately, a result that was not the question but matters more for the write-up:
**`x_lin = 0.45` is considerably more defensible than `docs/stage_law_walkthrough.md` §5 says.**

---

## 1. The numbers

Five drain factors, one integrator (verified identical to `cl.simulate` to **1.1e-16**), one
optimiser budget, fitted to **full swing only**, then asked to predict the stressed gate.
`edge@1` is the boundary each form implies at full gate drive, in swings.

### ex2, K = 3, 3.3 V

| form | n | full rms | 810 | 830 | 858 | 895 | 975 | mean\|e\| | wave rms | `vt` | edge@1 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| *measured* | | | .758 | .797 | .838 | .880 | .936 | | | | |
| `min(1,d/x_lin)` **today** | 4 | 0.0066 | .756 | .782 | .813 | .847 | .898 | 0.023 | **0.0108** | 0.265 | 0.406 |
| `q(2−q), d/x_lin` | 4 | 0.0057 | .739 | .769 | .804 | .844 | .902 | 0.030 | 0.0105 | 0.302 | 0.730 |
| `min(1,d/ov)` | 3 | 0.0092 | .856 | .873 | .890 | .908 | .934 | 0.051 | 0.0211 | 0.414 | 0.586 |
| `q(2−q), d/ov` long-channel | 3 | 0.0066 | .830 | .850 | .872 | .895 | .929 | 0.036 | 0.0277 | 0.240 | 0.760 |
| **`q(2−q), d/ov^(p/2)` vel-sat** | **3** | **0.0062** | .785 | .811 | .839 | .871 | .917 | **0.014** | 0.0161 | 0.325 | 0.822 |

### inv_chain, K = 7, 1.8 V

| form | n | full rms | 104 | 106 | 111 | 119 | 135 | mean\|e\| | wave rms | `vt` | edge@1 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| *measured* | | | .879 | .935 | .972 | .992 | 1.003 | | | | |
| `min(1,d/x_lin)` **today** | 4 | **0.0032** | .701 | .832 | .913 | .961 | .987 | 0.077 | **0.0079** | 0.507 | 0.482 |
| `q(2−q), d/x_lin` | 4 | 0.0032 | .658 | .823 | .917 | .966 | .989 | 0.086 | 0.0103 | 0.554 | 1.106 |
| `min(1,d/ov)` | 3 | 0.0032 | .960 | .968 | .975 | .985 | .993 | 0.027 | 0.0148 | 0.496 | 0.504 |
| `q(2−q), d/ov` long-channel | 3 | 0.0035 | .978 | .983 | .988 | .993 | .998 | 0.034 | 0.0188 | 0.392 | 0.608 |
| **`q(2−q), d/ov^(p/2)` vel-sat** | **3** | 0.0033 | .941 | .958 | .974 | .987 | .996 | **0.020** | 0.0146 | 0.466 | 0.731 |

**Peak error, today against velocity-saturated:**

```
ex2         today  -0.002  -0.015  -0.025  -0.033  -0.038     all low, drifting
            vsat   +0.027  +0.013  +0.002  -0.009  -0.019     straddles zero

inv_chain   today  -0.178  -0.103  -0.059  -0.031  -0.016     badly low at the deep end
            vsat   +0.062  +0.023  +0.001  -0.005  -0.008     straddles zero
```

Today's errors are **one-signed and drifting** — the signature of a missing mechanism. The
velocity-saturated form's straddle zero.

---

## 2. What the 2×2 attributes

The four original forms were a deliberate 2×2 (curve × boundary) so a change could be
attributed rather than lumped.

**The curve hardly matters.** Straight line → parabola, boundary held fixed: full rms
0.0066→0.0057 on ex2, 0.0032→0.0032 on inv_chain; stressed error 0.023→0.030 and 0.077→0.086.
**The most-criticised approximation in the stage law — the straight taper — is nearly
irrelevant.**

**The boundary is everything.** Fixed → moving, curve held straight: ex2 stressed error
0.023→0.051 (worse), inv_chain 0.077→0.027 (much better). Opposite signs on the two buffers.

**And the real parameter is how fast the boundary moves.** A fixed boundary **undershoots**
(10 of 10 cases). A fully-moving long-channel boundary **overshoots** (8 of 10). The
velocity-saturated boundary moves as `√overdrive` — between the two — and is the best peak
predictor on both buffers. That is the pre-recorded hypothesis confirmed, after the
long-channel form alone had appeared to refute it.

---

## 3. The result that decides it: the implied boundary is physically right

The fit is never told the supply or `V_th`. If a form is physically sound, the boundary it
implies at full gate drive should land near the device's own — and should be **larger on the
3.3 V part than on the 1.8 V part**.

| buffer | supply | today | long-channel | **velocity-sat** | a real device |
|---|--:|--:|--:|--:|--:|
| ex2 | 3.3 V | 0.450 | 0.760 | **0.822** | 0.88 – 0.89 |
| inv_chain | 1.8 V | 0.450 | 0.608 | **0.731** | 0.77 – 0.80 |

(device values from `results/model_provenance_2026-09-25/check_xlin.py`, `VTH0` in
`buffers/models/hspice.mod`)

**The velocity-saturated form recovers the right ordering and lands within 0.06–0.07 of the
silicon**, from a fit that saw only a full-swing waveform. `0.45` is off by 0.32–0.44 and is
the same number on both parts, which cannot be right when the two have different thresholds.

Closed form, for the record: the boundary at full drive is `1 − vt` for the long-channel form
and `√(1 − vt)` for the velocity-saturated one. Neither introduces a new parameter — **`x_lin`
collapses into `vt`.**

---

## 4. The cost, stated plainly

**Waveform rms gets worse on both buffers**: ex2 0.0161 against 0.0108, inv_chain 0.0146
against 0.0079 — roughly 1.5–1.9×. So the trade is **better peaks, worse shape**.

That matters because the recipe's S6 selects on the whole waveform, having measured that
ranking on peaks alone is far worse (217.3 mV against 52.3 mV). A form that improves peaks and
degrades shape could help the depth number and hurt the selector. **Not resolvable on this
bench** — it needs the pad.

---

## 5. Incidental, and it changes the write-up: 0.45 is defensible

Left **free** in this gate-domain fit, `x_lin` lands at **0.406** (ex2) and **0.482**
(inv_chain) — bracketing 0.45, and consistent with the 0.37–0.47 and 0.52–0.63 the individually
probed stages gave.

`docs/stage_law_walkthrough.md` §5 says free `x_lin` "lands anywhere between 0.02 and 1.50 — the
full-swing data barely constrains it". That is true of the **Ku-domain** fit and **false of the
gate-domain fit**. Against the true gate the parameter is well determined and it agrees with the
pinned value.

**So the problem was never the number. It is that the file-only fit cannot see it.** 0.45 has an
empirical basis; what it lacks is a derivation — and §3 above is that derivation, at a price.

---

## 6. What this does not show

* **Wrong domain.** This is the §8 bench: fitted against the **probed** gate. Track 1 fits in
  the **Ku domain** through an assumed map. The swap has to be re-tested there.
* **Not at the pad.** Gate accuracy is not depth accuracy; the map and the I-V tables sit
  between.
* **Two buffers**, one direction (short HIGH), one K each.
* **`vt` now does two jobs** in every moving-boundary form — threshold and boundary — which is
  the shape of the `pu_off` trap. It has not misbehaved here (fitted 0.325 and 0.466, both
  interior, neither on a bound, and *neither opens the mid-input dead band* that today's
  inv_chain fit at `vt = 0.507` does), but it is a coupling to watch.
## 6b. A committed result no longer reproduces — and it is not this harness

ex2's `linear_const` reproduces the committed §8 numbers exactly; inv_chain's does not
(**.701 here against .672 committed**). I guessed the pulse-swallowing cliff amplifying a
1e-16 integrator difference. **That guess was wrong.** Running `cl.fit_chain_shared` — the
owner, untouched — side by side with the probe:

```
=== inv_chain, K=7 ===
  cl.fit_chain_shared   rms 0.00316  s_up 22.952 s_dn 22.304 vt 0.508 x_lin 0.482
  probe linear_const    rms 0.00316  s_up 22.952 s_dn 22.304 vt 0.508 x_lin 0.482
       W  measured       cl    probe  committed CSV
     104     0.879    0.701    0.701          0.672
     106     0.935    0.832    0.832          0.820
  same params, both integrators: max diff 1.36e-20
```

**Identical parameters, identical predictions, integrators agreeing to 1e-20.** The two fitters
are the same fitter. What disagrees is `inv_chain_chain_shared_K.csv`, committed 09-10: the
current code does not produce it.

So the probe is sound and **the committed CSV is stale** — some change since 09-10 moved
inv_chain's fit, and nobody noticed because nothing re-ran it. It matters beyond this study:

| quoted where | says | code produces today |
|---|--:|--:|
| `stage_law_walkthrough.md` §8 ("off by 0.21 at 104 ps") | 0.672 | **0.701** (off by 0.18) |
| `track1_recipe.md` §5 stressed-gate row | 0.672 … 0.987 | 0.701 … 0.987 |

Neither conclusion changes — both are large undershoots, and K = 7 still beats K = 5 and K = 3
by a wide margin. But **the documented number is not the one the code gives**, and that should
be chased down rather than papered over: re-run `current_limited_stage_model.py --shared` and
find what moved. Not done here; it is outside this study's question.

* **One K per buffer.** K was taken from §8 rather than re-selected per drain factor. A form
  that changes the gate's speed could shift the best K, and that interaction is untested.

## 7. Next

1. Repeat in the **Ku domain** (`gate_chain_prototype.fit_chain_ku`) — the decisive test.
2. If it survives, emit it: `chain_command.stage_block` writes the drain factor as SPICE, and
   the change is one expression.
3. Then the pad, on all 12 buffers, against the existing ±10 %.
4. `p` and the boundary exponent are now **the same parameter** (`α/2`). The stressed runs can
   see `p` where full swing cannot — so fitting `p` would now also be fitting the boundary. That
   is either an elegant simplification or a new identifiability problem, and it should be
   checked before anything ships.
