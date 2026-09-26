# The five next steps, carried out

*2026-09-10*  ·  follows `FINDINGS.md` in this folder  ·  builds under `<variant>/<build>/`

## 1. Converter: clamp the input threshold to the supply — done

`tools/pybis2spice/pybis2spice/subcircuit.py::estimate_input_threshold` now
returns VCC/2 whenever the declared Vinh/Vinl sit outside the supply (Vinh ≥
VCC, Vinl ≤ 0, or Vinh ≤ Vinl). Regenerated: inv_chain 1.4 → **0.9 V**; ex2
and io_buf keep 1.4 V (Vinh 2.0 < 3.3). All three IBIS files carry the same
Vinl 0.8 / Vinh 2.0 V, a characterisation default rather than device data; on
the 3.3 V parts it still puts the switching point at 42 % of the edge (8 ps on
a 50 ps edge, 1 % on the pad), on the 1.8 V part it was 29 ps and half the
stressed error. The shipped inv_chain re-scored at 0.9 V: +2 / +8 / +18 / +37 /
+66 % (was −8 / −8 / −2 / +11 / +31 %) — the honest error of the shipped
command layer. `threshold_clamp_check/`, `../input_threshold_check_2026-09-10.txt`.

## 2. Sharpen the map: a three-parameter prior — done, and it is the map

`Ku(g) = ((g − vt)/(gs − vt))^alpha`, saturating at gs < 1
(`physics_map_gate_from_ibis.py`, `fit_prior3`):

| buffer | vt | alpha | gs | rms (was, 2-parameter) | gate at Ku 0.8 / 0.9: prior vs real |
|---|---:|---:|---:|---|---|
| ex2 | 0.52 | 1.10 | 0.91 | 0.036 (0.068) | 0.84 / 0.87 vs 0.84 / 0.88 |
| inv_chain | 0.42 | 1.15 | 0.87 | **0.013** (0.070) | 0.79 / 0.83 vs 0.79 / 0.82 |
| io_buf | 0.51 | 0.75 | 1.00 | 0.015 (0.014) | 0.87 / 0.94 vs 0.87 / 0.93 |

With saturation the exponent comes out ≈ 1.1 — the same near-linear drive
law the stage model uses (p = 1). Used as the *map* with the real gate on ex2:
**−0.3 / −5.2 / −5.5 / −3.4 / +2.0 %**, indistinguishable from the silicon map.
The map side is closed.

Used inside the file-only *chain fit* it did not help (ex2 −18…−38 %): the
Ku-domain fit is the weak link, not the map (see 3).

## 3. One stressed characterisation point — done, and it removes the cliff

`--calib W GATE_MAX`: after the full-swing fit, the stage threshold (the drive
law under a partial input, invisible at full swing) is moved until the python
chain reproduces the measured gate maximum at one width; the four full-swing
numbers stay.

| buffer / build | d1 | d2 | d3 | d4 | d5 | lag (ps) |
|---|---:|---:|---:|---:|---:|---|
| inv_chain, real gate, silicon maps, K = 7 — uncalibrated | +2.3 | +3.8 | −4.7 | −94.6 | −100 | collapse |
| inv_chain, same, **calibrated at 104 ps** | **+1.7** | **+5.7** | **+10.4** | **+6.1** | **+18.8** | **−6 … +9** |
| inv_chain, **file only** (IBIS gate, prior maps, K = 7), calibrated | **−6.5** | **−4.1** | **−0.1** | **−10.5** | **−7.9** | **−17 … +1** |
| ex2, file only (2-parameter prior, x_lin 0.45), uncalibrated | −9.5 | −15.1 | −18.4 | −22.6 | −27.6 | −60 … +33 |
| ex2, same, **calibrated at 810 ps** | **−6.2** | **−6.9** | **−4.5** | **−0.3** | **+6.7** | **+10 … +31** |
| ex2, file only with the 3-parameter prior, calibrated | −27 | −37 | −40 | −42 | −41 | (vt hit 0; needs a drive-scale knob) |

(widths: inv_chain 135 / 119 / 111 / 106 / 104 ps; ex2 975 / 895 / 858 / 830 / 810 ps.)

**IBIS file + one stressed number reproduces the stressed pad within ±11 % on
inv_chain and ±7 % on ex2**, with lags of tens of ps, where native is dead
(inv_chain) or +140 ps (ex2) and the shipped model is +31…+74 %. The one
number is the gate maximum at the deepest width of interest, which a single
extra transistor run in the characterisation flow gives.

## 4. io_buf: the depth-scaled residual re-attached — half done

| build | d2354 | d2090 | d1853 | d1666 | d1505 | lag (ps) | gate d1505 |
|---|---:|---:|---:|---:|---:|---|---|
| shipped | +2.1 | +1.6 | −1.8 | −1.3 | −3.5 | 63 … 69 | 0.40 / 0.67 |
| chains, prior maps | −4.7 | −5.2 | −9.0 | −17.3 | −29.2 | −35 … −136 | 0.63 / 0.67 |
| chains, prior maps, **+ depth residual** | **+0.8** | **−0.8** | −6.6 | −16.6 | −29.3 | +12 … −115 | 0.61 / 0.67 |
| file only, + depth residual | −4.8 | −6.3 | −12.3 | −23.6 | −38.8 | −16 … −189 | 0.61 / 0.67 |

The residual fixes the two shallow widths outright. The three deep widths
stay low for a reason that is now isolated: the one- or two-stage form puts
the NOR's ramp 0.06 short of the real gate (0.61 vs 0.67), right where the map
is steepest in relative terms (a 25 % Ku error). The calibration knob of step 3
(the threshold) cannot raise a stage that already runs at full drive; io_buf
needs the ramp itself right — a constant-current ramp with a rounded top, not
the RC-like fit the optimiser chose (x_lin 0.98). Open.

## 5. Across the twelve buffers and the pulse train

**Pulse train, ex2 chain build** (`../pulse_train_2026-09-08_chain/`,
8 stressed pulses at 858 ps, 50 % duty):

| | pulse 1 | 2 | 3 | 4–8 |
|---|---|---|---|---|
| transistor peak (V) | 1.085 | 1.406 | 1.438 | 1.444 |
| native peak error / lag | +247 mV / −38 ps | −74 / +165 | −106 / +140 | −114 / +136 |
| **chain** peak error / lag | **−70 mV / +25 ps** | **+2 / −5** | **−3 / +10** | **−7 / +10** |

No accumulation, and after the first pulse the chain tracks the train to
7 mV and 10 ps. The first-pulse −70 mV is the single-pulse −5 %.

**Nine variants, file-only recipe** (family priors, K fixed at the base
buffer's count, x_lin 0.45, no calibration — the honest "IBIS file in, nothing
else" run): see the table appended below.

| variant (depth 90 → 50 %) | shipped, peak % | **file-only chain**, peak % | shipped lag (ps) | chain lag (ps) |
|---|---|---|---|---|
| ex2_base | +6 / +16 / +30 / +49 / +75 | −13 / −21 / −24 / −23 / −21 | 152 … 300 | 1 … 16 |
| ex2_weak | +3 / +12 / +25 / +44 / +71 | **+3 / −2 / −9 / −9 / −5** | 159 … 300 | 41 … 72 |
| ex2_nomiller | +5 / +15 / +29 / +48 / +77 | −12 / −20 / −23 / −22 / −19 | 152 … 300 | −3 … 18 |
| ex2_skewp | +5 / +12 / +25 / +43 / +68 | −0 / −13 / −21 / −22 / −21 | 142 … 300 | −40 … 29 |
| ex2_slowpre | +2 / +8 / +18 / +32 / +51 | −9 / −17 / −21 / −24 / −27 | 88 … 300 | −16 … 4 |
| inv_base8 (7 depths) | −0 / +2 / +6 / +10 / +21 / +40 / +63 | **−1 / +0 / +1 / +2 / +4 / +3 / +2** | 9 … 64 | −15 … −8 |
| inv_weak | −2 / +1 / +6 / +16 / +35 | **−2 / −2 / +1 / +4 / +10** | 3 … 47 | −22 … −4 |
| inv_skewp | −1 / +2 / +9 / +18 / +36 | **−2 / −1 / +3 / +7 / +10** | 7 … 50 | −22 … −5 |
| inv_stage4, K = 7 (wrong count) | −0 / +1 / +3 / +5 / +12 / +25 / +39 | +0 / +2 / +5 / +7 / +15 / +28 / +46 | 7 … 39 | −23 … 1 |

(The "shipped" rows here are regenerated with the clamped threshold, so the
inv rows are the honest shipped error; K = 3 for the ex2 family, 7 for inv;
prior3 family values; x_lin 0.45; no calibration; the ex2 family at 1.7 pF and
the inv family at 0.6 pF.)

* **inv family**: the file-only chain is within ±10 % on inv_base8, inv_weak and
  inv_skewp at every depth, with lags of −22…−4 ps, where the shipped model
  runs to +35…+63 % at 50 % depth. inv_stage4 gets no better with K = 7: its
  chain has four stages, and the count must follow the buffer (a K = 4 run is
  appended below).
* **ex2 family**: the error changes sign and shrinks by 2–4×: −21…−27 % at
  50 % depth against +51…+77 %, lags within ±40 ps against 300. ex2_weak is
  within ±9 % at every depth. The family-wide −20 % is the same under-drive
  seen on ex2 itself before calibration (§3): the stage threshold from the
  full-swing fit is a little high, and one stressed point per buffer would
  pull it in as it did on ex2 (−28 → +7 %).

**Twelve buffers, then**: the current-limited chain with a physics map, from the
IBIS file alone, replaces a +35…+77 % stressed error with −27…+10 % on ten of
twelve (inv_stage4 needs its own K; io_buf needs its ramp), and one stressed
number per buffer brings ex2 and inv_chain inside ±11 %.

**inv_stage4 with its own stage count**: K = 4 gives −1 / +1 / +3 / +4 / +11 /
+22 / +37 % (K = 5: +42 % at the deepest), no better than K = 7 or the shipped
model. Its chain gate is already full at every depth (model 1.00), so the
stressed over-drive is not a predriver effect on this buffer: with only four
fast stages the pulse reaches the output gate intact, and what is left is the
output stage — the map for this variant is not the inv_chain family prior, or
its C_comp is not 0.6 pF. It is the one buffer of the twelve whose stressed
error the chain cannot touch, and the right next test is its own silicon map.

---

# Round 3: the calibration made real, the map closed, the recipe as one command

## 6. Which single number to calibrate on — the gate maximum is the wrong one for fast chains

The gate probe was added to the flow for all nine variants
(`scripts/variant_gate_probe.py`, `../variant_gate_probe_2026-09-10/gate_max.json`:
one full-swing and one deepest-width transistor run each with the last
predriver node probed). Calibrating the chain on that gate maximum worked on
the ex2 family (all five within −5…+15 %) but made the inv family *worse*
(inv_base8 +36 % at 50 % depth against +2 % uncalibrated). The reason is a
lesson about the physics: on a fast chain the pad depends on the gate pulse's
**width** as much as its height, and two chains with the same gate maximum can
differ by 10 ps of gate time and 30 % of pad. The full-swing fit is degenerate
in the stage threshold (vt 0.23 and 0.44 both fit inv_base8's full swing to
rms 0.0045), and the gate maximum does not resolve it in the direction the pad
needs.

So the calibration target became the **pad peak itself at one stressed width**
(`--calib-pad DEPTH`): one extra transistor run of the pad, no internal probe,
bisection on the stage threshold in ngspice, the drive scale as fallback. That
is a cheaper measurement and the quantity that matters.

## 7. Twelve buffers, IBIS file + one stressed pad run

| buffer | shipped (clamped threshold), peak % at depth 90 → 50 | **file + one pad point**, peak % | lag (ps) |
|---|---|---|---|
| ex2 (matrix) | +4 / +13 / +26 / +46 / +74 | −6 / −7 / −5 / −0 / +7 (gate-max point) ¹ | 10 … 31 |
| ex2_base | +6 / +16 / +30 / +49 / +75 | **−6 / −7 / −6 / −3 / +1** | 12 … 16 |
| ex2_weak | +3 / +12 / +25 / +44 / +71 | **−5 / −7 / −8 / −5 / +2** | 47 … 53 |
| ex2_nomiller | +5 / +15 / +29 / +48 / +77 | **−6 / −7 / −6 / −3 / +0** | 11 … 14 |
| ex2_skewp | +5 / +12 / +25 / +43 / +68 | **−6 / −9 / −10 / −7 / −1** | −10 … −2 |
| ex2_slowpre | +2 / +8 / +18 / +32 / +51 | **−5 / −5 / −4 / −2 / −0** | −3 … 39 |
| inv_chain (matrix) | +2 / +8 / +18 / +37 / +66 | **−6 / −3 / +2 / −7 / −4** | −17 … +2 |
| inv_base8 (7 depths) | −0 / +2 / +6 / +10 / +21 / +40 / +63 | **−0 / +2 / +4 / +5 / +7 / +3 / −7** | −4 … +5 |
| inv_weak | −2 / +1 / +6 / +16 / +35 | **−2 / −1 / +1 / +3 / +2** | −7 … +4 |
| inv_skewp | −1 / +2 / +9 / +18 / +36 | **−2 / +0 / +3 / +5 / −2** | −7 … +5 |
| inv_stage4 (7 depths, K = 4) | −0 / +1 / +3 / +5 / +12 / +25 / +39 | **+2 / +3 / +5 / +6 / +9 / +9 / −0** | 2 … 31 |
| io_buf | +2 / +2 / −2 / −1 / −4 (peak); pedestal + bump | chains + depth residual: +1 / −1 / −7 / −17 / −29 | |

¹ ex2 (matrix) used the gate-maximum point with the two-parameter prior; the
three-parameter prior with the drive-scale fallback gives −5 / −8 / −6 / +0 / +11.

**Eleven of twelve buffers inside ±10 % at every stressed depth, with lags of
tens of picoseconds, from the IBIS file plus one stressed pad run.** The
shipped model was +35…+77 % and 150–300 ps late on the same cases; native is
dead on the ex2 family and inv_stage4.

## 8. What else this round settled

* **inv_stage4's map is the family map** to g = 0.8 (silicon 0.817 vs prior
  0.823) and saturates a little later (gs 0.90 vs 0.87); its over-drive was the
  chain passing the pulse too well (model gate 1.00 where the real vout3
  reaches 0.90), i.e. a predriver effect after all — the pad calibration is the
  right fix, and its own stage count (4) is needed. `../variant_gate_probe_2026-09-10/inv_stage4/silicon_map.png`.
* **io_buf's gate is not a current-limited stage.** Forcing a constant-current
  ramp (x_lin 0.1–0.3) made the deep widths worse (gate 0.56–0.59 vs 0.67); the
  real n2 ramp decelerates like an RC but starts steeper than any one time
  constant. io_buf is linear end to end (`../predriver_stages_2026-09-09/`), so
  the right command for it is the *measured step response itself* (two
  stopwatches, one per edge direction, and P = S_rise(t − t_on) + S_fall(t −
  t_off) − 1), not a fitted form. Not built; the evidence is the superposition
  test (within 0.035 of the real gate at every width).
* **The converter now clamps the input threshold** (inv_chain 0.9 V); every
  variant's "shipped" row above is the honest one.
* **The recipe is one command**: `scripts/build_chain_model.py --ibis … --supply
  … --family … [--ccomp] [--calib W GMAX] --out driver.sub` reproduces the
  prototype's chain and maps line for line on ex2 (verified by diff). Pad
  calibration lives in the prototype (needs the reference pad); the builder
  takes the gate-max form or the already-calibrated numbers.

---

# Round 4: io_buf's step-response command, C_comp per variant, the builder complete

## 9. io_buf: the measured step response as the command (`scripts/gate_step_prototype.py`)

Built into the model: a 30 ps delayed copy of the digital input marks each
edge, a latch samples the edge time, and the elapsed times since the last
rising and falling edge index two pwl tables holding the gate's own full-swing
step responses; GUP = S_rise + S_fall − 1, clipped, and the same for GDN from
the NMOS-gate path. (A first version with a 3 ps edge window latched 1.3 ns
short — the integrator could not resolve a 0.2 ps tracking constant; 30 ps and
2 ps fixed it.)

| build | full-swing gate rms | d2354 | d2090 | d1853 | d1666 | d1505 | lag (ps) | gate d1505 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| shipped | — | +2.1 | +1.6 | −1.8 | −1.3 | −3.5 | 63 … 69 | 0.40 / 0.67 |
| chains + depth residual (round 3) | 0.035 | +0.8 | −0.8 | −6.6 | −16.6 | −29.3 | +12 … −115 | 0.61 / 0.67 |
| **step responses + depth residual** | **0.029** | −5.2 | −6.5 | −12.7 | −17.5 | −25.0 | −1 … −107 | 0.63 / 0.67 |
| step responses, pad-calibrated at d1505 | — | not obtained: the second bisection run stalled ngspice at 16.3 ns (the io_buf stall of the replay round, 626 MB raw); the calibration needs that stall solved first | | | | | | |

The step-response command draws the ramp the fitted stage could not (full-swing
gate rms 0.029 vs 0.035) and still sits 0.04 low at every stressed width
(0.83 / 0.78 / 0.73 / 0.68 / 0.63 vs 0.88 / 0.83 / 0.77 / 0.72 / 0.67): the
superposition test itself had this 4 % short-fall (`../physics_map_gate_2026-09-10/`,
0.841 vs 0.876). io_buf's truncated ramp runs 4 % higher than its own step
response predicts — a small super-linearity at the top of the NOR's ramp.
Near the map's threshold that 0.04 is 25 % of Ku, hence the deep widths. A
pad-peak calibration on the rise's time-scale is the same one-point fix as on
the chains; its result is appended below.

## 10. C_comp per variant (`scripts/variant_ccomp_loop.py`, `../variant_gate_probe_2026-09-10/ccomp_loop.json`)

| variant | declared (pF) | loop at declared | loop-minimising (pF) |
|---|---:|---:|---:|
| ex2_base / nomiller / slowpre | 5.00 | 0.48 / 0.50 / 0.34 | **1.75** |
| ex2_weak / skewp | 5.00 | 0.63 / 0.55 | **2.00** |
| inv_base8 / stage4 | 0.47 | 0.09 / 0.09 | 0.50 |
| inv_weak | 0.47 | 0.25 | **0.30** |
| inv_skewp | 0.47 | 0.14 | 0.40 |

The 3× C_comp error is family-wide on ex2 (the same characterisation
produced all five files); the 1.7 pF used for the family was right to ±0.25.
The inv family sits within ±0.2 pF of the declared value. Rebuilt with their
own values: inv_weak (0.3 pF) −3…+6 %, inv_skewp (0.4 pF) −1…+8 % — the same
as at 0.6 pF; the pad calibration absorbs a C_comp error of that size.

## 11. The builder is complete

`scripts/build_chain_model.py` now takes `--calib-pad PAD_CSV W_PS` — one
stressed transistor pad waveform — and does the ngspice bisection itself.
Run end to end on inv_chain from the IBIS file and the 104 ps pad waveform:
K = 7 from the plateau, threshold 0.42, drive scale 1.045 (identical to the
prototype's calibration); with the family prior3 map and x_lin 0.45 the scored
build is −4 / −3 / −2 / −10 / −1 % — but 50–60 ps early, because the drive
scale (the fallback when the threshold cannot bracket the target) speeds the
whole chain up. The threshold is the right first knob; when the fit lands on a
chain that swallows the pulse at every threshold (x_lin fixed, fast family),
a two-parameter calibration (threshold and drive, on the peak and the lag) is
the next refinement.

## 12. Pulse trains through the calibrated file-only builds — a second characterisation point is needed

`../pulse_train_2026-09-08_chain_fileonly/` (8 stressed pulses at 50 % duty;
peak error in mV and lag in ps per pulse):

| build | pulse 1 | pulse 2 | pulses 3–8 |
|---|---|---|---|
| ex2, transistor peaks (V) | 1.085 | 1.406 | 1.438 → 1.444 |
| ex2, native | +247 / −38 | −74 / +165 | −106…−114 / +136 |
| ex2, chain from the real gate (round 2) | −70 / +25 | +2 / −5 | −3…−7 / +10 |
| **ex2, file-only chain, calibrated at 810 ps** | −37 / −27 | −117 / −5 | **−126…−130 / −8** |
| inv_chain, transistor peaks (V) | 0.002 | 1.028 | 1.261 → 1.304 |
| inv_chain, native | 0 / +7 | +210 / +25 | −18…−62 / +29 |
| **inv_chain, file-only chain, calibrated at 104 ps** | −2 / −104 | −24 / +10 | **−255…−299 / +11** |

Both file-only chains are right on the first pulse (what they were calibrated
on) and wrong on the settled train: ex2 −9 % and inv_chain −23 % on pulses
3–8, where the chain built from the real gate was within 7 mV. On a train
each pulse starts before the stages have returned to rest, so the chain's
behaviour for a *partial-from-partial* input is exercised — the file-only
fit, pinned at one point, gets the from-rest case right and this case wrong;
the real-gate fit gets both. Timing is fine on both (lags ≤ 11 ps).

So the one stressed pad run fixes the single-pulse regime and the train shows
the next degree of freedom. A stressed train is the natural second
characterisation point: fit the threshold on the single pulse and the drive
(or x_lin) on the train's settled peak. Not done here.

---

# Round 5: the train as a second characterisation point, and the chain in the converter

## 13. Two-point calibration (`scripts/gate_chain_train_calib.py`, `../gate_chain_train_calib_2026-09-10/`)

For each resistive fraction x_lin the chain is refitted at full swing, its
threshold calibrated on the single stressed pulse (pad peak), and the 8-pulse
stressed train run; the x_lin whose settled train peak matches is chosen.

**ex2** (single pulse 810 ps, train 858 ps):

| x_lin | single pulse: peak / lag | train, settled pulses: peak / lag | all five widths (peak %) | lags (ps) |
|---:|---|---|---|---|
| 0.25 | +1.6 % / 140 ps | **−2.7 % / 134 ps** | **−0.3 / +0.1 / +1.4 / +1.9 / +1.6** | 140 … 162 |
| 0.35 | +0.8 / 77 | −7.1 / 74 | | |
| 0.45 | −0.1 / 15 | −9.3 / 24 | (round 3: −6…+7) | 10 … 31 |
| 0.60 | +1.6 / −13 | −11.5 / −18 | | |
| 0.80 | −1.1 / −8 | −13.6 / −27 | | |
| 0.45, discharge fraction 0.35 × | +1.4 / 51 | −25.1 / 91 | — | (the two other ratios stalled ngspice) |

The train fixes x_lin, and x_lin 0.25 gives every single-pulse peak within
±2 % *and* the settled train within 3 % — the first build that is right on
both — but the pulses arrive 140–160 ps late, while x_lin 0.45 has the timing
right (15–30 ps) and the train 9 % low. **Peak and timing cannot both be met
by one resistive fraction**, and a separate fraction for the discharge
direction made the train worse (−25 %). What remains is a genuine limitation
of the four-number stage: the real stage's current-limited *return* and its
arrival time are not tied together the way `r(x) = min(1, x/x_lin)` ties them.
The next refinement is a stage law with an independent delay (or a
saturation current that depends on the previous stage's level, the h(u)·r(v)
product replaced by a proper I(Vgs, Vds)), not another calibration point.

**inv_chain** (single pulse 104 ps, train 111 ps): the settled train is
−18…−21 % at every x_lin from 0.25 to 0.8, with the single pulse within ±3 %
each time — the train shortfall is not the resistive fraction. A sweep of a
slower stage discharge returned identical train numbers for three scales and
is treated as inconclusive (suspected run cache; not debugged). Open.

## 14. The chain is in the converter package

`tools/pybis2spice/pybis2spice/chain_command.py` carries the pure-text part of
the recipe (the stage block, the mid-supply comparator, the shared gate, the
prior maps); `scripts/build_chain_model.py` now calls it, and its ex2 output is
identical to the prototype's line for line. Fitting and calibration stay in
the script because they need ngspice runs. The remaining integration work is
a converter option that runs the full-swing fit itself.

## Where the direction stands after five rounds

* Single stressed pulses: eleven of twelve buffers within ±10 % from the IBIS
  file plus one stressed pad run (round 3).
* Stressed trains: ex2 within 3 % on the settled pulses with the train as a
  second point, at the cost of 140 ps of lag; inv_chain not yet.
* io_buf: gates right, pad short by the 4 % its own ramp exceeds linearity; its
  calibration blocked by the ngspice stall.
* The stage law itself is now the frontier: return dynamics and arrival time
  need one more degree of freedom than the four numbers give.
