# The track-1 recipe

*2026-09-23*

How a stress-surviving model is built from an IBIS file plus **one** stressed pad run, with no
internal probing. Each step states what it consumes, what it decides, why the decision cannot
be made any other way, and the measurement that shows it.

Studies behind it: `results/stage_count_from_file_2026-09-21` (steps 1-8),
`results/ccomp_from_file_2026-09-22`, `results/selector_from_one_run_2026-09-23`.
Waveforms: `results/track1_summary_2026-09-23/WAVEFORMS.md`.

---

## 0. The problem, in one equation

An IBIS file gives the pull-up's I-V table (current at each pad voltage, fully on) and a V-T
waveform (one complete transition). Dividing one by the other gives **Ku(t)**: the fraction of
the device that was conducting at each instant. That is the only time-dependent quantity IBIS
carries.

A model that survives a truncated pulse needs to know **where the gate was** when the input
reversed. Ku(t) does not record that, because it is a composition:

```
        Ku(t)   =   map( gate(t) )
        ^^^^^       ^^^^^^^^^^^^^
        the file    two factors the file does NOT separate
        pins this
```

A slow gate through a steep map and a fast gate through a gentle map give the **identical**
Ku(t), the identical full swing, and the identical everything the file records - and completely
different answers under truncation, because truncation asks where the gate was, not how much
was flowing.

**Consequence.** No procedure operating on the file alone can split those two factors. One
stressed observation can. Every step below is either (a) a piece of the split, or (b) a check
that the file's own numbers are self-consistent.

---

## 1. Inputs

| input | source | needs probing? |
|---|---|---|
| I-V tables, V-T waveforms | the IBIS file | no |
| declared C_comp | the IBIS file | no |
| one stressed pad waveform, at one width | a pad probe on the real part | no |
| *(nothing else)* | | |

Not used: the transistor netlist, the predriver stage count, the gate node, the Ku-vs-gate map.
Those belong to track 2.

---

## 2. What gets built

```
   input ──►[ stage 1 ]──►[ stage 2 ]──► ... ──►[ stage K ]──► g ──►[ map ]──► Ku
            └──────────── K identical stages ────────────┘
```

**Each stage** is a current-limited node - a constant-current source into a capacitor, so its
output is a **ramp**:

```
   dx/dt =  s_up · h(u)   · min(1, (1−x)/x_lin)          charging
          − s_dn · h(1−u) · min(1, x/(x_lin·r))          discharging

   h(u) = clip((u − vt)/(1 − vt), 0, 1)^p                stage response to its input
```

`u` = the previous stage's output, `x` = this one's. `r` is the discharge-side taper ratio,
held at 1 (symmetric) in every build here. All K stages share one parameter set.

**The map** turns the last stage's output into Ku:

```
   Ku(g) = Ku_off + (Ku_on − Ku_off) · clip((g − vt_map)/(1 − vt_map), 0, 1)^α
```

`Ku_off` and `Ku_on` are read from the file; only the interior shape is assumed.

**Why a ramp and not an RC.** The shipped model uses a command delay followed by a fast RC
gate, so at any reversal its gate is essentially fully on or fully off - never partway. That is
its failure mode. A real predriver stage is a transistor in saturation charging the next gate,
which *is* a constant-current source, and its output *is* partway at a reversal. Measured: a
current-limited stage fitted at full swing predicts ex2's stressed gate to 0.05.

---

## 3. Parameter inventory

| symbol | meaning | how it is set | class |
|---|---|---|---|
| `s_up` | stage charge rate (1/ns) | fitted | **FITTED** |
| `s_dn` | stage discharge rate (1/ns) | fitted | **FITTED** |
| `x_lin` | how close to the rail before the constant current tapers | fitted | **FITTED** |
| `vt` | stage-to-stage handoff threshold | fitted, then **overwritten** by step S5 | **FITTED → CALIBRATED** |
| `C_comp` | pad capacitance | declared, or the knee if the file rejects it | **RULE** |
| `K` | stage count | one of 3 candidates | **SELECTED** |
| `vt_map`, `α` | map shape | one of 3 candidates | **SELECTED** |
| `p` | stage response power | assumed = 1 | **ASSUMED** |

Four numbers are fitted (three, where `x_lin` is pinned). Two discrete choices are selected.
One number is a rule. One is assumed.

Note the double life of `vt`: the fit produces a value, and S5 throws it away. The fit's real
product is the three **rates**.

---

## 4. The procedure

### S1 — C_comp

| | |
|---|---|
| **consumes** | the file's I-V tables, V-T waveforms and declared C_comp |
| **decides** | one number |
| **rule** | keep the declared value; if it implies a Ku above 1, take the knee where Ku first reaches 1 |

**Why a physical bound and not a fit.** Ku is by definition a fraction of the buffer's own I-V
table, so `Ku ≤ 1` identically. The solver books `C_comp · dV/dt` as device current, so too
large a C_comp makes the solved Ku exceed 1 - a buffer conducting more than its own table
allows. The file therefore **rejects** an impossible C_comp without any measurement.

**Why a rough value suffices.** The stressed peak is not sharp in C_comp once it is in range.

| buffer | declared | implied Ku | knee | loop-measured | score at the knee |
|---|---:|---:|---:|---:|---:|
| ex2 | 5.0 | **1.24** (rejected) | 2.64 | 1.7 | better at 2.31 than at 1.7 |
| ex2_slowpre | 5.0 | 1.03 | 4.65 | 1.7 | 5.4 % despite being 2.7x off |
| inv_chain | 0.468 | 1.00 | 0.66 | 0.6 | fine |

**Caveat.** The file's information about C_comp scales with `dV/dt`, so a slow buffer carries
almost none - ex2_slowpre is the failure case, and it only survives because the score is
insensitive.

### S2 — Fit the stage parameters

| | |
|---|---|
| **consumes** | the file's Ku(t) at the C_comp from S1; one candidate `(K, shape)` |
| **decides** | `s_up`, `s_dn`, `vt`, `x_lin` |
| **method** | Nelder-Mead, 3 restarts (s0 = 2, 8, 30), on a 2 ps grid over 4-21 ns |
| **target** | `map(chain output)` against the tables' full-swing Ku(t), rms |

**Why this target.** Track 1 has no probed gate, so the only curve available to fit is the one
the file implies. Nothing measured enters here.

**Why each parameter earns its place.**

| parameter | what it controls | where that shows up under stress |
|---|---|---|
| `s_up` | the gate's rise rate | **where the gate is when the reversal arrives** |
| `s_dn` | the gate's fall rate | how the gate comes back - the trailing half of the pulse |
| `vt` | how far the previous stage must rise before this one responds | how much of a short pulse survives each hop |
| `x_lin` | how current-limited the stage is (1 = an RC, small = a pure ramp) | the shape of the gate's approach to its rail |
| `p` | the stage's response curvature | **assumed**, because the full-swing tables cannot see it |

`vt` is not an abstraction: it is exactly why io_buf's pull-down chain never fires. Each stage
needs 0.7 of the swing from the one before, so a 163-322 ps pulse dies in the first stage and
GDN never rises (`results/io_buf_pulldown_calib_2026-09-23`).

### S3 — The stage-count band

| | |
|---|---|
| **consumes** | the S2 fit rms for K = 1 … 10 |
| **decides** | 3 candidate stage counts |
| **rule** | the 3 smallest K whose rms is within 25 % of the best |

**Why a band and not the best K.** The rms falls steeply, flattens at the true count, then
keeps creeping down past it - so "best rms" lands 1-3 stages high. The plateau rule recovers
the netlist count on **1 of 13 chains**. The file bounds K; it does not pin it.

**What the band delivers:** it contains the netlist count on all 12 buffers.

| buffer | band | netlist K |
|---|---|---:|
| ex2 family, inv_stage4 | 3, 4, 5 | 3 |
| inv_chain | 6, 7, 8 | 7 |
| inv_base8, inv_skewp, inv_weak | 5, 6, 7 | 7 |
| io_buf pull-up | 1 | 1 |
| io_buf pull-down | 3, 4, 5 | 3 |

### S4 — The shape grid

| | |
|---|---|
| **consumes** | nothing - a fixed list |
| **decides** | 3 candidate `(vt_map, α)` pairs |
| **grid** | `(0.50, 0.70)` universal · `(0.40, 0.60)` · `(0.40, 0.90)` |

**Why the shape cannot be fitted — this is section 0 made concrete.** Hand the S2 fit *any*
map and it will find a chain that reproduces the same Ku(t): steeper map with a slower chain,
gentler map with a faster chain, identical full swing either way. The fit is structurally
incapable of choosing between them. Only a stressed observation can.

**What it cost to learn this.** inv_chain sat at 34 %. With the universal shape the chain the
fit found implied a **square** gate, where the real gate rolls off with pulse width. Choosing
the shape from the stressed run instead: **5.1 %**, and its full swing improved with it
(54 → 36 mV). The discharge rate and a faster final stage were both tried first; both were
symptoms.

**S3 × S4 = 9 candidate models per buffer**, each with its own S2 fit.

### S5 — Calibrate on the one stressed run

| | |
|---|---|
| **consumes** | one stressed pad waveform, at the shortest width |
| **decides** | `vt`, overwriting S2's value |
| **method** | bisect `vt` over [0, 0.7], 7 steps in ngspice, until the model's peak matches |
| **fallback** | if `vt` cannot bracket the target, scale `s_up` and `s_dn` together over [0.5, 2.0] |

**Why `vt` and not the rates.** The rates were fitted to reproduce the full swing; moving them
breaks it. Moving `vt` changes **when** the chain hands off without changing how fast it runs.

### S6 — Select on the same run's whole waveform

| | |
|---|---|
| **consumes** | the same stressed run; the 9 calibrated candidates |
| **decides** | which candidate ships |
| **rule** | smallest rms between model and transistor pad over that pulse and 1.5 ns of its return |

**Why not the peak.** S5 has just forced the peak to match at that width for **every**
candidate. The peak is spent - measured, adding a peak gate to the rule changes nothing.

**Why not peaks at other widths either.** A chain that turns on late still hits the right peak
height with the wrong pulse under it. Ranking that way picks builds that arrive **155-300 ps**
late:

| ranked by | waveform error, mean over all widths |
|---|---:|
| whole waveform at the calibration width | **52.3 mV** |
| best possible in the grid | 51.7 mV |
| best stressed peak | **217.3 mV** |

**Why the window is what it is:** the pulse plus 1.5 ns of its return was chosen once and never
tuned. It is the rule's one untested free choice.

---

## 5. The result

**All 12 buffers within ±10 %** on the worst stressed peak against the transistor.

| | value |
|---|---|
| range | 3.2 % (inv_stage4) … 10.0 % (ex2_skewp, on the line) |
| mean | 6.9 % |
| shipped model, same pulses | 35 - 76 % on 11 of 12 |
| inv_chain, file-only | **5.1 %**, against 25.8 % for the build made from probed silicon |
| selector quality | within **1 %** of the best build the grid contains |

**What it costs.**

| | |
|---|---|
| full swing | our pad rms is worse than shipped on 10 of 12 (ex2: 61 vs 16 mV) |
| pulse trains | shipped still wins on ex2 and io_buf |
| io_buf | the one buffer where shipped beats us outright (4.0 vs 7.7 %) |

---

## 6. What this has been tested on

| axis | covered | not covered |
|---|---|---|
| depth | 50, 60, 70, 80, 90 % of the settled swing | below 50 % |
| direction | short HIGH | **short LOW on 11 of 12** |
| pulses | one | trains |
| load | 50 Ω ∥ 2 pF | anything else |
| corner | Typical | Min / Max, supply, temperature |

---

## 7. What is not yet honestly file-only

1. **The shape grid was chosen from results on these same 12 buffers.** `(0.40, 0.60)` and
   `(0.40, 0.90)` are the two best of an earlier grid run on this set, so S4 has seen the answer
   key. A 13th buffer may need a shape the grid does not contain.
2. **`x_lin` is inconsistent.** Pinned at 0.45 on 10 buffers - defensible as a prior - but
   fitted on inv_chain and io_buf. It should be one or the other.
3. **`p = 1` is assumed**, never tested against `p = 2` (the square-law alternative).
