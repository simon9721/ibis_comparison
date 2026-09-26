# Review package — stress investigation, 2026-09-07 → 09-09

Each folder is one claim. Inside: the figure that shows it, the CSV it was
computed from, the write-up (`FINDINGS.md`) with every number, and the script
that produced it (re-runnable with `py -3.14 <script>`). Reference throughout is
the **HSPICE transistor**; native IBIS is the bar; "ours" is the shipped
`InputDrivenTwoStateGateDelayCommandFull` build unless stated.

Read the folders in order; each builds on the last.

---

## 01 — Two stress regimes, twelve buffers  `01_two_regimes_twelve_buffers/`

**Claim.** Under stress, eleven buffers (four inv_chain variants + base, five ex2
variants + base) fail the same way: our model enters the reversal with the
pull-up fully on where the transistor is only part-way, so the stressed peak comes
out **+34…+71 % too tall at 50 % depth**. io_buf alone is in a different regime
(peak within ±3 %), because its gate is slow (τ 1.13 ns) and its pad peaks at the
reversal.

**Evidence.** `cross_device_stress.png` — panel 1: peak excess vs depth, all
twelve; panel 2: entry excess vs peak excess, **r = 0.889 over 68 cases,
0.86–0.98 inside every buffer**; panel 5: io_buf isolated by gate τ and event
timing. Native (dotted) fails identically where alive.
Numbers: `metrics.csv` (one row per case × model), `cases.csv` (per case).

**Also in the write-up.** The transistor's Kd residual shrinks toward zero with
stress on 12/12 buffers while ours is constant (panel 4). Native is dead on all
ex2 variants and inv_stage4 below 90 % (tr1ps IBIS files) — flagged
`native_valid = 0`, excluded. Pedestal sign vs the transistor is positive on
every case; the old "opposite sign on inv/ex2" was measured against native.

---

## 02 — Ku is a static map of the real gate; the loop measures C_comp  `02_gate_physics_and_ccomp_loop/`

**Claim.** The matrix transistor runs recorded the predriver gate node (io_buf
`n2`, inv_chain `vout7`, ex2 `n4`). Plotting the two-fixture Ku against it: on
io_buf and inv_chain Ku is a **static function of the gate** (loop ≤ 0.1). On ex2
it is not (loop 0.5–0.75) — until C_comp is corrected: a wrong C_comp books
displacement current as Ku with a sign that flips between rise and fall, opening a
loop. Minimising the loop gives **ex2 = 1.5–1.75 pF on all five widths, declared
5.0**; inv_chain 0.5–0.6 (declared 0.47); io_buf too shallow to decide.

**Evidence.** `ku_gate_hysteresis_ccomp.png` — top row: loop vs C_comp used, per
width (ex2's declared value is at the far right, off the minimum); bottom row:
the Ku-vs-gate loop at the declared value and at the minimum.
Script: `ku_gate_hysteresis_ccomp.py`.

**What it settles.** The gate-map architecture is physically right; our error is
in the gate *dynamics*. Three different physical situations hide under "stress":
io_buf's predriver is truncated by the pulse; inv_chain's completes but late;
ex2's reaches ~70 % regardless (at those widths).

---

## 03 — Applying the measured C_comp makes the model worse  `03_ccomp_correction_negative_result/`

**Claim.** Editing ex2's `.ibs` to the measured 1.7 pF makes **every stressed
metric worse** for ours and native (858 ps: peak +244 → +289 mV, lag +236 → +268
ps), with the control unchanged. The declared 5 pF was compensating about a third
of the gate-timing error by slowing the simulated pad. **Order matters: fix the
gate turn-off first, then correct C_comp.**

**Evidence.** `ex2_ccomp_correction_negative.png` (bars, both models, both
widths), `run.log` (raw numbers), `FINDINGS.md`.

---

## 04 — Pulse trains: nothing accumulates  `04_pulse_train_no_accumulation/`

**Claim.** Eight pulses at 50 % duty: every stressed error moves to a **new
plateau within 3–4 pulses** and stays there; controls are flat to the picosecond.
Two things a single pulse hides: on ex2 the error **flips sign** (+250 mV too
tall on pulse 1, −107 mV too low from pulse 3 — the device itself nearly reaches
full swing once the pad stops returning to zero), and **io_buf native collapses**
on the stressed train (+750 mV, lag pinned −327 ps from pulse 4) while ours holds
at +90 ps.

**Evidence.** `pulse_train.png` (top: stressed, bottom: control, per pulse),
`per_pulse.csv`.

**Caveat.** inv_chain's ~270 ps output delay against 222 ps windows shifts its
per-pulse attribution by one; the plateau conclusion is unaffected.

---

## 05 — Open-drain, three variants  `05_open_drain_three_variants/`

**Claim.** The open-drain ex2 (base, pull-down at half width, predriver at half
width) shows the regime in its purest form: the transistor's low excursion runs
smoothly from ~5 % to ~95 % depth while **both IBIS models pull all the way down
at every width** (Kd = 1.0 at the pad minimum). The transistor's Kd at the
minimum is **linear in depth at R² ≥ 0.99 on all three**, and its real gate at
that instant tracks depth at corr ≥ 0.99.

**Evidence.** `od_three_variants_law.png` — left: Kd at the minimum vs depth,
transistor (solid, with fit) against ours (dashed, flat at 1); middle: the real
gate vs depth; right: model-minus-transistor low error. `sweep_*.png` — the raw
pad waveforms per width for each variant. `cases_*.csv`.

**Two converter facts.** Our build has **no gate-state path for `Open_drain`**
(`subcircuit.py` falls back to legacy Kd control): it rests in the wrong state
(pulled low with the input high — visible at t = 0 in every `sweep_*.png`) and is
~120 ps late on both edges at full swing. **Native malfunctions on od_weak**: Kd
goes to −0.82 and it drives the pad above VCC to 3.6 V (right panel, positive
errors). The single-fixture C_comp loop on the OD closes at 3.0 pF vs push-pull's
1.7 — both effective values, gap open, both far from the declared 5.0.

---

## 06 — io_buf background from 09-07  `06_io_buf_background_0907/`

The io_buf-only results this week's generalisation was testing. Kept here so the
claims above can be checked against where they started:

* `native_st_vs_solved.png` — native's stored trajectory *is* the offline
  two-fixture solve (residual 0.4 % of span). No mystery in the trajectory.
* `silicon_kukd_conditioning.png` — the transistor's coefficients within ~90 ps of
  a reversal are `C_comp·dV/dt` differentiation noise (they do not converge with
  the grid); **not** ill-conditioning (cond 1.4–2.7). Every window in this
  package starts past that zone.
* `full_swing_silicon_kukd.png` — the transistor's Ku overshoots early and
  briefly (+25–30 ps); both IBIS models make it late and broad. Native's Ku is
  1.52× the transistor at full swing.
* `pu_off_conflict.png` — `pu_off` sets both the gate turn-off and its phase
  against the residual spike; the two objectives are monotone in opposite
  directions (best 0.10 vs 0.86), so no single value works.
* `correction_bump.png`, `correction_shapes.png` — the +1.8 ns pull-down turn-on
  bump: transistor's moves 205 ps across the stress range, native 68, ours 6.
  io_buf-only (05 and 01 show the other buffers have no such event).

---

---

## 07 — Slow gate + re-derived map  `07_gate_ramp_prototype/`

**Claim.** Slowing the gate ramp by k and re-deriving the map from the shipped
full-swing gate-part Ku(t) (so full swing is preserved by construction) fixes
io_buf's pedestal (single map, k = 4: +63…+69 → +10 / +9 / +2 / −4 / −20 ps),
takes a quarter off inv_base8's peak excess (dual map, 65 → 49 %) and ~100 ps
off ex2's lag — but **cannot move ex2's peak**, because the peak is set before
the command T-line lets the reversal through. *Check:* `sweep_*.csv`.

## 08 — The command as an RC cascade / delay + one stage  `08_cascade_and_hybrid_command/`

**Claim.** Replacing the command T-lines with an N-stage RC cascade (50 % points
at pu_on / pu_off, maps re-derived) removes ex2's entry-level defect: **ex2_base
+71 % → −9…+8 % at N = 5**, ex2_weak the same, ex2_nomiller N = 5, ex2_skewp
N = 6; full swing kept to Ku rms ≤ 0.003. A pure cascade is catastrophic on
inv_chain (a 100 ps pulse cannot pass it; the real inverter chain regenerates),
where **delay line + one ~60 ps analog stage** halves the peak excess instead
(inv_base8 65 → 22 %). io_buf is neutral. Three families, three structures, each
predicted by the gate probe in 02. *Check:* `prototypes_summary.png`, `sweep_*.csv`.

## 09 — Residual scaled by depth, and fenced in time  `09_residual_depth_rule_and_fence/`

**Claim.** Scaling the falling residual by pad-peak ÷ plateau (the 12/12 law)
matches the old gate-based FRAC on io_buf (Kd rms 0.03 → 0.01–0.02) and, like
it, halves the +1.8 ns bump — until the scale is **fenced** to the truncated fall
(HNX < ~1 ns), which restores the bump to within 5 mV of the transistor with
nothing else lost. On inv/ex2 the rule does nothing: the residual is not their
defect. *Check:* `results_io_buf.csv` rows `fenced_*` vs `frac_depth`.

## 10 — Inside the transistor: stage by stage, and the real gate replayed into the model  `10_transistor_stages_and_gate_replay/`

**Claim A (what the transistor does).** Every internal node probed at full swing
and five stressed widths, each tested against the superposition of its own two
step responses (`stages_vs_linear_*.png`, `pulse_down_the_chain_*.png`):
**io_buf is linear from input to pad** — its stressed pads are its step
responses cut short, nothing else. **ex2** is three slow inverters (n4 reaches
50 % 1.1 ns after a 50 ps input edge); its stages are sub-linear in the *return*
(n4 0.76 vs 0.93 linear at 810 ps) — current-limited stages. **inv_chain's**
seven stages are near-linear (vout7 0.88 vs 1.00) and the pulse dies in the
output inverter (pad 0.49 vs 0.85). *Check:* `stages.csv` columns `meas_max`,
`p2_max`.

**Claim B (one gate, two maps).** ex2 and inv_chain drive P and N from one node;
the transistor's Kd is a static map of it (loop 0.04–0.06,
`kd_gate_hysteresis.png`). Tying the model's GDN to 1 − GUP changes the peak
< 1.5 % (`shared_gate_sweep_*.csv`) — right, not the lever.

**Claim C (the split).** Feed the model the transistor's real gate
(`gate_replay_*.png`). ex2 at C_comp 1.7 pF: **−3…−6 %, 18–24 ps** on all five
widths (shipped +4…+74 %). So ex2's stressed error is predriver + C_comp; the
static-map output stage is right. inv_chain with the IBIS-implied map:
**−14…−69 %** — the map is late in the gate (Ku 0.19 vs silicon 0.57 at
g = 0.7, `maps_inv_chain.png`); with the silicon Ku-vs-gate map, measured at
full swing, the same replay is **+2…+9 %, 9–13 ps** (`silicon_map_replay_inv_chain.png`)
and the full-swing pad improves too. On ex2 the two maps agree to ±0.03. io_buf (two
widths; the deeper three stall ngspice, see FINDINGS §7): peak unchanged, lag 63 → 38 ps. *Check:*
`sweep_*_gate_replay_silicon_full.csv`.

## 11 — Breaking the map/gate tie with physics, and the predriver's non-linearity  `11_physics_prior_and_current_limited_stages/`

**Claim A (map prior).** The three silicon Ku-vs-gate maps share one shape,
`((g − vt)/(1 − vt))^alpha`, vt ≈ 0.5, alpha 0.6–0.8 (`physics_map_gate.png`,
top row). Inverting it on the shipped model's full-swing Ku(t) recovers the real
gate: inv_chain to 10 ps (rms 0.028), ex2 at the 50 % point (middle row). The
tables are not late; the model's RC gate was the wrong partner. *Check:*
`results_physics_map_gate.csv`.

**Claim B (superposition is not enough).** Superposing the derived step
responses predicts io_buf's stressed gate within 0.035 (the shipped RC gate is
0.15–0.27 low), inv_chain within 0.01 at shallow and +0.11 at the deepest width,
ex2 not at all (0.99 vs 0.76) — bottom row.

**Claim C (current-limited stage).** One stage, four numbers fitted at full
swing only, driven by its measured stressed input, predicts ex2's output gate to
0.05 from the input pin (linear: 0.17 off) and each inv_chain stage to rms 0.003
(`*_current_limited_stages_p1.png`, red on black). The drive law under a partial
input (p) is invisible at full swing and must be assumed; p = 1.

**Claim D (how many stages, and from what).** K *identical* stages, four
shared numbers fitted at full swing: ex2 K = 3 predicts the stressed gate within
0.04 (`ex2_chain_shared_K.png`), inv_chain K = 7–9 brackets it. The full-swing
rms plateaus at the real stage count (3 and 7), so K is recoverable from the
tables alone; a free per-stage fit is degenerate and can swallow short pulses
(`*_chain_K.png`). *Check:*
`results_current_limited_stages_p1.csv`, `*_chain_K.csv`.

## 12 — The current-limited chain built in ngspice  `12_current_limited_chain_in_ngspice/`

**Claim A (ex2 solved by the recipe).** Three identical current-limited stages
(four numbers fitted at full swing) with the silicon maps: **−3…−10 %** on all
five stressed widths, lag 60–70 ps (shipped +4…+74 %, 150–300 ps); file-only
(IBIS gate through the prior, prior maps) −10…−28 %. *Check:*
`chain_ex2_c1.7_real_silicon.png`, `sweep_ex2_c1.7_*.csv`.

**Claim B (a converter defect on inv_chain).** The IBIS file declares Vinh 2.0 V
on a 1.8 V part; the digital input switches at 1.4 V and cuts every 50 ps-edge
pulse by 29 ps. With the comparator at mid-supply the shipped model's error
doubles (+31 → +66 % at 104 ps): two errors have been cancelling. *Check:*
`input_threshold_check_2026-09-10.txt`.

**Claim C (the cliff).** On inv_chain the chain reproduces the gate maximum to
0.03 but sits on a pulse-swallowing cliff between K = 7 (collapses at the two
deepest widths) and K = 9 (passes them, returns ~10 ps late, pad +17…+51 %); the
drive law under a partial input cannot be fitted at full swing. io_buf's gates
are placed correctly (0.63 vs 0.67 where the RC gate gave 0.40) but its
residual regime is not re-attached, pad −6…−29 %. *Check:* `chain_inv_chain_c0.6_*.png`,
`chain_io_buf_*.png`.

**Claim E (round 3, `NEXT_STEPS_FINDINGS.md` §6–8).** Calibrating on the probed
gate maximum is the wrong target for fast chains (the pad follows the gate
pulse's width too); calibrating on **the pad peak at one stressed width** — one
extra transistor run, no probe — puts **eleven of twelve buffers inside ±10 % at
every depth** with lags of tens of ps (shipped +35…+77 %, 150–300 ps; native dead
on six). io_buf is the exception (its gate is linear and needs the measured step
response, not a fitted stage). The recipe is one command,
`build_chain_model.py`, verified line-for-line against the prototype. *Check:*
`chain_*_calibpad*.png`, `sweep_*_calibpad*.csv`, `gate_max.json`.

**Claim F (round 4, `NEXT_STEPS_FINDINGS.md` §9–12).** io_buf's command as its
own measured step responses (two edge stopwatches, two pwl tables) draws the
ramp a fitted stage cannot (gate rms 0.029) but the truncated ramp runs 4 %
above its step response and the deep widths stay 13–25 % low; its pad
calibration hit the io_buf ngspice stall. C_comp by the loop method on all nine
variants: ex2 family 1.75–2.0 pF (declared 5.0), inv family 0.3–0.5 (declared
0.47); the pad calibration absorbs the inv differences. The builder now does the
pad calibration itself from a CSV. **The pulse train exposes the next degree of
freedom**: file-only chains calibrated on one pulse are right on pulse 1 and
9 % (ex2) / 23 % (inv_chain) low on the settled train, where the real-gate chain
was within 7 mV — a stressed train is the second characterisation point. *Check:*
`step_io_buf_*.png`, `ccomp_loop.json`, `pulse_train_fileonly.png`.

**Claim G (round 5, `NEXT_STEPS_FINDINGS.md` §13–14).** With a stressed train as
the second characterisation point, ex2's chain (x_lin 0.25) is within ±2 % on
every single-pulse width and within 3 % on the settled train — but 140 ps
late; the x_lin that gets timing right leaves the train 9 % low. One resistive
fraction cannot serve both, and a separate discharge fraction made it worse:
the four-number stage law is now the frontier. inv_chain's train shortfall
(−20 %) does not move with x_lin. The chain's text generation now lives in the
converter package (`chain_command.py`), builder output identical. *Check:*
`train_calib_sweep_*.csv`.

**Claim D (the next steps, `NEXT_STEPS_FINDINGS.md`).** The converter now
clamps input thresholds to the supply (inv_chain 1.4 → 0.9 V). A three-parameter
map prior (saturation before the rail) matches the silicon maps to 0.013–0.036
and, as the map with the real gate, gives ex2 −0.3…+2 %. **One stressed
characterisation point** (the gate maximum at the deepest width) removes the
inv_chain cliff: real gate +2…+19 % / ±9 ps, and **file-only −11…0 % /
−17…+1 ps**; on ex2 file-only −6…+7 %. The ex2 chain tracks a stressed 8-pulse
train to 7 mV / 10 ps after pulse 1 (native −114 mV / +136 ps). io_buf's shallow
widths are fixed by re-attaching the depth residual; its deep widths need the
NOR ramp itself. *Check:* `chain_*_calib*.png`, `pulse_train_ex2_chain.png`.

## What the whole set says about the model, in order

0. The output stage is a static Ku/Kd map of one gate node (10). Assume the
   MOSFET-shaped map (11A), fit K identical current-limited stages so that the
   map of the chain reproduces the tables' Ku(t) (11C, 12A) — done on ex2. Clamp
   the input thresholds to the supply first (12B). For fast chains, one stressed
   characterisation point to place the drive law (12C). Judge every gate
   prototype together with its map.
1. Make the command structure match the predriver: an RC cascade for ex2
   (N = 5–6), delay + one ~60 ps stage for inv_chain, a slow single-map gate for
   io_buf — each derived, each preserving full swing (07, 08). This is the
   entry-level defect from 01 and 05, fixed on ex2 and halved on inv.
2. Then correct C_comp (ex2 ≈ 1.7 pF) — not before (03).
3. Replace io_buf's FRAC with the universal law: residual ∝ depth (01, 05).
4. Add a 50 %-duty stressed train to validation (04).
5. Build an Open_drain gate-state path with a correct rest state (05).

## Retracted along the way (so you do not find them elsewhere and wonder)

* "ill-conditioned solve" as the reason the transistor's near-reversal Ku spikes
  — it is the differentiation grid (06).
* a secondary bump on ex2 — argmax on a monotone tail (05, 01).
* a Kd sign flip on eight buffers — a window artifact; only ex2_slowpre and
  inv_stage4 genuinely cross zero (01).
* `PU_OFF_SCALE = 0.70` as "derived", and my own 0.29 after it (06).
