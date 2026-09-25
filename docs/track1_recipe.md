# The track-1 recipe

*2026-09-23*

How a stress-surviving model is built from an IBIS file plus **one** stressed pad run, with no
internal probing — and why each step has to be where it is.

This is the written version of the explainer page; the two are kept in step. The page carries
the figures, this carries the numbers and the exact procedure.

Studies: `results/gate_physics_2026-09-08`, `results/predriver_stages_2026-09-09`,
`results/current_limited_stages_2026-09-10`, `results/stage_count_from_file_2026-09-21`,
`results/ccomp_from_file_2026-09-22`, `results/selector_from_one_run_2026-09-23`.
Waveforms: `results/track1_summary_2026-09-23/WAVEFORMS.md`.

---

## 0. The argument, and the order of everything below

1. IBIS gives you Ku(t), and Ku(t) is a **product**: `map( gate(t) )`.
2. A truncated pulse depends on the **factors**, not the product — the reversal asks where the
   gate was.
3. A full transition gives Ku(t) with shape at **every** instant — but that fixes only the
   **composition**. Pair any monotone gate trajectory with the map that reproduces Ku(t), and the
   full-swing waveform comes out identical; the file cannot choose between them. A truncated
   pulse can, because the chain then produces a *different* gate trajectory, and where it turns
   round depends on the gate's real speed.
4. But a handful of samples cannot pick a path out of infinitely many, so we need a **physics
   prior** on which gate paths this circuit produces.
5. **Prior + samples = the factorisation.** The recipe is then just the three things that can
   corrupt it: C_comp is the product, K is one factor, the map shape is the other.

Everything below follows that order. Section 3 is a check that the frame in line 1 is
legitimate at all; sections 4 and 5 supply the prior; section 6 is the procedure.

---

## 1. The product

The I-V tables and the V-T waveforms give **Ku(t)**: the conducting fraction at each instant of
one complete transition. That is the whole of what IBIS carries about the dynamics, and it is a
composition:

```
        Ku(t)   =   map( gate(t) )
        ^^^^^       ^^^^^^^^^^^^^
        the file    two factors the file
        pins this   does NOT separate
```

A map that turns on late needs a **fast, square** gate to reach it; a map that turns on early
needs a **slow** one. Both give the same Ku(t), the same full swing, and the same everything the
file records — and completely different answers under truncation.

That is exactly the direction inv_chain moved. The universal `(0.50, 0.70)` turns on later than
the chosen `(0.40, 0.90)` — at a gate of 0.6 they give Ku 0.32 and 0.38, and below a gate of 0.5
the universal gives nothing at all — so the universal shape demanded the squarer gate, and the
earlier-turning shape admits the rolled-off one the real buffer has.

**The shipped model makes the extreme version of the row-B choice**: a command delay followed by
a fast RC gate, so its gate is fully on or fully off at any reversal and never partway. That one
choice is most of the 35–76 % it misses by.

---

## 2. The probe: why a truncated pulse is the only instrument

The file's Ku(t) is a complete waveform, with shape at every instant. What it fixes is the
**composition** `map(gate(t))` and nothing else: choose any monotone gate trajectory g(t), define
`map = Ku ∘ g⁻¹`, and the pair reproduces the file's waveform exactly. **Infinitely many
(gate, map) pairs are equally consistent with the file** — which is why no analysis of it can
factor Ku(t). Section 5's K = 5 / 7 / 9 table is the measured form of the same thing.

Cutting the input short breaks the tie, for a specific reason: the chain then produces a
**different** gate trajectory — one that turns round partway — and where it turns round
depends on how fast the gate was really travelling. A fast gate is near the rail at the reversal,
a slow one is only halfway, and the same static map reads different values off them. So the pad
under truncation depends on the two factors **separately**, where the full swing depended only on
their composition. Two consequences shape the whole method:

* **The stress axis is a sampling grid, not a robustness sweep.** The five widths are five
  instants along the gate's travel; the depth targets decide *which part of the travel* is
  visible. That is what "depth 50–90 %" in section 8 means, and why "below 50 %" is a real gap
  rather than a formality.
* **Five samples per buffer is thin**, so the model must arrive already constrained. The samples
  **select** among possibilities; they cannot invent a trajectory. Hence sections 4 and 5.

---

## 3. The frame: Ku is single-valued in the gate

Everything above writes Ku(t) as `map(gate(t))` — a fixed curve the gate is driven through. That
is only legitimate if the output stage has no state of its own. Probe the real predriver node,
solve Ku from the pad, and plot one against the other: if Ku is a genuine function of the gate,
the branch traced while the gate rises sits on the branch traced while it falls.

| buffer | gate node | hysteresis | reading |
|---|---|---:|---|
| io_buf | n2 | 0.07 – 0.11 | single-valued |
| inv_chain | vout7 | 0.09 – 0.10 | single-valued |
| ex2 | n4 | 0.47 – 0.75 → **0.09** once C_comp is corrected | single-valued |

**The output stage carries no memory**, so the modelling job really is just the factorisation.
It also says where our older model was wrong: the map architecture was right all along, the
**gate dynamics** were not.

ex2's apparent exception is not an exception — it is a C_comp error, and the same plot is the
instrument that measures it. That belongs with C_comp, in section 6.

---

## 4. The prior: what gate paths this circuit produces

`predriver_stages_2026-09-09` measured that ex2's and inv_chain's stages **under-reach** what
linear superposition predicts and **return early**. The explanation is ordinary MOS behaviour: a
CMOS inverter driving a large load is a **current source** while its input sits at the rail (its
device is in saturation) and becomes a **resistor** only near the destination rail (triode).

That picture is the stage law term for term, and it **forces exactly four numbers**:

```
   dv/dt =  s_up · h(u)   · min(1, (1−v)/x_lin)        charging
          − s_dn · h(1−u) · min(1, v/x_lin)            discharging
            ^^^^   ^^^^     ^^^^^^^^^^^^^^^^
            |      |        └─ x_lin: where saturation gives way to triode
            |      └─ vt, p: drive follows the input through the switching threshold
            └─ s_up, s_dn: the constant current — so the output is a RAMP
```

| symbol | what it is | where its value comes from |
|---|---|---|
| `s_up` | the stage's charging current | fitted to the file's own full-swing Ku(t) |
| `s_dn` | the stage's discharging current | the same fit |
| `x_lin` | where saturation gives way to triode | the same fit, or pinned at 0.45 |
| `vt` | the next inverter's switching threshold | the same fit, then recalibrated (S5) |
| `p` | the drive's curvature in overdrive | **assumed = 1**; see below |

**None of the four costs a measurement.** They are fitted to the curve the file already
contains; the stressed run is spent elsewhere.

### The test that put the family in

Fit each real stage **at full swing only**, then drive it with its *measured stressed input* and
compare against the *measured stressed output*. No stressed data in the fit.

| | ex2's output gate n4, through 3 stages from the input pin |
|---|---|
| measured, 5 widths | 0.758 / 0.797 / 0.838 / 0.880 / 0.936 |
| current-limited chain | 0.755 / 0.782 / 0.813 / 0.847 / 0.898 — **within 0.05 everywhere** |
| linear superposition | 0.926 at the deepest width — **off by 0.17** |
| rms, deepest width | 0.012 current-limited · 0.069 linear |

Each inv_chain stage is predicted to rms 0.003. On **io_buf**, which is linear end to end, the
linear structures are exact — so the non-linearity is a real, buffer-specific property. RC
cascades, delay + RC and superposition of step responses are ruled out, and the shipped model is
built from exactly those.

**Section 2's argument recurs one level down.** A current-limited ramp and the RC that reaches
the same point at the same time differ only *in between*. Endpoints agreeing while interiors
differ is why the gate's **shape**, not just its timing, is what a truncation sees.

### Why the two pinned numbers are pinned

* **`x_lin` = 0.45 is not a round number.** Fitting the real probed stages individually gave
  0.37–0.47 on ex2's three and 0.52–0.63 on inv_chain's. 0.45 sits inside that measured range.
  (inv_chain fits it rather than taking the pin, and lands high — consistent with its own
  stages.)
* **`p` cannot be fitted at full swing, ever.** The stage input is always at the rail there, so
  every p from 1 to 2 fits to rms 0.002–0.007. It acts only under a *partial* input — which is
  precisely the kind of thing section 2 says a truncation can see.

### K is first-order, because a chain extinguishes rather than attenuates

Each stage needs its input past `vt` before it delivers anything, so a short pulse loses a
little at every hop; once it falls under the threshold, nothing at all continues. That is why
the stage count is a first-order parameter rather than a refinement.

It is also, exactly, why **io_buf's pull-down chain is inert on short pulses**: its stages each
want 0.7 of the swing, so a 163–322 ps pulse dies in the first one and GDN never rises. Kd is
consequently unidentifiable from the pad — 0.4 mV across Kd = 2…5 — and the depth on a short-LOW
pulse is set by the *pull-up's turn-off* instead (`results/io_buf_pulldown_calib_2026-09-23`:
scaling it by 1.2 takes the worst error from 21.3 to 8.9 points).

---

## 5. What the file cannot pick

### A free fit is degenerate

Fit K stages to ex2's full swing with all 4K parameters free:

| K | full-swing rms | predicted stressed gate | measured |
|---:|---:|---:|---:|
| 2 | **0.005** (better) | **0.23** | 0.76 |
| 3 | 0.004 | **0.81** | 0.76 |

The K = 2 fit is *numerically better at the thing it was fitted to* and physically worthless: it
split the delay into one very slow stage plus one fast one, and by the previous section a slow
stage with a threshold swallows short pulses. inv_chain's K = 2 and 3 fits found the same corner
(`x_lin` 0.02 — a ramp-to-threshold delay dressed as a stage) and predict exactly zero.

**Fix one: constrain the stages to be identical**, which is what a real tapered predriver
approximately is. That removes the degenerate corner and leaves one structural number.

### With identical stages, the file still cannot choose K

| buffer | K | full-swing rms | stressed gate, deepest → shallowest | measured |
|---|---:|---:|---|---|
| ex2 | 2 | 0.014 | 0.29 … 0.52 | 0.758 … 0.936 |
| **ex2** | **3** | **0.0066** | **0.755 / 0.782 / 0.813 / 0.847 / 0.898** | 0.758 / 0.797 / 0.838 / 0.880 / 0.936 |
| ex2 | 4 | 0.0072 | 0.78 / 0.80 / 0.83 / 0.86 / 0.90 | — |
| inv_chain | 3 | 0.014 | **0 — pulse swallowed** | 0.879 … 1.003 |
| inv_chain | 5 | 0.0037 | 0 … 0.87 | — |
| **inv_chain** | **7** | **0.0032** | **0.672 / 0.820 / 0.909 / 0.960 / 0.987** | 0.879 / 0.935 / 0.972 / 0.992 / 1.003 |
| inv_chain | 9 | 0.0032 | 0.941 / 0.954 / 0.967 / 0.981 / 0.992 | — |

Read the **rms** column: K = 7 and K = 9 are identical to four decimals, K = 5 close behind.
Read the **stressed** column: one swallows the deepest pulse, one passes it almost intact. The
file supplies a band and cannot choose inside it.

K = 1 cannot fit even full swing (rms 0.082 on ex2) — a 1.1 ns delay with a 660 ps edge needs
stages to make the delay out of.

**Fix two: let the stressed samples choose.** The same argument applies to the map shape — the
other factor — so both are selected rather than fitted.

---

## 6. The recipe: the three things that corrupt the factorisation

The model is K identical current-limited stages (section 4) driving a static map (section 3)
into the file's own I-V tables. All K stages share one set of the four numbers.

| number | where it sits in the argument | what goes wrong if it is wrong | set by |
|---|---|---|---|
| `C_comp` | **the product** — the tables were solved with it | Ku(t) is inflated before any factoring starts | the Ku ≤ 1 bound |
| `K` | **factor one** — how fast the gate travels | a short pulse passes too easily, or is extinguished | the samples |
| `vt_map`, `α` | **factor two** — the gate-to-Ku curve | full swing right and stress wrong; inv_chain's 34 % | the samples |
| `s_up`, `s_dn`, `x_lin` | the family's own parameters | the gate's rate and its approach to the rail | the file's Ku(t) |

### Where each factor of the stage law comes from

The law is

    dv/dt = s_up*h(u)*min(1,(1-v)/x_lin)  -  s_dn*h(1-u)*min(1,v/x_lin)
    h(u)  = clip((u-vt)/(1-vt), 0, 1)**p

and the four factors have four different provenances. The textbook side is Leventhal & Green,
*Semiconductor Modeling*, §3.8 printed page 89 (pdf 105), the SPICE Level 1 (Shichman-Hodges)
equations 3-23 to 3-25:

| factor | where it comes from | verdict |
|---|---|---|
| `s_up`, `s_dn` | the capacitor law `C dV/dt = I`, with the book's saturation result that the current does not depend on V_DS | **has a source.** Channel-length modulation (the book's `LAMBDA` term) is dropped |
| `h(u) = 0` below `vt` | eq. 3-23, `I_D = 0` for `V_GS - V_th < 0` | **has a source**, same form |
| `h(u)` above `vt` | eq. 3-24, `I_D ∝ (V_GS - V_th)²` | **the source's form, one thing changed.** The book's exponent is 2; we use `p = 1` |
| `min(1, (1-v)/x_lin)` | eq. 3-25 is `V_DS(2(V_GS-V_th) - V_DS)`, a **parabola** in V_DS | **ours.** A straight line in place of that parabola |
| K identical stages | nothing | **ours** — a modelling choice, evidenced only by the fit (section 5) |

Two of those deserve their reason stated rather than buried:

* **`p = 1` is not a claim about the device.** It is an admission that the file cannot see `p`:
  every value from 1 to 2 fits the full-swing Ku(t) to rms 0.002-0.007, so the fit cannot
  choose, and 1 is taken. The book's own value is 2.
* **The linear taper is the model's biggest liberty.** Normalising both to the width of the
  region, the book passes `r(2-r)` of full current at a fraction `r` into it and we pass `r`:
  half way in, 0.75 against our 0.50. We give the current up faster than the device does. What
  keeps it usable is that `x_lin` is fitted rather than derived, and that a stressed pulse
  turns round before the gate is far into this region on most buffers.

The boundary itself is also not free in the book: saturation ends at `V_DS = V_GS - V_th`, so
the width of the resistive region is set by the device's overdrive. We make that width the free
parameter `x_lin` and fit it.

`s_up` and `s_dn` are **slopes, not currents**: `v` is normalised, so `dv/dt` is swings per
nanosecond. The physics behind `s_up` is `I_sat/(C·V_swing)`, but no current is ever computed —
ex2 fits 2.59/ns, i.e. 0.39 ns to cross a stage's swing flat out. `x_lin` is named for the
MOSFET's **linear (triode) region**: within `x_lin` of the destination rail the device has left
saturation and the drive tapers linearly to zero. `vt` is an **internal** stage's threshold —
the file's `Vinh`/`Vinl` are the input **pin's** thresholds, which the converter uses for the
input comparator, and say nothing about this node.

| `vt` | the stage handoff — and the amplitude knob | how much of a pulse survives each hop | fitted, then recalibrated |
| `p` | drive curvature under a partial input | invisible at full swing | assumed = 1 |

The four numbered steps below are S2–S6. **S1 is not one of them**: C_comp is an input the
method assumes it is given, with a validity check on it, in the same way the I-V tables are an
input. When s2ibispy extracts C_comp properly it drops into the S1 slot and S2–S6 are unchanged.

| deck | here |
|---|---|
| before the recipe | S1 — C_comp, an input with a Ku ≤ 1 check |
| recipe step 1 of 4 | S2 — fit the four numbers to the file's Ku(t) |
| recipe step 2 of 4 | S3 + S4 — the stage-count band × the shape grid = nine candidates |
| recipe step 3 of 4 | S5 — calibrate `vt` on the one stressed run |
| recipe step 4 of 4 | S6 — select on that same run's whole waveform |

### S1 — C_comp: an input, not a step

C_comp is not a model parameter, and it is not something this method derives. It is a number in
the file that **the file's own Ku tables were solved with**, so a wrong value inflates the curve
everything downstream is fitted to. Today's numbers take it from the file, because the file's
declared value fails the check below.

**How the true value is measured** (track 2, needs the gate): the solve subtracts `C_comp·dV/dt`,
and dV/dt flips sign between rise and fall, so a wrong C_comp adds on one branch and subtracts
on the other — it **opens a loop in exactly the plot of section 3**. The C_comp that closes the
loop is the one the device has: ex2 **1.70 pF**, stable across five widths, against a declared
5.0. That is section 3's measurement used as an instrument.

**What track 1 does instead** (no gate): Ku ≤ 1 identically, so keep the declared value unless it
implies Ku > 1 — ex2's declared 5.0 pF implies **1.24** — and then take the knee where Ku first
reaches 1.

| buffer | declared | implied Ku | knee | loop-measured |
|---|---:|---:|---:|---:|
| ex2 | 5.0 | **1.24** (rejected) | 2.64 | 1.70 |
| ex2_slowpre | 5.0 | 1.03 | 4.65 | 1.70 |
| inv_chain | 0.468 | 1.00 | 0.66 | 0.58 |
| io_buf | 1.2 | 1.00 | 1.65 | (undecided) |

**Why a rough answer is acceptable.** The stressed peak is not sharp in C_comp once it is in
range: ex2 scores *better* at 2.31 pF than at the measured 1.7, and ex2_slowpre is estimated at
4.65 against a measured 1.7 and still scores 5.4 %. The file's information about C_comp scales
with dV/dt, so a slow buffer carries almost none — ex2_slowpre is the failure case and survives
only because of that insensitivity.

### S2 — Fit `s_up`, `s_dn`, `vt`, `x_lin`

Target: `map(chain output)` against the file's full-swing Ku(t). Nelder–Mead, 3 restarts
(s0 = 2, 8, 30), maxiter 800, on a 2 ps grid over 4–21 ns. Stages held identical (section 5).

### S3 — The stage-count band

The 3 smallest K whose fit rms is within 25 % of the best. Taking the single best fit instead
recovers the netlist count on **1 of 13 chains**; the band contains it on **all 12 buffers**.

| buffer | band | netlist K |
|---|---|---:|
| ex2 family, inv_stage4 | 3, 4, 5 | 3 |
| inv_chain | 6, 7, 8 | 7 |
| inv_base8, inv_skewp, inv_weak | 5, 6, 7 | 7 |
| io_buf pull-up / pull-down | 1 / 3, 4, 5 | 1 / 3 |

### S4 — The shape grid

`(0.50, 0.70)` · `(0.40, 0.60)` · `(0.40, 0.90)`, where the map is
`clip((g − vt_map)/(1 − vt_map), 0, 1)^α` scaled between the file's own off and on levels.

**S3 × S4 = 9 candidates per buffer**, each with its own S2 fit.

### S5 — Calibrate on the one stressed run

Bisect `vt` over [0, 0.7], 7 ngspice runs, until the model's peak matches the measured one.
Fallback if `vt` cannot bracket it: scale `s_up` and `s_dn` together over [0.5, 2.0], 7 runs.

**Why `vt` and not the rates.** The rates were fitted to reproduce the full swing; moving them
breaks it. `vt` changes **when** the chain hands off without changing how fast it runs — the one
number that buys stressed amplitude at no full-swing cost. It also absorbs M2's own limit: the
stage law is slightly too weak for an input at 0.85–0.9 of swing, and over K stages that
compounds.

### S6 — Select on the same run's whole waveform

Smallest rms between model and transistor pad over that pulse and 1.5 ns of its return, at the
calibration width only.

**Why not the peak.** S5 has just forced the peak to match at that width for **every**
candidate; measured, adding a peak gate to the rule changes nothing. Ranking on peaks at the
other widths is worse than useless:

| ranked by | mean waveform error over all widths | lag of the picks |
|---|---:|---|
| whole waveform at the calibration width | **52.3 mV** | −27 … +17 ps |
| best possible in the grid | 51.7 mV | — |
| best stressed peak | **217.3 mV** | +155 … +300 ps |

The rms window (the pulse plus 1.5 ns of its return) was chosen once and never tuned — the
rule's one untested free choice.

### Why selection rather than one fixed correction

"Stressed" hides three mechanisms, and any single correction fits one and misses two:

| buffer | what is truncated | probed gate excursion |
|---|---|---|
| io_buf | the predriver itself | 0.42 – 0.63 of supply |
| inv_chain | time — it completes but arrives late | 0.91 – 1.03 |
| ex2 | neither; it is speed-limited | 0.67 – 0.72, whatever the width |

---

## 7. The result

| | |
|---|---|
| **12 of 12 within ±10 %** | range 3.2 % (inv_stage4) … 10.0 % (ex2_skewp, on the line), mean 6.9 % |
| shipped model, same pulses | 35 – 76 % on 11 of 12 |
| inv_chain, file-only | **5.1 %**, against 25.8 % for the build made from probed silicon |
| selector quality | within **1 %** of the best build the grid contains |

**What it costs:** full-swing pad rms worse than shipped on 10 of 12 (ex2 61 vs 16 mV) — we buy
interior accuracy with endpoint accuracy · on a stressed train the shipped model still wins on
ex2 (−3.7 % against −9.5) and io_buf (−2.0 against +4.6) · io_buf beaten outright (4.0 vs 7.7 %).

---

## 8. Which part of the path has been sampled

Read against section 2, this is not a generic coverage table: it says which instants of the
gate's travel we have looked at, and in which direction.

| axis | sampled | not sampled |
|---|---|---|
| where in the travel | 50, 60, 70, 80, 90 % of the settled swing | below 50 % — the early part of the path |
| direction | short HIGH | **short LOW on 11 of 12 buffers** |
| pulses | one | trains |
| load | 50 Ω ∥ 2 pF | anything else |
| input edge | 50 ps on the three probed buffers, 1 ps on the nine variants | a sweep at fixed width |
| corner | Typical | Min / Max, supply, temperature |

---

## 9. What is not yet honestly file-only

1. **The shape grid was chosen from results on these same 12 buffers.** `(0.40, 0.60)` and
   `(0.40, 0.90)` are the two best of an earlier grid run on this set, so S4 has seen the answer
   key. A thirteenth buffer may need a shape the grid does not contain.
2. **`x_lin` is inconsistent** — pinned at 0.45 on ten buffers, fitted on inv_chain and io_buf.
   The pinned value is inside the 0.37–0.63 the real stages fitted, so it is defensible, but it
   should be one or the other.
3. **`p` is assumed.** By section 2's own argument it is exactly the kind of parameter a
   partial-input observation can see and a full swing cannot — and the recipe already takes one
   such observation. An open gap rather than a closed one.
