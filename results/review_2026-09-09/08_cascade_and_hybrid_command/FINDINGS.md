# Prototype v2: the command delay as an analog RC cascade

*2026-09-09*

**Why.** `gate_ramp_prototype_2026-09-09` showed nothing done to the gate can move
the stressed peak on ex2, because the peak is set before our off-command arrives:
the command is a T-line delay, so the input reversal cannot influence the model
until rev + pu_off (733 ps), while the transistor's rise bends the instant the
input reverses. Its predriver is a chain of analog stages, not a delay.

**What.** Replace the pull-up command path — two T-lines (pu_on, pu_off) and an
AND producing a 0/1 target — with an N-stage RC cascade driven by the input,
each stage first-order with separate up/down time constants calibrated so the
50 % crossings land at pu_on and pu_off (Erlang-N: x_N·τ with x = 0.693, 1.678,
2.674, 3.672, 4.671, 5.670). The gate target becomes continuous. The Ku gate maps
are re-derived from the new full-swing GUP(t) against the shipped gate-part
Ku(t), so **full swing is preserved by construction**. `--pd` does the same for
the pull-down command and the Kd maps.

`scripts/gate_cascade_prototype.py`, `<variant>/sweep.csv`.

---

## ex2_base: the entry-level defect goes away at N = 5

Peak error (%) and lag (ps) against the transistor; full-swing Ku rms in the
second column.

| build | FS Ku rms | 90 % | 80 % | 70 % | 60 % | 50 % depth | lag 90 → 50 % |
|---|---:|---:|---:|---:|---:|---:|---|
| shipped | — | +3.4 | +13.0 | +26.7 | +44.5 | **+70.9** | 124 → 300 |
| cascade 1 | 0.0029 | −97 | −94 | −90 | −87 | −83 | never rises |
| cascade 2 | 0.0018 | −64 | −79 | −89 | −89 | −88 | |
| cascade 3 | 0.0014 | −26 | −41 | −55 | −59 | −55 | −106 → −199 |
| cascade 4 | 0.0011 | −13.8 | −20.1 | −21.8 | −18.6 | −13.7 | −7 → 46 |
| **cascade 5** | **0.0008** | **−8.8** | **−9.5** | **−7.2** | **−1.0** | **+8.0** | **40 → 158** |
| cascade 6 | 0.0011 | −6.4 | −4.5 | +1.7 | +11.1 | +23.8 | 64 → 221 |
| cascade 5 + `--pd` | 0.0013 | −8.9 | −10.4 | −8.0 | −1.5 | +8.0 | 34 → 147 |

The error crosses zero between N = 5 and 6. At N = 5 the stressed peak is within
±10 % at every depth, from +71 % — with a change that is derived, not tuned:
the only inputs are the shipped delays (which set the 50 % points) and the
shipped full-swing Ku(t) (which sets the maps). The full-swing coefficient is
reproduced to 0.0008 rms, better than any earlier prototype. Lag halves;
cascading the pull-down too takes another ~10 ps.

N is the one free choice. Physically it is how many analog stages the predriver
behaves like; ex2's netlist has three predriver stages driving a large output
stage, and the fit says "about five first-order sections", i.e. each real stage
is somewhat more than first-order. That is the number to check on the other ex2
variants.

## inv_base8: catastrophic — a cascade is the wrong physics for a regenerative chain

| build | 100 % | 90 % | 70 % | 50 % depth |
|---|---:|---:|---:|---:|
| shipped | +0.1 | +3.3 | +22.8 | +65.1 |
| cascade 1–4 | −82…−99 | **−97…−99** | −98 | −98 |

The pad never rises. inv_base8's pulses are 100–170 ps against a 267 ps on-delay:
an Erlang cascade whose 50 % point is at 267 ps passes almost nothing of a 100 ps
pulse, so the gate never turns on. The real inverter chain passes it nearly
intact, because each inverter regenerates — the delay really is a delay there,
and only the last stage is analog. This is the same split the gate probe found
(`gate_physics_2026-09-08`): ex2's predriver is speed-limited, inv_chain's
completes but late.

The candidate for inv is the hybrid: keep the delay line, put one analog stage
after it (`--hybrid TAU`), calibrated so the 50 % points do not move. Tested
below.

## io_buf: neutral, as its regime predicts

| build | FS Ku rms | peak 2354 → 1505 ps | lag |
|---|---:|---|---|
| shipped | — | +2.1 → −3.5 % | 63 → 65 ps |
| cascade 2–5 | 0.0001–0.0003 | −2.5 → −6.8 … +0.7 → −3.2 | 53 → 82 … 64 → 81 |

No help and no harm. io_buf's slow element is the gate itself (τ_rise 1.13 ns),
and its pedestal was removed on the gate side (`gate_ramp_prototype`, `single`
k = 4). The command delay was never its problem. That the cascade leaves io_buf
alone while fixing ex2 is the regime picture holding under a structural change.

## Status of the three fronts after both prototypes

| buffer family | defect | fix that works | remaining |
|---|---|---|---|
| ex2 (speed-limited predriver) | entry level, +71 % | **RC cascade, N ≈ 5** | lag 40–158 ps; N to confirm on variants |
| inv_chain (regenerative chain) | turn-off late, +65 % | dual slow-fall map (¼ of it) | hybrid under test |
| io_buf (slow gate) | pedestal, residual | single slow-gate map (pedestal); fenced depth-scaled residual (bump) | deep-stress peak −10…−13 % |

## Caveats

* Pull-up path only unless `--pd`; short-high only.
* Maps re-derived on a 200-point grid from a single full-swing run.
* Native is dead on the ex2 variant IBIS (−97 % here), so the ex2 comparison is
  ours-vs-transistor only.
* N = 5 chosen on ex2_base; the other four ex2 variants are running at N = 4–6
  to see whether it is a family constant.

---

## Addendum, same day: the inv hybrid, and N on a second ex2 variant

**inv_base8, delay line + one analog stage (`--hybrid TAU`)**, 50 % points held
by shortening both T-line delays by 0.693·τ:

| τ | FS Ku rms | 100 % | 90 % | 80 % | 70 % | 60 % | 50 % depth | lag 100 → 50 % |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| shipped | — | +0.1 | +3.3 | +11.2 | +22.8 | +41.3 | **+65.1** | 11 → 67 |
| **50 ps** | **0.0001** | −0.7 | −1.1 | +1.4 | **+7.7** | **+19.1** | **+35.6** | 10 → 56 |
| 100 ps | 0.0002 | −5.1 | −26 | −50 | −63 | −71 | −71 | 0 → 8 |
| 200 ps | 0.0003 | −87 | −99 | −99 | −99 | −99 | −98 | never rises |

One ~50 ps analog stage after the delay halves inv's peak excess at every
depth, with full swing reproduced to 0.0001 and lag down ~12 ps. 100 ps
over-corrects; anything longer swallows the 100–170 ps pulse — the same failure
the pure cascade had, now with a knob that says where the boundary is. The
finer sweep (60–80 ps) and the other three inv variants are running.

**ex2_weak at N = 5**: peak −8.1 / −4.4 / −6.6 / −0.8 / +7.0 % from −0.7 → +66.3,
lag 36 → 94 ps, full swing 0.003 — the same numbers as ex2_base. Two of two ex2
variants put the crossover at N = 5; the remaining three are running.

**The picture the two prototypes leave:** three buffer families, three
structures, each derived from the shipped model plus one integer or one time
constant, each preserving full swing by construction —

| family | predriver physics | structure that works | free choice |
|---|---|---|---|
| ex2 | speed-limited analog stages | RC cascade replacing the delay | N = 5 |
| inv_chain | regenerative chain + one analog output stage | delay line + one RC after it | τ ≈ 50 ps |
| io_buf | slow gate, peak at the reversal | slow gate with re-derived single map; fenced depth-scaled residual | k = 4, fence < 1.3 ns |

Native fails on all three in the ways recorded earlier; none of these structures
is available to it.

## Addendum 2: N across the ex2 family, τ on inv_base8

| ex2 variant | shipped 50 % peak | best N | peak at best N (90 → 50 %) | lag at best N |
|---|---:|---:|---|---|
| ex2_base | +70.9 % | 5 | −9 / −10 / −7 / −1 / +8 | 40 → 158 |
| ex2_weak | +66.3 | 5 | −8 / −4 / −7 / −1 / +7 | 36 → 94 |
| ex2_nomiller | +67.8 | 5 (–6) | −12 / −14 / −13 / −9 / +2 | 22 → 123 |
| ex2_skewp | +58.7 | 6 | −9 / −12 / −10 / −10 / −2 | 20 → 66 |

N is 5 on three variants and 6 on the one whose pull-up PMOS is halved (a slower
rise wants one more section). A family range of 5–6, not a per-buffer fit; every
residual error is inside ±15 % from +59…+71 % shipped. ex2_slowpre is running.

**inv_base8, finer τ:**

| τ | 100 % | 90 % | 85 % | 80 % | 70 % | 60 % | 50 % | lag 100 → 50 % |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| shipped | +0.1 | +3.3 | +7.2 | +11.2 | +22.8 | +41.3 | +65.1 | 11 → 67 |
| 50 ps | −0.7 | −1.1 | +0.2 | +1.4 | +7.7 | +19.1 | +35.6 | 10 → 56 |
| **60 ps** | −1.2 | −2.8 | −3.2 | −3.4 | **−0.5** | **+7.9** | **+22.2** | 9 → 50 |
| 70 ps | −1.7 | −6.6 | −8.8 | −11.1 | −9.1 | −9.4 | −1.2 | 7 → 41 |
| 80 ps | −2.6 | −10.2 | −16.7 | −20.4 | −25.2 | −26.9 | −19.6 | 5 → 33 |

τ = 60 ps holds every depth down to 70 % within ±4 % and takes the 50 % case from
+65 to +22 %; 70 ps zeroes the deepest case at the cost of the middle. The
residual mid-depth error is the sign that one first-order stage is not quite the
right shape either — but a single 60 ps constant, full swing kept to 0.0001, is a
long way from +65 %. The other three inv variants are running at 40–80 ps.

## Addendum 3: ex2_slowpre, inv_skewp

**ex2_slowpre** (predriver at half width): shipped 0 / +5 / +14 / +27 / +44 %;
N = 6 → −10 / −13 / −10 / −7 / −3 %, lag 77→300 → 4→151, FS 0.0011; N = 5
over-corrects (−12…−16). So across the five ex2 variants:

| variant | N | note |
|---|---:|---|
| ex2_base, ex2_weak, ex2_nomiller | 5 | |
| ex2_skewp, ex2_slowpre | 6 | the two with a slower rise (halved PMOS; halved predriver) |

A family range of 5–6, moving one step with the rise speed. Every residual
error inside ±16 % from +44…+71 % shipped.

**inv_skewp** (`--hybrid`): shipped −1 / +2 / +9 / +18 / +35 %; τ = 50 ps →
−2 / −1 / +1 / +5 / +12 % (lag 9→52 → 8→42, FS 0.0002); τ = 65 ps →
−2 / −4 / −5 / −3 / +1. The same 50–65 ps window as inv_base8. Two of two inv
variants; inv_weak and inv_stage4 running.

**inv_weak** (`--hybrid`): shipped −1 / +1 / +6 / +16 / +34 %; τ = 50 ps →
−2 / −2 / 0 / +4 / +15 % (lag 6→49 → 4→37, FS 0.0002); τ = 65 ps →
−3 / −5 / −7 / −7 / 0. Three of three inv variants sit in the same 50–65 ps
window. inv_stage4 running.

**inv_stage4** (`--hybrid`): shipped 0 / +1 / +4 / +5 / +12 / +23 / +40 %
(100 → 50 % depth); τ = 40 ps → −0.4 / −0.9 / −1.8 / −2.2 / −3.4 / −2.1 / +2.1 %,
lag 8→40 → 9→25, FS 0.0002; τ = 50 already over-corrects (−21 % at 50 %). The
fastest chain (pu_on 102 ps against base8's 267) wants the shortest stage.

## Closing table: what the two prototypes established across the twelve

| buffer | shipped 50 % peak | structure | choice | 50 % peak after | worst depth after |
|---|---:|---|---|---:|---|
| ex2_base | +71 % | RC cascade | N = 5 | +8 % | −10 % |
| ex2_weak | +66 | cascade | 5 | +7 | −8 |
| ex2_nomiller | +68 | cascade | 5 | +2 | −14 |
| ex2_skewp | +59 | cascade | 6 | −2 | −12 |
| ex2_slowpre | +44 | cascade | 6 | −3 | −13 |
| inv_base8 | +65 | delay + one stage | τ = 60 ps | +22 | +22 |
| inv_skewp | +35 | delay + one stage | 50 | +12 | +12 |
| inv_weak | +34 | delay + one stage | 50 | +15 | +15 |
| inv_stage4 | +40 | delay + one stage | 40 | +2 | −3 |
| io_buf | −3 (pedestal +65 ps) | slow single-map gate; fenced residual | k = 4; fence < 1.3 ns | pedestal −20…+10 ps | peak −10 % |

Each choice is one integer or one time constant, each build reproduces the
shipped full-swing Ku(t) to ≤ 0.004 rms, and the structure that works on each
family is the one the transistor's own gate predicted in
`gate_physics_2026-09-08`. Native fails on all of them in the ways recorded
earlier.

Open: the inv residual +12…+22 % at 50 % depth (one first-order stage is not
quite the right shape for the last inverter); ex2's lag (still +40…+160 ps at
N = 5); io_buf's deep-stress peak; short-low, trains and open-drain untested with
any of these.
