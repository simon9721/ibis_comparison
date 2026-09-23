# The track-1 recipe

*2026-09-23*

How a stress-surviving model is built from an IBIS file plus **one** stressed pad run, with no
internal probing.

The model is not a curve fit that happens to work. It is a physical picture of the buffer, and
every part of it was measured on the real transistors before it was put in. Sections 1 and 2
are those measurements; sections 3 to 5 are the recipe, and each step cites the measurement
that forces it.

Studies: `results/gate_physics_2026-09-08`, `results/predriver_stages_2026-09-09`,
`results/current_limited_stages_2026-09-10`, `results/stage_count_from_file_2026-09-21`,
`results/ccomp_from_file_2026-09-22`, `results/selector_from_one_run_2026-09-23`.
Waveforms: `results/track1_summary_2026-09-23/WAVEFORMS.md`.

---

## 1. The three measurements the model stands on

Everything below follows from these. They were made by probing the real transistors, once, so
that the model built afterwards needs no probing.

### M1 — Ku really is a static map of the gate

Probe the predriver's output node on the real transistor, then plot the solved Ku against that
gate voltage. If Ku is a genuine function of the gate, the rising and falling branches lie on
top of each other. Measured hysteresis, |Ku_rising − Ku_falling| at matched gate voltage:

| buffer | gate node | hysteresis | reading |
|---|---|---:|---|
| io_buf | n2 | 0.07 - 0.11 | single-valued |
| inv_chain | vout7 | 0.09 - 0.10 | single-valued |
| ex2 | n4 | 0.47 - 0.75 → **0.09** once C_comp is corrected | single-valued |

**Why this matters more than anything else here.** It says the output stage has no memory of
its own: whatever the gate is doing, Ku follows it instantly through a fixed curve. So a model
of a stressed buffer has exactly **two** jobs — get the gate trajectory right, and get the
gate→Ku curve right. Nothing else. The whole recipe is those two jobs.

*(It also says where our model was wrong: the map architecture was fine all along, the gate
dynamics were not.)*

### M2 — A predriver stage is a current source with a threshold

`predriver_stages_2026-09-09` measured that ex2's and inv_chain's stages **under-reach** what
linear superposition predicts, and **return early**. The physical explanation is ordinary MOS
behaviour: a CMOS inverter driving a large load is a **current source** while its input sits at
the rail (its driving transistor is in saturation) and becomes a **resistor** only near the
destination rail (the transistor enters triode). That picture is the stage law, term for term:

```
   dv/dt =  s_up · h(u)   · min(1, (1−v)/x_lin)        charging
          − s_dn · h(1−u) · min(1, v/x_lin)            discharging
            ^^^^   ^^^^     ^^^^^^^^^^^^^^^^
            |      |        └─ saturation gives way to triode near the rail
            |      └─ drive follows the input, through the inverter's switching threshold
            └─ constant current: the output is a RAMP
```

**The test that put it in.** Fit each real stage **at full swing only**, then drive it with its
*measured stressed input* and compare against the *measured stressed output*. No stressed data
in the fit.

| | ex2's output gate n4, through 3 stages from the input pin |
|---|---|
| measured, 5 widths | 0.758 / 0.797 / 0.838 / 0.880 / 0.936 |
| current-limited chain | 0.755 / 0.782 / 0.813 / 0.847 / 0.898 — **within 0.05 everywhere** |
| linear superposition | 0.926 at the deepest width — **off by 0.17** |
| rms, deepest width | 0.012 current-limited · 0.069 linear |

Each inv_chain stage is predicted to rms 0.003. And on **io_buf**, which is linear end to end,
the linear structures are exact — so the non-linearity is a real, buffer-specific property, not
a modelling preference.

**What this rules out:** RC cascades, delay + RC, and superposition of step responses cannot
represent ex2 or inv_chain. The shipped model is delay + fast RC, which is why it fails.

### M3 — Full swing does not pin the internal structure, and stress depends on nothing else

Fit K stages to ex2's full swing with all 4K parameters free:

| K | full-swing rms | predicted stressed gate | measured |
|---:|---:|---:|---:|
| 2 | **0.005** (excellent) | **0.23** | 0.76 |
| 3 | 0.004 | **0.81** | 0.76 |

The K = 2 fit is *numerically better at the thing it was fitted to* and physically worthless: it
split the buffer's delay into one very slow stage plus one fast one, and **a slow stage with a
threshold swallows a short pulse**. inv_chain's K = 2 and 3 fits found the same corner (x_lin
0.02 — a ramp-to-threshold delay dressed as a stage) and predict a stressed gate of exactly
zero.

**Why this is the central fact of track 1.** Full swing is blind to the structure, and the
structure is the entire stressed answer. Two fixes follow, and they are the shape of the whole
recipe:

1. **Constrain the structure with physics** — make the K stages *identical*, which is what a
   real tapered predriver approximately is. That makes the fit well-posed.
2. **Choose what remains with a stressed observation**, because nothing in the file can.

---

## 2. What gets built

```
   input ──►[ stage 1 ]──►[ stage 2 ]──► … ──►[ stage K ]──► g ──►[ map ]──► Ku ──► I-V tables
            └───────────── K identical stages ────────────┘
                          (M2, M3)                                (M1)
```

The map, whose form is the output MOSFET's own transfer characteristic — nothing below
threshold, then a power law in overdrive:

```
   Ku(g) = Ku_off + (Ku_on − Ku_off) · clip((g − vt_map)/(1 − vt_map), 0, 1)^α
```

`Ku_off` and `Ku_on` are read from the file; only the interior shape is assumed.

---

## 3. Every parameter, and what breaks without it

| symbol | what it **is**, physically | what goes wrong if it is wrong | how it is set |
|---|---|---|---|
| `s_up` | the stage's charging current | the gate is in the wrong place when the reversal arrives — the entry level | FITTED |
| `s_dn` | the stage's discharging current | the gate comes back at the wrong rate — the trailing half of the stressed pulse, and the pad's falling leg | FITTED |
| `x_lin` | where saturation gives way to triode | the stage's approach to its rail is the wrong shape; at `x_lin` = 1 the stage degenerates to an RC, at 0.02 to a pure delay that swallows pulses (M3) | FITTED / pinned 0.45 |
| `vt` | the next inverter's switching threshold | how much of a short pulse survives each hop | FITTED → **recalibrated** |
| `K` | **the number of real gates the pulse must survive** | too few, the pulse passes too easily; too many, it is swallowed entirely | SELECTED |
| `vt_map`, `α` | the output MOSFET's threshold and overdrive law | the gate/map split is wrong, so full swing is right and stress is not (§0) | SELECTED |
| `C_comp` | the pad capacitance the tables were solved with | the Ku tables themselves are inflated — a defect in the file, not the model | RULE |
| `p` | the drive's curvature in overdrive | — **cannot be fitted**: at full swing the input is always at the rail, so every p from 1 to 2 fits to rms 0.002-0.007. It acts only under a partial input. | ASSUMED = 1 |

Two entries deserve their evidence spelled out.

**`x_lin` = 0.45 is not a round number.** Fitting the *real probed stages* individually gave
x_lin 0.37-0.47 on ex2's three stages and 0.52-0.63 on inv_chain's. 0.45 sits inside that
measured range. (inv_chain fits it instead of taking the pin, and lands high — consistent with
its own stages being at 0.52-0.63.)

**`p` = 1 is the velocity-saturated MOSFET.** Fitted freely it lands on 1 for ex2's inner
stages and 1.5-2 for inv_chain's, and the latter under-predicts. It is the one number a
partial-input observation would pin and full swing cannot.

---

## 4. Why K must be *selected* and not *fitted* — the same table, read twice

With the stages constrained identical (M3's fix 1), K becomes the one structural number left:

| buffer | K | full-swing rms | stressed gate, deepest → shallowest | measured |
|---|---:|---:|---|---|
| ex2 | 2 | 0.014 | 0.29 … 0.52 | 0.758 … 0.936 |
| **ex2** | **3** | **0.0066** | **0.755 / 0.782 / 0.813 / 0.847 / 0.898** | 0.758 / 0.797 / 0.838 / 0.880 / 0.936 |
| ex2 | 4 | 0.0072 | 0.78 / 0.80 / 0.83 / 0.86 / 0.90 | — |
| inv_chain | 3 | 0.014 | **0 — pulse swallowed** | 0.879 … 1.003 |
| inv_chain | 5 | 0.0037 | 0 … 0.87 | — |
| **inv_chain** | **7** | **0.0032** | **0.672 / 0.820 / 0.909 / 0.960 / 0.987** | 0.879 / 0.935 / 0.972 / 0.992 / 1.003 |
| inv_chain | 9 | 0.0032 | 0.941 / 0.954 / 0.967 / 0.981 / 0.992 | — |

Read the **full-swing rms** column: K = 7 and K = 9 are identical to four decimals, and K = 5
is close. Read the **stressed** column: K = 5 swallows the deepest pulse and K = 9 passes it
almost intact. The file cannot tell these apart; the stress can, completely.

That is the motivation for S3 and S6 in one table: *the file gives a band, the stressed run
picks inside it.*

Also: K = 1 cannot fit even full swing (rms 0.082 on ex2) — a 1.1 ns delay with a 660 ps edge
needs stages to make the delay out of.

---

## 5. The procedure

### S1 — C_comp

**What it is.** Not a model parameter. It is a number in the file that **the file's own Ku
tables were solved with**, so a wrong value inflates every coefficient downstream. ex2's
declared 5.0 pF inflates its solved Ku to 1.14-1.26 — above 1, which is impossible.

**How we know the true value** (track 2, needs the gate): the solve subtracts `C_comp·dV/dt`,
and dV/dt flips sign between rise and fall, so a wrong C_comp opens a **loop** in Ku-vs-gate.
The C_comp that closes the loop is the one the device has: ex2 **1.70 pF**, stable across five
widths — against a declared 5.0. That is M1's hysteresis, used as an instrument.

**What track 1 does instead** (no gate available): Ku ≤ 1 identically, so keep the declared
value unless it implies Ku > 1, then take the knee.

**Why a rough answer is acceptable.** The stressed peak is not sharp in C_comp once it is in
range: ex2 scores *better* at 2.31 pF than at the measured 1.7, and ex2_slowpre is estimated at
4.65 against a measured 1.7 and still scores 5.4 %. The file's information about C_comp scales
with dV/dt, so a slow buffer carries almost none — ex2_slowpre is the failure case, and it
survives only because of that insensitivity.

### S2 — Fit `s_up`, `s_dn`, `vt`, `x_lin`

**Target:** `map(chain output)` against the file's full-swing Ku(t). Nelder-Mead, 3 restarts,
2 ps grid over 4-21 ns.

**Why this target and no other:** track 1 has no probed gate. The Ku(t) the tables imply is the
only curve that exists.

**Why the stages are identical (one set of 4, not 4K):** M3. A free fit reaches a better
full-swing rms and predicts stress wrong by a factor of three.

### S3 — The stage-count band

**Rule:** the 3 smallest K whose fit rms is within 25 % of the best.

**Why a band, not the best K.** The rms falls steeply, flattens at the true count, then keeps
creeping down past it — so "best rms" lands 1-3 stages high and recovers the netlist count on
**1 of 13 chains**. §4 shows why that residual creep is meaningless and the stress is not.

**What the band delivers:** it contains the netlist count on all 12 buffers.

| buffer | band | netlist K |
|---|---|---:|
| ex2 family, inv_stage4 | 3, 4, 5 | 3 |
| inv_chain | 6, 7, 8 | 7 |
| inv_base8, inv_skewp, inv_weak | 5, 6, 7 | 7 |
| io_buf pull-up / pull-down | 1 / 3, 4, 5 | 1 / 3 |

### S4 — The shape grid

**Grid:** `(0.50, 0.70)` · `(0.40, 0.60)` · `(0.40, 0.90)`.

**Why the shape cannot be fitted.** Ku(t) = map(gate(t)); the file pins the product only. Hand
the S2 fit *any* map and it will find a chain reproducing the same Ku(t) — steeper map with a
slower chain, gentler map with a faster chain, identical full swing either way. The fit is
structurally incapable of choosing. This is M3 again, on the other factor.

**What it cost to learn.** inv_chain sat at 34 %. With the universal shape the chain the fit
found implied a **square** gate where the real one rolls off with pulse width. Choosing the
shape from the stressed run: **5.1 %**, full swing improving with it (54 → 36 mV). The
discharge rate and a faster final stage were both tried first; both were symptoms.

**S3 × S4 = 9 candidates per buffer**, each with its own S2 fit.

### S5 — Calibrate on the one stressed run

**Method:** bisect `vt` over [0, 0.7], 7 ngspice runs, until the model's peak matches the
measured one. Fallback if `vt` cannot bracket: scale `s_up` and `s_dn` together over [0.5, 2.0].

**Why `vt` and not the rates.** The rates were fitted to reproduce the full swing; moving them
breaks it. `vt` changes **when** the chain hands off without changing how fast it runs — it is
the one number that buys stressed amplitude at no full-swing cost.

**Why a calibration is needed at all.** M2's own limit: the stage law is slightly too weak for
an input at 0.85-0.9 of swing, where a real inverter delivers nearly full current, and full
swing cannot see that. Over K stages the deficit compounds. `vt` absorbs it.

### S6 — Select on the same run's whole waveform

**Rule:** smallest rms between model and transistor pad over that pulse and 1.5 ns of its
return.

**Why not the peak.** S5 has just forced the peak to match at that width for **every**
candidate. Measured: adding a peak gate to the rule changes nothing.

**Why not peaks at other widths.** A chain that turns on late still hits the right peak height
with the wrong pulse under it:

| ranked by | mean waveform error over all widths |
|---|---:|
| whole waveform at the calibration width | **52.3 mV** |
| best possible in the grid | 51.7 mV |
| best stressed peak | **217.3 mV** |

**Why selection, rather than one universal correction.** "Stressed" hides three different
mechanisms: io_buf's predriver is itself **truncated** (its gate reaches 0.42-0.63 of supply),
inv_chain's swings **fully every time but arrives late**, ex2's is **speed-limited** and reaches
~70 % whatever the width. Any single fixed correction fits one and misses two.

---

## 6. The result

| | |
|---|---|
| **12 of 12 within ±10 %** | range 3.2 % (inv_stage4) … 10.0 % (ex2_skewp, on the line), mean 6.9 % |
| shipped model, same pulses | 35 - 76 % on 11 of 12 |
| inv_chain, file-only | **5.1 %**, against 25.8 % for the build made from probed silicon |
| selector quality | within **1 %** of the best build the grid contains |

**What it costs:** full-swing pad rms worse than shipped on 10 of 12 (ex2 61 vs 16 mV) · pulse
trains still lost on ex2 and io_buf · io_buf beaten outright (4.0 vs 7.7 %).

---

## 7. What it has been tested on

| axis | covered | not covered |
|---|---|---|
| depth | 50, 60, 70, 80, 90 % of the settled swing | below 50 % |
| direction | short HIGH | **short LOW on 11 of 12** |
| pulses | one | trains |
| load | 50 Ω ∥ 2 pF | anything else |
| corner | Typical | Min / Max, supply, temperature |

---

## 8. What is not yet honestly file-only

1. **The shape grid was chosen from results on these same 12 buffers.** `(0.40, 0.60)` and
   `(0.40, 0.90)` are the two best of an earlier grid run on this set, so S4 has seen the
   answer key. A 13th buffer may need a shape the grid does not contain.
2. **`x_lin` is inconsistent** — pinned at 0.45 on 10 buffers, fitted on inv_chain and io_buf.
3. **`p = 1` is assumed.** It is the one parameter a single partial-input observation would
   pin, and the recipe already takes one stressed run — so this is a gap that could be closed.
