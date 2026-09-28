# The stage law, term by term — and how Ku is built from it

*2026-09-28*

A walkthrough of the one equation track 1 rests on:

```
dv/dt = s_up · h(u) · min(1, (1−v)/x_lin)  −  s_dn · h(1−u) · min(1, v/x_lin)
h(x)  = clip((x − vt) / (1 − vt), 0, 1) ** p
```

what every symbol means, why the equation has this shape, **how Ku(t) is constructed by running
it**, and what the comparison against the file's own Ku(t) can and cannot decide.

Companion to [track1_recipe.md](track1_recipe.md), which gives the procedure. This one gives the
equation. Where the two overlap, the recipe is the procedural authority and this is the
explanation.

**Canonical implementations.** Every claim below is checkable in one of:

| what | file |
|---|---|
| the law, the integrator, the fitter | `scripts/current_limited_stage_model.py` |
| the Ku-domain fit (`fit_chain_ku`) | `scripts/gate_chain_prototype.py` |
| the emitted SPICE (`stage_block`, `patch_chain`) | `tools/pybis2spice/pybis2spice/chain_command.py` |
| the map prior (`prior`, `prior3`) | `scripts/physics_map_gate_from_ibis.py` |
| the provenance audit, with runnable checks | `results/model_provenance_2026-09-25/` |

---

## 1. Why there is an equation here at all

The IBIS file gives **Ku(t)**: the conducting fraction of the pull-up at each instant of one
complete transition. That is a **product of two things**:

```
Ku(t)  =  map( gate(t) )
          ^^^^^^^^^^^^^
          a static curve   a trajectory
          (gate → Ku)      (time → gate)
```

The file pins the *product* and says nothing about the *factors*. Pair any monotone gate
trajectory `g(t)` with the map `Ku ∘ g⁻¹` and you reproduce the file's waveform exactly —
infinitely many (gate, map) pairs fit equally well.

For a **full** transition that does not matter: the product is all you need. For a **truncated**
pulse it is the whole problem, because the chain then produces a *different* gate trajectory, one
that turns round partway, and where it turns round depends on how fast the gate was really
travelling. A fast gate is near the rail at the reversal; a slow one is only halfway; the same
static map reads different values off them.

So track 1 needs a **gate trajectory**, and the file cannot supply one. The stage law is the
prior that supplies it: *this is the family of trajectories a CMOS predriver produces.* The file's
Ku(t) then picks a member of that family instead of picking out of thin air.

That is the entire motivation. Everything below is what the family is, and how the picking works.

---

## 2. The coordinates — read this before the equation

This trips people up more than the equation does.

### u and v are normalised, per node

Each physical node is mapped to a 0→1 scale using **its own** rest and settled-high levels:

```python
rest = node voltage at 4.5 ns      # before the edge
high = node voltage at 14.5 ns     # long after it
normalised = (v_node − rest) / (high − rest)
```

*(`load()` in `current_limited_stage_model.py`)*

For an **inverting** node, `high < rest`, so the denominator is **negative** — and the normalised
signal still runs 0 → 1. This is the trick that lets a chain of inverters be written as a chain of
**non-inverting** stages. You never carry a sign through the chain; every stage reads "input goes
up, output goes up."

- **`u`** = the stage's normalised **input** (its gate)
- **`v`** = the stage's normalised **output** (its drain)

### What u and v are in device terms

For the device doing the work inside a stage:

| model symbol | device quantity |
|---|---|
| `u` | \|V_GS\| / swing — how hard the device is turned on |
| `1 − v` | \|V_DS\| / swing — how much headroom is left to the destination rail |

That second line is the one worth memorising. **`1 − v` is the drain-source voltage.** When the
output is far from its destination rail, `1 − v` is large and there is plenty of V_DS; as it
arrives, `1 − v → 0` and the device is collapsing into triode. That is why the taper term is
written `min(1, (1−v)/x_lin)` and not something in `v`.

### dv/dt is a slope, not a current

`v` is dimensionless, so `dv/dt` is in **swings per nanosecond**. `s_up` and `s_dn` are
**slopes**, not currents. Nothing in the model ever computes an ampere.

The physical content behind `s_up` is `I_sat / (C · V_swing)` — but that grouping is never
unpacked, and it does not need to be. ex2's track-1 build fits `s_up = 2.190 /ns`, i.e. a stage
flat out crosses its full swing in **457 ps**. (File-only for the stages and the threshold — §6.4
is precise about what that build does and does not take from the file.)

> **Why this matters.** Calling them currents was an error in an earlier write-up. They are
> slopes. Anything that reads "the stage's charging current" means "the slope the stage produces
> while it is behaving as a current source."

---

## 3. The equation, term by term

```
dv/dt =  s_up · h(u)   · min(1, (1−v)/x_lin)        ← charging  (pull-up device)
       − s_dn · h(1−u) · min(1,    v /x_lin)        ← discharging (pull-down device)

h(x)  = clip((x − vt)/(1 − vt), 0, 1) ** p
```

### Two terms, one per device

A CMOS stage has a PMOS on top and an NMOS on the bottom. **The two terms are those two devices**,
not two directions of a single one.

- The **first term charges** `v` upward. Its gate factor is `h(u)` — it grows as the input rises.
- The **second term discharges** `v` downward. Its gate factor is `h(1−u)` — it grows as the
  input **falls**.

Because `h` clips to zero below `vt`, at a settled input only one term is alive:

| input `u` | `h(u)` | `h(1−u)` | result |
|---|---|---|---|
| 1 (high) | 1 | 0 | charging only, `v → 1` |
| 0 (low) | 0 | 1 | discharging only, `v → 0` |
| mid | see below | see below | depends on `vt` |

That middle row is the case a short pulse creates and a full transition never shows you. It is
exactly where the model has to be right and exactly where the file carries no information — so it
is worth being precise about what the law actually does there.

**Both terms are alive only when `vt < u < 1 − vt`.** That interval is non-empty only if
**`vt < 0.5`**. Above that the two live regions stop overlapping and a **dead band** opens around
mid-input where *both* terms are zero and the stage simply **holds** its output.

| fitted `vt` | behaviour at mid-input |
|---|---|
| `vt < 0.5` | the two terms overlap and fight; net drive is the difference |
| `vt ≥ 0.5` | dead band of width `2·vt − 1`; the stage freezes until the input clears it |

This is not hypothetical: ex2's file-only fit lands at **`vt = 0.528`** and inv_weak at **0.524**,
both of which open a dead band — 5.6 % and 4.8 % of the swing wide. A stage that freezes
mid-input is a real mechanism for extinguishing a short pulse (§7.3), not a fitting artefact, but
it is the model's behaviour and not a device's.

### `h(x)` — the gate factor

```
h(x) = clip((x − vt)/(1 − vt), 0, 1) ** p
```

Reading it left to right:

1. **`x − vt`** — the stage delivers nothing until its input passes `vt`. Below threshold, zero.
2. **`/(1 − vt)`** — rescale so that a full-rail input gives exactly 1. Keeps `s_up` meaning
   "the slope at full drive" regardless of where `vt` sits.
3. **`clip(…, 0, 1)`** — no negative drive, and no extra credit above the rail.
4. **`** p`** — the curvature between threshold and full drive.

### `min(1, (1−v)/x_lin)` — the drain factor

This is the **current source / resistor** switch:

```
1 − v  >  x_lin   →  min() = 1        far from the rail: full slope, output is a RAMP
1 − v  <  x_lin   →  min() < 1        close in: slope tapers linearly to zero at the rail
```

`x_lin` is the width of the tapering zone, as a fraction of the swing. With `x_lin = 0.45`:
the stage drives at **full slope for the first 55 % of its travel**, then eases off over the last
45 %.

The discharging term mirrors it with `v` in place of `1 − v`, since "distance to the rail" is now
distance to zero.

### The four (five) numbers

| symbol | what it is | units | where its value comes from |
|---|---|---|---|
| `s_up` | slope while charging at full drive | swings/ns | fitted to the file's full-swing Ku(t) |
| `s_dn` | slope while discharging at full drive | swings/ns | the same fit |
| `vt` | where the stage hands over — **an effective parameter, not V_th** | normalised | fitted, then **recalibrated** on the stressed run |
| `x_lin` | width of the tapering zone near the rail | normalised | **held at 0.45** on 10 of 12 buffers |
| `p` | curvature of the gate factor | — | **assumed = 1**; invisible at full swing |

All K stages in a chain share one set of these. "Identical" means identical **normalised
dynamics** — not identical transistor dimensions, which a real tapered predriver deliberately
varies.

---

## 4. Why this shape — the transistor, term by term

This section is the "why is the equation valid" part. The short answer: **a real device's current
already factors into a gate term times a drain term, and the stage law has the same factored
shape with three specific simplifications.**

### 4.1 A real device factors — exactly

For SPICE Level 1 (Shichman–Hodges) across both conducting regions, write `r = V_DS / (V_GS − V_th)`
— the drain voltage normalised by the overdrive. Then:

```
I / I_sat  =  q(2 − q),      q = min(r, 1)        ( equivalently 1 − (1 − q)² )
```

**The clamp goes on `r`, not on the result.** `r(2 − r)` is a downward parabola peaking at
`r = 1`, so above saturation it *falls* — 0.75 at `r = 1.5`, 0 at `r = 2`, negative beyond. Writing
it `min(1, r(2−r))` would pick that falling branch and give the wrong current in saturation, which
is where a driving stage spends most of its travel.

This is an algebraic identity, not an approximation: `check_factorisation.py` in
`results/model_provenance_2026-09-25/` verifies it to **4e-16** over 20 000 random `(V_ov, V_DS)`
pairs, **66 % of them in saturation**.

So the standard form really is `[gate term] × [drain term]`, with the drain term saturating at 1.
**That is the stage law's shape.**

### 4.2 The capacitor law gives the ramp

```
C · dV/dt = I
```

A device in saturation delivers a current that does not depend on V_DS. Constant current into a
capacitance is a **constant slope** — the output is a ramp, not an exponential. That is the single
most important structural consequence, and it is why the model is not an RC.

This is literal in the emitted SPICE — a controlled current source driving an explicit capacitor:

```spice
BSTG1 STG1 0 I = -{gate_c} * 1e9 * ( s_up*h(u)*r(1-v) - s_dn*h(1-u)*r(v) )
CSTG1 STG1 0 {gate_c} ic=0
```

*(`stage_block` in `chain_command.py`. The `1e9` converts per-nanosecond to per-second; `gate_c`
cancels out of the resulting `dv/dt` and is there only to make it a real capacitor node.)*

### 4.3 The three departures

| | a real device (Level 1) | the stage law |
|---|---|---|
| gate exponent | `(V_GS − V_th)²` | `(…)¹` — `p = 1` |
| drain factor | `q(2−q)`, `q = min(r,1)` — a parabola into a clamp | `min(1, r′)` — a straight line |
| the normaliser | `r` is divided by the **overdrive**, so the boundary moves with the input | `r′` is divided by a **constant** `x_lin` |

Everything else — off below threshold, saturate above it, taper into the rail, current-into-a-cap
— is the standard behaviour.

### 4.4 Provenance, badge by badge

Badges: **device** = standard device behaviour · **simplified** = same shape, one thing changed ·
**assumed** = a modelling choice with no derivation behind it.

| factor | source | badge |
|---|---|---|
| `C dV/dt = I`, saturated current independent of V_DS → a ramp | the capacitor law + standard saturation | **device** |
| `h(u) = 0` below `vt` | `I_D = 0` for `V_GS − V_th < 0` | **device** |
| `h(u)` above `vt` | a real device squares it; `p = 1` here | **simplified** |
| `min(1, (1−v)/x_lin)` | the real taper is the parabola `r(2−r)`; a straight line here | **assumed** |
| `x_lin` held at 0.45 | a real device's zone is 0.77–0.89 of the swing (§5) | **assumed** |
| boundary at constant `x_lin` | a real device's boundary is `1−v = u−vt`, which **moves with the input** | **assumed** |
| K identical stages | nothing — a modelling choice, evidenced only by the fit | **assumed** |
| one shared `s_up` across every stage | in normalised coordinates the *charging* term is the PMOS on odd stages and the **NMOS** on even ones (§3), so a single `s_up` asserts the two are equally strong — a **β-ratio assumption** | **assumed** |

### The sources, and exactly what each one covers

A source earns its place only if it maps onto a **specific term**. Four tiers, because they are
not equally solid.

#### Tier 1 — held in this repository, quoted verbatim

`docs/book/` holds Leventhal & Green, *Semiconductor Modeling: For Simulating Signal, Power, and
Electromagnetic Integrity* (Springer 2006) as JSON. Every quote below is checked against
`pages.json`; `py -3.14 scripts/extract_book_json.py --find "phrase"` greps it with page
references. Page numbers are printed page, PDF page in brackets.

**(a) The three-region structure and the two conducting laws** — §3.8.3.4, p.89 [pdf 105],
equations 3-23 to 3-25, transcribed from the OCR:

```
(3-23)  ID = 0                                             for  VGS - VTO < 0
(3-24)  ID = (KP/2)(W/L)(VGS - VTE)^2                      for  0 < VGS - VTO < VDS   [saturation]
(3-25)  ID = (KP/2)(W/L) VDS (2(VGS - VTE) - VDS)(1 + LAMBDA VDS)
                                                           for  0 < VDS < VGS - VTO   [triode]
```

> "A few MOSFET model equations (3-23) through (3-26) are shown for illustration. These equations
> are level 1 and level 2 with terms for gate modulation specifically included…"
> — p.89 [pdf 105]

**This sources four things and no more:** `h = 0` below threshold (3-23) · that the gate factor is
a **power of the overdrive** (3-24) · that a **different law** takes over near the rail, and that
it is a parabola in V_DS (3-25) · and the identity of §4.1, which is just 3-24 and 3-25 divided by
each other.

Two things to notice. The book prints 3-25 **with** `LAMBDA` — channel-length modulation. The
factorisation check drops it, and so does the stage law: without it a saturated device's current
is exactly flat in V_DS, and that flatness is what makes the ramp a ramp. And these are ~0.6 µm
parts, so the long-channel form is itself an approximation for this silicon.

**(b) A caution against treating any of this as device physics** — §20.4.1, p.578 [pdf 583]:

> "All so-called physical models (Ebers-Moll [34], Shichman-Hodges [109]) are actually
> macromodels when compared to the device physics formulations."

This one matters more than it looks. **Even Level 1 is a macromodel.** The stage law is therefore
a reduced-order model *of a macromodel*, and citing Level 1 buys structure, not authority. It is
the book's own warning against the overclaim §4.5 avoids.

**(c) Explicit sanction for modelling the pre-driver at reduced detail** — §20.5 and §20.5.1,
p.580 [pdf 585]:

> "But complex I/O requires some modeling of the buffer internal behavior. A new balance between
> simulation speed and I/O internal modeling will have to be devised."

> "The black-box model can simplify the physical model of the output stage so that we can model
> driver and pre-driver at a less detailed level."

That is the closest thing in the literature we hold to a description of the job track 1 is doing.

#### Tier 2 — the primary source, cited by the book, not held here

Level 1 is not the book's; the book restates it. The original is

> H. Shichman and D. A. Hodges, "Modeling and Simulation of Insulated-Gate Field-Effect
> Transistor Switching Circuits," *IEEE Journal of Solid-State Circuits*, SC-3, 1968.

— bibliography entry [109], p.740 [pdf 742]. **We hold the restatement, not the paper.** Cite the
book, which is what was actually read.

#### Tier 3 — an outside reference that genuinely connects, not verified against a copy

**For `p`, the gate exponent — the α-power law:**

> T. Sakurai and A. R. Newton, "Alpha-Power Law MOSFET Model and its Applications to CMOS Inverter
> Delay and Other Formulas," *IEEE Journal of Solid-State Circuits*, vol. 25, no. 2, pp. 584–594,
> April 1990.

It replaces (3-24)'s square with `I_D ∝ (V_GS − V_th)^α`, with `α` running from 2 (long channel)
down toward 1 as velocity saturation takes over. **That is exactly the `p` in `h(x)`** — same
position, same role — so the connection is structural rather than decorative, and it is why
`p = 1` is a defensible end of a documented range instead of merely a convenience.

**Status: not verified in-repo.** `docs/book/` contains neither "Sakurai" nor "velocity
saturation" (checked 2026-09-28), so this is outside knowledge and nobody here has checked it
against the paper. **Treat it as a lead, not as evidence**, until someone does.

#### Tier 4 — no source, and none is claimed

| term | status |
|---|---|
| `min(1, ·)` in place of the parabola | **no source.** A straight line, chosen for simplicity; §4.6 measures what it costs |
| `x_lin` constant, not the overdrive | **no source.** A real boundary moves with the input |
| `x_lin = 0.45` | **no source.** It sits inside the 0.37–0.63 the real probed stages fitted (§5) — which is evidence, not derivation |
| K identical stages | **no source.** Evidenced only by the fit (§7) |
| one shared `s_up` (the β-ratio assumption) | **no source** |
| the hard threshold in `h` | **no source.** Silicon rolls off continuously (§7.3) |

**Roughly half the equation has a reference and half does not.** That is the honest summary, and
it is why §4.5 calls this a physically motivated reduced-order model rather than a derivation.

#### What would close the gaps

* **`p`** — read Sakurai–Newton, then re-fit with `--p` (already a flag) against the stressed
  runs, which *can* see `p` where full swing cannot (§9).
* **the taper** — swap `min(1, r')` for the device form `q(2−q)`, `q = min(r,1)`, normalised by the
  overdrive `(u − vt)` instead of by a constant. It is the shape (3-25) actually gives, it costs
  **one parameter fewer** because `x_lin` disappears into `vt`, and it has never been tried.
* **`x_lin`** — pinned or fitted, not both (§9).

### 4.5 What kind of model this is

**A physically motivated reduced-order model — not a model derived from device physics.**

The physics tells us to expect a current-limited phase followed by a resistive approach to the
rail, and that prior is real and useful. It does **not** hand us the `min()`, the straight taper,
the fixed `x_lin`, `p = 1`, the hard threshold, or K identical stages. Those are architecture
choices, and the case for them is §8 — the measured result — not the derivation.

### 4.6 The taper comparison, done correctly

An earlier write-up said "half way into the region a real device passes 0.75 and we pass 0.50,"
implying the model is weak near the rail. **That comparison is invalid**, because the two
normalise `r` by different things — a device by its overdrive, the stage law by a constant.

Done properly, at full gate drive on a 3.3 V part (`compare_taper.py`):

| `v` | a real device | the stage law |
|---|---:|---:|
| 0.30 | 0.959 | 1.000 |
| 0.50 | 0.815 | 1.000 |
| 0.70 | 0.567 | 0.667 |
| 0.90 | 0.215 | 0.222 |
| 0.99 | 0.023 | 0.022 |

A real device gives up its constant current at **v = 0.12**; the stage law holds to **v = 0.55**.
Integrated over the travel the stage law delivers **1.095×** the *average current*. **It is
*more* current-source-like than long-channel theory, not less** — the opposite of the old claim.

*(Not 1.095× the charge: the charge moved is `C · swing` either way, since both traverse the same
0 → 1. `compare_taper.py` integrates the normalised drain factor over `v`, so the ratio is of mean
drive — which is to say the stage law crosses its swing faster, not further.)*

There is a favourable post-hoc reading of `x_lin = 0.45`: a device's boundary sits at
`1 − v = u − vt`, so 0.45 is where a real one lands at about **57 % gate drive**. The constant is
right for a *partly*-driven stage and too generous for a fully-driven one — and a stressed pulse
is precisely the partly-driven case. Nobody chose 0.45 for that reason. Separately, velocity
saturation in real short-channel silicon extends the constant-current region, moving real silicon
toward the model — a hypothesis, not a measurement.

---

## 5. Why `vt` and `x_lin` are not device quantities

The names invite the wrong reading, so state it plainly.

**`x_lin` is not the saturation/triode boundary.** A real device leaves saturation at
`V_DS = V_GS − V_th`, so at full drive the resistive region occupies `1 − V_th/V_DD` of the swing.
Using `VTH0` from `buffers/models/hspice.mod`:

| | a real device | the stage law |
|---|---|---|
| 1.8 V parts | 0.77 (NMOS) / 0.80 (PMOS) | **0.45** |
| 3.3 V parts | 0.88 (NMOS) / 0.89 (PMOS) | **0.45** |

**And it is not even fitted.** Across all `step1` fit rows, **360 of ~390 have `x_lin = 0.45`
exactly** — the fitter is handed it as a fixed constant on every pass that produces a shipped
number. In the one pass where it is left free it lands anywhere between **0.02 and 1.50**: the
full-swing data barely constrains it.

What makes 0.45 defensible is not theory but measurement: fitting the *real probed stages*
individually gave **0.37–0.47** on ex2's three and **0.52–0.63** on inv_chain's. 0.45 sits inside
that range.

**`vt` is not the device threshold.** Fitted values at each buffer's best K:

```
ex2 0.029   ex2_base 0.015   ex2_nomiller 0.033   ex2_skewp 0.022
ex2_slowpre 0.062   ex2_weak 0.029   inv_base8 0.325   inv_chain 0.447
inv_skewp 0.077   inv_stage4 0.018   inv_weak 0.524   io_buf 0.432
```

Range **0.015 to 0.524**, against a physical `V_th/V_DD` of 0.11 (3.3 V) or 0.20 (1.8 V). It is an
effective hand-over point, and the stressed-run calibration overwrites it anyway.

**And `vt` is not even stable across passes of the same buffer.** The list above is the `est_knee`
pass at each buffer's best K; ex2 sits at **0.029** there and at **0.528** in the `as_track1`
K = 3 build of §6.4 — half a swing apart, at near-identical fit quality (Ku-domain rms 0.0215 vs
0.0233). Different C_comp, different map, wildly different `vt`, same curve reproduced. Note that
0.528 falls *outside* the range quoted above, because that range is one pass and not a property of
the buffers.

That is not a contradiction to explain away. It is the §7.1 degeneracy showing up in a second
parameter: **`vt` is essentially unidentified by the file.** Which is precisely why the recipe
spends its one stressed run recalibrating it (S5).

**`vt` is also not the file's `Vinh`/`Vinl`.** Those are the input **pin's** thresholds, used by
the converter for the input comparator. `vt` is an *internal* stage's threshold and the file says
nothing about it.

---

## 6. How Ku is constructed from the model

This is the heart of it. The model never produces Ku directly — it produces a **gate**, and Ku is
what you get by reading the gate through the map.

### 6.1 The four steps

```
   input pin
      │  ① comparator at mid-supply
      ▼
   u(t)  ∈ {0, 1}
      │  ② K identical stages, each integrating the stage law
      ▼
   g(t) = V(STG_K) = GUP          ← the gate trajectory. NOT observable from the file.
      │  ③ the static map
      ▼
   Ku_model(t) = map(g(t))        ← this IS comparable to the file
      │  ④ into the file's own I-V tables
      ▼
   pad current
```

**① The input.** In the built model, `BCHIN CHIN 0 V = (V(IN,VSS) > 0.5·sup) ? 1.0 : 0.0` — a
mid-supply comparator on the input pin. *In the fit* (§6.3) the chain is instead driven by an
ideal 10 ns box starting at `t_on = 5.0 ns + edge/2`. Worth knowing: the fit sees a perfect step,
the built model sees a comparator output.

**② The chain.** `simulate_chain` applies `simulate` K times, each stage taking the previous
stage's output as its `u`. The integrator is **Heun (RK2) with 1 ps substeps**, not explicit Euler:

> Explicit Euler at 2 ps biased inv_chain's fast stages (τ ≈ 20 ps) enough that the Python chain
> passed a 119 ps pulse the same chain in ngspice swallowed. Heun agrees with ngspice.

Each stage's state is clipped to `[−0.05, 1.05]`.

**③ The map.** A static, MOSFET-shaped curve from gate to Ku:

```
map(g) = clip((g − vt_map) / (gs − vt_map), 0, 1) ** α
```

with `gs = 1` in the two-parameter form. `vt_map` is where the output device starts conducting;
`α` is the curvature; `gs < 1` lets Ku reach 1 before the gate reaches its rail, which the real
maps do.

**Note that `vt_map` and `α` are a different pair from the stage law's `vt` and `p`.** Same
shape, different job: `vt`/`p` shape the *stage*, `vt_map`/`α` shape the *output device's*
turn-on. Confusing the two is easy and fatal.

**④** The Ku multiplies the file's own fully-on I-V table. That part is unchanged from the
shipped converter.

### 6.2 What "actual Ku" is, exactly

The target is **not** a hand-derived curve. It is a probe node:

```
v(x1.kugate_base)   from a full-swing ngspice run of the SHIPPED pybis2spice subcircuit
```

*(`gp.run_ours(mdir/"shipped/full", ship, sup, 10.0)`)*

Precisely: **the gate-driven part of Ku, direction-selected, with the residual transient
excluded.** In the gate-state subcircuit, `KUGATE_BASE` picks between the `KUGATE_ON` and
`KUGATE_OFF` tables according to whether the gate is still chasing its target, and the separate
`kures_table` residual is *not* included.

So the comparison is **model Ku against the file's Ku**, both on the same footing — and the file's
Ku is itself the product of the IBIS I-V tables and V-T waveforms as the existing converter
solves them. The stage law is not being compared against silicon here. It is being fitted to
reproduce what the file already says.

Both sides are normalised rest → on before comparison:

```python
k_rest = Ku at 4.5 ns          # settled low
k_on   = Ku at 12.0 ns         # settled high
target = clip((kb − k_rest)/(k_on − k_rest), 0, 1)
```

### 6.3 The fit

`fit_chain_ku` in `gate_chain_prototype.py`:

| | |
|---|---|
| **cost** | `rms( map(simulate_chain(u, prms)) − target )` |
| **grid** | 4.0 → 21.0 ns at **2 ps** |
| **free numbers** | 3 (`s_up`, `s_dn`, `vt`) with `x_lin` pinned; 4 if free |
| **optimiser** | Nelder–Mead, 3 restarts at `s0 = 2, 8, 30`, maxiter 800 |
| **bounds** | `0 ≤ vt ≤ 0.7`, `0.02 ≤ x_lin ≤ 1.5` |
| **repeated** | once per candidate K |

Look at where the comparison happens: **in the Ku domain, not the gate domain.** That is forced,
not chosen — the gate is not observable from a file. The model's gate is pushed through the map
and only then compared. The immediate consequence is that **the map shape must be fixed before
the fit runs**, because otherwise map and gate trade off against each other exactly as in §1. In
the recipe that is S4, the shape grid.

**The pull-down needs its own domain.** For an open-drain part, fitting the pull-down in the Ku
domain leaves its onset unconstrained: the Ku-domain target is zero wherever `g < vt`, which is
exactly where Kd turns on. Measured **250 ps early** on the open-drain parts (`opendrain`,
`od_slowpre`, `od_weak` — open-drain buffers built from ex2, a separate line of work; ex2 itself
is push-pull). Hence `which="kd_map"`,
which fits Kd through its own map with `GDN = 1 − GUP`.

### 6.4 A worked example — ex2, file-only

The build `ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810`:

| | |
|---|---|
| map shape | `(vt_map 0.57, α 0.64)` — see the caveat below |
| K | 3 |
| fitted in the Ku domain | `s_up` **2.190** · `s_dn` **2.124** · `vt` **0.528** · `x_lin` **0.45 (fixed)** |
| Ku-domain rms | **0.023** |
| then calibrated | `vt` 0.528 → **0.487** on the one stressed pad run |

Three free numbers, fitted to a curve the file already contains. The stressed run is not spent
here — it is spent on the single `vt` bisection in the last row.

> **Two traps, both from the same correction**
> (`results/track2_train_check_2026-09-13/FINDINGS.md`, 2026-09-18 entry):
>
> **1. `2.590 / 2.375 / 0.512 / 0.658` are not these numbers.** Those appear in the 09-17
> animation and behind `track1_recipe.md`'s "ex2 fits 2.59/ns". They are the **`--source real`**
> fit — stages fitted to the *probed* gate n4, which needs the transistor. The file-only fit is
> the table above.
>
> **2. This build is not fully file-only either.** Its map shape `(0.57, 0.64)` is ex2's
> *measured-curve* fit. "File only" holds for the stages and the threshold, **not** for the two
> shape numbers. The strictly file-only pass (`step1`, `file_only`) uses the universal
> `(0.5, 0.7)` instead and fits `s_up`/`s_dn`/`vt` against that — different numbers, same
> procedure. Check which pass a figure came from before quoting it.

---

## 7. What the Ku comparison can decide — and what it cannot

This is the part that shapes the whole recipe, so it is worth seeing the raw numbers.

### 7.1 It constrains the rate. It does not constrain K.

Ku-domain fit rms for K = 1 … 10, each K independently fitted
(`results/stage_count_from_file_2026-09-21/step1_summary.csv`, `as_track1` pass):

| buffer | K=1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | netlist K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ex2 | .0829 | .0292 | .0233 | .0224 | **.0215** | .0222 | .0235 | .0255 | .0274 | .0294 | **3** |
| inv_chain | .0468 | .0216 | .0141 | .0108 | .0076 | .0071 | **.0070** | .0072 | .0072 | .0074 | **7** |
| io_buf pull-up | **.0176** | .0264 | .0500 | .0639 | .0724 | .0783 | .0825 | .0858 | .0883 | .0904 | **1** |

Read ex2's row. K = 1 genuinely fails — you cannot make a 1.1 ns delay with a 660 ps edge out of
one stage. After that the curve is **flat**: K = 3 through K = 6 all sit within 0.002 of each
other, and the minimum is at **K = 5** while the netlist has **3**.

inv_chain is worse: K = 6, 7, 8, 9 differ in the fourth decimal.

Taking the single best-fitting K recovers the netlist count on **2 of 13 chains** in this pass —
inv_chain and io_buf's pull-up.

**But the count is the wrong statistic.** Look instead at the **margin** between the best K and
the runner-up:

| chain | best K | netlist K | margin to runner-up |
|---|---:|---:|---:|
| ex2 | 5 | 3 | 0.0007 |
| inv_chain | 7 | **7** | 0.0001 |
| io_buf pull-up | 1 | **1** | **0.0088** |

Across all thirteen chains in this pass the margin is **0.0000–0.0007 on twelve of them**, and
0.0088 on the thirteenth. **io_buf's pull-up is the only row with a real minimum** — it genuinely
is one stage. inv_chain landing on 7 is a coincidence decided in the fourth decimal; the same fit
on the `est_knee` pass puts it at 8.

*(The recipe's "1 of 13" is a different statistic: `pick_K`, the smallest K within 5 % of the
best, which is the rule the band is built on. Argmin and `pick_K` disagree, and both are
arbitrary at these margins — which is the point.)*

**So the file's Ku(t) constrains how fast the gate moves, and barely constrains how many stages
move it.** That is not a defect in the fit. It is the §1 degeneracy showing up quantitatively: many
trajectories reproduce the same product.

The recipe's response is S3 — take the **three smallest K within 25 % of the best rms** as a band,
and let the stressed run choose inside it. The band contains the netlist count on all 12 buffers.

**Doesn't that spend one observation on two unknowns?** K and `vt` are both settled by the same
single stressed run, which looks like it should be degenerate — and `vt` and K trade off exactly
the way the chain makes easy (a later hand-off and a shorter chain both pass more pulse). The
recipe's answer is that the two are read off **different features of the same waveform**:

| | uses | from that run |
|---|---|---|
| S5 calibrates `vt` | the **peak** at the calibration width | bisected until it matches |
| S6 selects K and the shape | the **whole waveform**, peak already matched for every candidate | rms over the pulse + 1.5 ns of return |

Because S5 has forced the peak to match at that width for *every* candidate, the peak carries no
information left for S6 — so K is chosen on shape, not amplitude. That is measured, not asserted:
ranking candidates by stressed peak instead of by waveform gives **217.3 mV** mean waveform error
against **52.3 mV** for the waveform rule, and lags of +155…+300 ps against −27…+17 ps
(`track1_recipe.md` S6).

It is still two unknowns from one run. The claim is only that they are not reading the same
number.

### 7.2 A free fit is not just uninformative — it is actively wrong

Fit K stages to ex2's full swing with **all 4K parameters free**
(`current_limited_stages_2026-09-10/ex2_chain_K.csv`). **Gate-domain** rms here — against the
probed gate n4, not against Ku, so these numbers are not comparable with §7.1's:

| K | full-swing rms | predicted stressed gate, deepest width | measured |
|---:|---:|---:|---:|
| 1 | 0.0816 | 0.408 | 0.758 |
| 2 | **0.0046** | **0.228** | 0.758 |
| 3 | 0.0042 | 0.809 | 0.758 |

K = 2 is **numerically excellent at the thing it was fitted to** and physically worthless. It
split the delay into one very slow stage plus one fast one — and a slow stage with a threshold
swallows short pulses. inv_chain's K = 2 and 3 free fits found the same corner (`x_lin` 0.02, a
ramp-to-threshold delay dressed up as a stage) and predict **exactly zero**.

This is why the stages are constrained to be **identical**. It removes the degenerate corner and
leaves one structural number, K, for the stressed run to pick.

### 7.3 Why a chain extinguishes rather than attenuates

Each stage needs its input past `vt` before it delivers anything. A short pulse therefore loses a
little at every hop, and once it drops under the threshold **nothing continues at all**. That is
why K is a first-order parameter and not a refinement — and it is exactly why io_buf's pull-down
chain is inert on short pulses: its stages each want 0.7 of the swing, so a 163–322 ps pulse dies
in the first one and GDN never rises.

**Two caveats on that 0.7.**

* **It is the optimiser's ceiling, not a free landing.** The fitter bounds `vt` to `[0, 0.7]` and
  the fit returned **0.699999**. Its own study reads that correctly: *"a sign the full-swing fit
  wanted something it was not allowed to have"*
  (`results/io_buf_pulldown_calib_2026-09-23/FINDINGS.md`). An active bound is not a measurement,
  and it should never be quoted as one.
* **It does not contradict §8's "io_buf is linear end to end".** Those are different stimuli:
  the linearity was measured on **short HIGH** pulses at **1505–2354 ps**, the extinction on
  **short LOW** at **163–322 ps** — opposite direction, an order of magnitude apart in width. The
  pull-up path is linear over the widths tested; the pull-down dies at widths an order of
  magnitude shorter.

*Honest qualifier:* that hard extinction is the **model's** threshold. In silicon the current falls
off continuously and a short pulse degrades stage by stage until it is gone. The extinction is
real; the abruptness is the model's.

---

## 8. The validity test — full swing in, stress out

Everything above is motivation. This is the evidence, and it is the only reason to believe the
equation.

**The test:** fit the stages **at full swing only**, then drive them with a *measured stressed
input* and compare against the *measured stressed output*. **No stressed data anywhere in the
fit.**

> ### What this section does and does not show
>
> The fits below are **gate-domain**: K identical stages fitted to the **probed transistor gate**
> (`fit_chain_shared(full[input_pin], full[gate_node], K)`). That is the `--source real` path of
> §6.4's first trap — **it needs the transistor.** So what §8 establishes is:
>
> **the stage law's *shape* extrapolates** — a family fitted at full swing to the true gate
> predicts the stressed gate, where the linear families do not.
>
> It does **not** establish that §6's *file-only pipeline* extrapolates, because that pipeline
> never sees the true gate: it fits in the **Ku domain** through an **assumed map**, then
> recalibrates `vt` on the stressed run. The evidence for that is the end-to-end pad result —
> **12 of 12 within ±10 %** (`track1_recipe.md` §7) — and that one is not held out either: its
> calibration width (810 ps on ex2) is one of the five widths scored.
>
> Keep the two apart. **§8 is why the family is the right family; the end-to-end number is why
> the pipeline built on it works.** Neither substitutes for the other.

### ex2 — 3 identical stages, input pin to output gate n4

| width (ps) | 810 | 830 | 858 | 895 | 975 |
|---|---|---|---|---|---|
| **measured** | 0.758 | 0.797 | 0.838 | 0.880 | 0.936 |
| **stage law, K=3** | **0.755** | **0.782** | **0.813** | **0.847** | **0.898** |
| linear superposition | 0.926 | 0.932 | 0.940 | 0.951 | 0.968 |

Within **0.05 everywhere on ex2**. Linear superposition is off by **0.17** at the deepest width.
Gate-domain rms: full-swing 0.0066, stressed 0.012 (stage law) against 0.069 (linear).

And K matters, exactly as §7 predicts: K = 2 gives 0.287 … 0.520 — it swallows the pulse.

### inv_chain — 7 identical stages

| width (ps) | 104 | 106 | 111 | 119 | 135 |
|---|---|---|---|---|---|
| **measured** | 0.879 | 0.935 | 0.972 | 0.992 | 1.003 |
| **K = 7** | **0.672** | **0.820** | **0.909** | **0.960** | **0.987** |
| K = 5 | 0 | 0 | 0 | 0 | 0.869 |
| K = 3 | 0 | 0 | 0 | 0 | 0 |

**inv_chain does not meet ex2's 0.05.** K = 7 is off by **0.21** at 104 ps and 0.115 at 106 ps,
converging to 0.016 at the shallowest. What it gets right is that the pulse *survives at all* and
in the right order — which is the thing that decides the pad.

Now read the full-swing rms for those three: **0.0032 (K=7) · 0.0037 (K=5) · 0.0141 (K=3)**. K = 5
is within 16 % of K = 7 at the thing the file can see, and **swallows four of the five stressed
pulses**. The file supplies a band; only the stressed run can choose inside it.

### The control that makes it a real test

On **io_buf**, which is linear end to end, the linear structures are *exact*. So the
non-linearity the stage law captures is a genuine, buffer-specific property — not a fitting
artefact. RC cascades, delay + RC, and superposition of step responses are all ruled out on ex2
and inv_chain, and the shipped model is built from exactly those.

### The structural point underneath

A current-limited ramp and an RC that reaches the same point at the same time **differ only in
between**. Endpoints agreeing while interiors differ is the §1 argument one level down — and it is
why the gate's *shape*, not just its timing, is what a truncation sees.

---

## 9. What is assumed, and still open

| | |
|---|---|
| **`p = 1` is an admission, not a claim.** | At full swing the stage input is always at the rail, so every `p` from 1 to 2 fits to rms 0.002–0.007. The fit **cannot** choose, and 1 is taken. `p` acts only under a *partial* input — precisely what a truncation can see and the recipe already samples. An open gap. |
| **But `p = 1` may be closer to the silicon than `p = 2`.** | The square law is the *long-channel* form. In short-channel devices velocity saturation flattens the exponent — the alpha-power law (Sakurai–Newton) puts it nearer 1.2–1.5 — so on ~0.6 µm parts `p = 1` is plausibly the better approximation, not merely the convenient one. **Not verified in-repo:** the book JSON in `docs/book/` contains neither the alpha-power law nor velocity saturation, so this is an outside reference and a hypothesis, like the velocity-saturation note in §4.6. It would be cheap to test, since `--p` is already a flag. |
| **The linear taper is the biggest liberty.** | A parabola replaced by a straight line. §4.6 shows it errs toward *more* current, not less. |
| **`x_lin` is inconsistent.** | Pinned at 0.45 on ten buffers, fitted on inv_chain and io_buf. Defensible (inside the measured 0.37–0.63) but it should be one or the other. |
| **K identical stages has no derivation.** | Only the fit evidences it. A real tapered predriver has deliberately *different* devices; the claim is that their **normalised dynamics** are similar. |
| **The map shape grid saw the answer key.** | `(0.40, 0.60)` and `(0.40, 0.90)` are the two best of an earlier grid run on these same 12 buffers. A thirteenth may need a shape the grid does not contain. |
| **So did the S3 band rule.** | "The three smallest K within 25 %" was chosen on these same 12 buffers. "The band contains the netlist K on all 12" therefore carries the same answer-key caveat as the shape grid — it is a property of a rule tuned until it did, not an independent result. |
| **The rms window was chosen once.** | The pulse plus 1.5 ns of its return, never tuned. The one untested free choice in the selection rule. |

---

## 10. One-page summary

1. IBIS gives **Ku(t) = map(gate(t))** — a product. A truncated pulse depends on the **factors**.
2. The file cannot factor it, so a **prior on gate trajectories** is needed. That is the stage law.
3. The law says: **off below threshold, constant slope while there is headroom, taper into the
   rail.** Two terms, one per device.
4. `u` = \|V_GS\|/swing, `1 − v` = \|V_DS\|/swing, `dv/dt` is **swings per ns**.
5. A real device's current factors as `q(2−q)` with `q = min(r, 1)` — the **same shape**, verified
   to 4e-16. (The clamp is on `r`; `min(1, r(2−r))` is a different and wrong function above
   saturation.) The departures are the exponent (1 not 2), a straight taper (not a parabola), and
   a constant `x_lin` (not the overdrive).
6. **Ku is constructed** by driving K identical stages from a comparator, taking the last stage's
   output as the gate, and reading it through a static map. **Ku_model is compared against
   `kugate_base` from the shipped model's full-swing run**, rms over 4–21 ns at 2 ps.
7. That comparison **fixes the rate and barely constrains K** — within **0.002** across K = 3…6 on
   ex2, and the best-to-runner-up margin is **0.0007 or less on twelve of thirteen chains**. Only
   io_buf's pull-up has a real minimum. `vt` is unidentified the same way (§5).
8. So: **identical stages** kill the degenerate corner, a **band** of K survives the file, and the
   **one stressed run** picks inside it.
9. Two separate claims, both needed. **The family is right:** fitted at full swing to the *probed*
   gate, it predicts ex2's stressed gate to within 0.05 where linear superposition is off by 0.17
   (§8 — this uses the transistor). **The file-only pipeline works:** 12 of 12 within ±10 % at the
   pad (`track1_recipe.md` §7). §8 does not prove the second.
10. It is a **physically motivated reduced-order model**. The results stand on the measurements,
    not on the derivation.
