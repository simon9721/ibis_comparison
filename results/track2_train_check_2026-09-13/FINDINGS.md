# Track 1 vs track 2, 2026-09-13

Track 1 = the IBIS file plus one short-pulse pad measurement (hand-off level).
Track 2 = track 1 plus one more piece of transistor information: the measured Ku/Kd map
against the gate (ex2, inv_chain) or the measured step response of the last stage (io_buf).

## Single pulse (peak error vs the transistor, 90 → 50 % stress; scripts gate_chain_prototype.py / gate_step_prototype.py)

| buffer | build | 90 | 80 | 70 | 60 | 50 | lag ps |
|---|---|---|---|---|---|---|---|
| ex2 | track 1 (`ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810`) | −7 | −9 | −7 | −5 | 0 | 14…17 |
| ex2 | track 1, calibrated on the real gate peak (`…_calib810`) | −6 | −7 | −4 | 0 | +8 | 10…33 |
| ex2 | track 2, measured map (`ibis_silicon_K3_xlin0.45_calibpad810`) | 0 | 0 | −1 | −2 | 0 | 4…12 |
| inv_chain | track 1 (`ibis_prior_K7_prior0.49_0.6_calibpad104`) | −6 | −4 | 0 | −10 | −8 | −17…1 |
| inv_chain | track 1, gate-calibrated (`…_calib104`) | −6 | −3 | +2 | −9 | −8 | −17…2 |
| inv_chain | track 2, measured map (`ibis_silicon_K7_calibpad104`) | −4 | −1 | +4 | −7 | −7 | −14…5 |
| io_buf | track 1, chain (`ibis_prior_prior0.5_0.78_calibpad1505`) | +4 | +7 | +8 | +5 | +1 | 11…−58 |
| io_buf | track 1, file step response (`ibis_prior_calibpad1505`) | +3 | +4 | +4 | +4 | 0 | 37…−18 |
| io_buf | track 2, measured step response (`real_prior_calibpad1505`) | +2 | +3 | +3 | +1 | −2 | 24…−28 |

Calibrating on the gate peak instead of the pad peak changes nothing: the pad point loses
nothing by going through the map. The measured map removes ex2's 5–9 % low bias and halves
its lag; on inv_chain it is worth ~2 % because that chip's error is the chain's cliff below
60 %, not the map. io_buf's peak is within 4 % on both step builds; the pull-down bump at
1.7 ns still arrives at ~2.2 ns and is too tall at the deepest width (the residual).

## Stressed train (8 pulses, 50 % duty, deepest matrix width, 50 ps edges; trains.png)

Read from the waveforms (the per-pulse scorer in track2_train_check.py mis-windows io_buf's
pulse 1 and ex2's peak shift; the settled numbers agree with the plot):

| buffer | build | pulse 1 | settled pulses 4–8 |
|---|---|---|---|
| ex2 | track 1 | −9 % | −9.5 % |
| ex2 | track 2 | −2 % | −3.5 % |
| inv_chain | track 1 / track 2 | 0 / +2 % | −22 / −21 % |
| io_buf | track 1 / track 2, single-slot step command | 0 % | −41 / −43 % |
| io_buf | track 2, 3-slot step command (`real_prior_calibpad1505_slots3`) | −3 % | **−4.6 %**, peak shift +19 ps |

- ex2: the measured map fixes the train as well as the single pulse.
- inv_chain: the transistor's settled pulses are 25 % taller than its first (stages that
  have not returned to rest are pre-charged); both chains keep pulse-1 height. That is the
  recovery number, which neither the file nor the map contains; it needs a train measurement.
- io_buf: the single-slot step-response command keeps only the most recent edge of each
  direction, and io_buf's 2.8 ns rise response has not settled within the 1.8 ns half period,
  so pulses 2–8 collapse to 0.52 V. `gate_step_prototype.py --slots 3` superposes the last
  three pulses (one counter; a slot holds a rise and its own fall, cleared together, so
  dropping a settled pulse keeps the sum balanced): single pulse unchanged (+2/+3/+3/+2/−1 %),
  train settled −4.6 %. Left: the rising flank of pulses 2–8 starts ~0.4 ns late and the
  small pull-down bump between pulses is missing (the residual).

## Variants with the measured map (variant_silicon_maps.py: two fixture runs + gate probe per variant, 1 ps edges like their stress cases)

Peak error vs the transistor, 90 → 50 % (inv_base8 and inv_stage4: 100/90/85/80/70/60/50); track 1 from the evidence page.

| variant | track 1 (file + one pad point) | track 2 (+ measured map) | track 2 lag ps |
|---|---|---|---|
| ex2_base | −6 / −7 / −6 / −3 / +1 | +2 / +2 / +3 / −1 / −1 | 5 … 9 |
| ex2_weak | −5 / −7 / −8 / −5 / +2 | −3 / −4 / −7 / −2 / +4 | 47 … 76 |
| ex2_nomiller | −6 / −7 / −6 / −3 / 0 | +2 / +3 / +4 / +2 / +2 | −1 … 10 |
| ex2_skewp | −6 / −9 / −10 / −7 / −1 | 0 / −1 / +3 / +2 / +4 | 17 … 36 |
| ex2_slowpre | −5 / −5 / −4 / −2 / 0 | +2 / +3 / +2 / 0 / −4 | −13 … 16 |
| inv_base8 | 0 / +2 / +4 / +5 / +7 / +3 / −7 | +1 / +3 / +5 / +7 / +10 / +10 / −3 | 1 … 13 |
| inv_weak | −2 / −1 / +1 / +3 / +2 | +1 / +2 / +5 / +6 / −1 | 9 … 22 |
| inv_skewp | −2 / 0 / +3 / +5 / −2 | 0 / +2 / +4 / +6 / −1 | 6 … 19 |
| inv_stage4 (K = 4) | +2 / +3 / +5 / +6 / +9 / +9 / 0 | +2 / +3 / +5 / +6 / +10 / +11 / +2 | 22 … 28 |

The measured map lifts the whole ex2 family from a 5–10 % low bias to ±4 % (ex2_weak keeps a
50–75 ps lag); on the inv family it is neutral to slightly worse, as on inv_chain itself.
Full-swing pad rms grows (ex2_base 51 mV vs shipped 14) because the chain fit is looser
than the tables' own replay.

## Recovery on inv_chain (why the train is −21 %)

Probing every stage of the transistor on the train (`inv_chain/transistor_edge50_probed`):
every stage still reaches full swing on every pulse; what changes is the pulse WIDTH. On
pulse 1 each stage narrows it (input 111 ps → vout7 90 ps, ~3 ps per stage, every stage
starting from rest); on the settled train each stage widens it (~+6 ps per stage, vout7
133 ps) because 3–9 % of charge is left in each stage between pulses. At 111 ps the pad is
on the cliff, so 90 → 133 ps of gate width is 0.71 → 0.91 on the pad. The chain narrows
pulse 1 like the transistor (87 ps) and never widens: its stages drain to exactly 0 in the
gap. Slowing the drain (`gate_chain_train_calib.py --sdn-scales`) breaks the single pulse
(+25…+103 %) before it widens the train: wrong knob.

`recovery_law_probe.py` (python chain refitted to the real full-swing gate under candidate
laws): a square-law drive (h = clip((x−vt)/(1−vt))², vt 0.42, x_lin 0.66) narrows pulse 1 to
exactly 90 ps and widens the settled train to 140 ps (transistor 133) with 4–17 % residual;
the linear law with the same fit only reaches 98 → 132. In ngspice, the square law fitted
from the IBIS tables (`ibis_silicon_K7_calibpad104_p2`: x_lin 0.17, vt 0.30, drive scale
1.10) gives the best inv_chain single pulse so far (−4 / −1 / +4 / −4 / +1) but still
−19.7 % on the train: the table-derived fit has no resistive tail, so no residual. ex2 with
p = 2: +2 / +5 / +5 / +1 / −1, train −5 % (slightly worse than p = 1).

The truth-bounded square-law chain in ngspice (`real_silicon_K7_p2`: fitted to the real
gate, x_lin 0.61, vt 0.45, no calibration) swallows the pulse below 119 ps (−89 … −100 %),
unlike the python probe with the same law. The probe drove the chain with the 50 ps ramped
input; the ngspice chain sees the mid-supply comparator (a 0/1 step), and a square-law
stage responds very differently to the two. With the step input (`recovery_law_probe.py --step-input`)
the plain linear law fitted to the real gate (s 22.9/22.3, vt 0.55, x_lin 0.48) already
reproduces it in python: pulse 1 88 ps (transistor 90), settled 128 (133), residual 6–14 %.

**Confirmed in ngspice**: the truth-bounded linear chain `real_silicon_K7` (fitted to the
real gate, no calibration) on the train: pulse 1 −2.3 %, settled **+1.7 %**, shift +19 ps.
The chain law can carry the recovery. What cannot is the fit from the IBIS tables, which
lands at x_lin 0.13 / vt 0.48 / s 18 (no resistive tail, so no residual); the pad-point
calibration then moves vt or the drive, never the tail. The same truth-bounded chain has
the single-pulse cliff 5 ps too early (−95 / −100 % at 106 / 104 ps, 2026-09-10 run), so
on inv_chain the two measurements pull the four stage numbers to different corners: the
deep single pulse wants a low threshold, the train wants a long tail. Next: a two-point
calibration that fits (vt, x_lin) jointly to the single-pulse peak and the settled train
peak, instead of vt-then-drive on the single pulse alone.

## Bench notes

- The 2026-09-08 transistor train reference used 1 ps input edges; the single-pulse matrix,
  the calibration and the model trains use 50 ps. On inv_chain (threshold 1.4 V on 1.8 V) that
  changes the effective width by 28 ps. The transistor trains here are re-run with 50 ps edges
  (`<dev>/transistor_edge50`). The earlier `gate_chain_train_calib` sweep's "pulse 1 −95 %" on
  inv_chain was this mismatch plus input-period windowing, not the model.
- Measured maps exist only for ex2, inv_chain, io_buf (full_swing_fixtures_2026-09-09); the
  nine variants would need their two-fixture full-swing runs before track 2 can be scored on them.

## Variants on a train (variant_train_check.py, 2026-09-14; 8 pulses at the 50 %-depth width, 1 ps edges; settled = pulses 4-8)

| variant | W ps | track 1 settled | track 2 settled |
|---|---|---|---|
| ex2_base | 812 | −13 % | −5.5 % |
| ex2_weak | 706 | −12 % | −9.5 % |
| ex2_nomiller | 809 | −14 % | −6 % |
| ex2_skewp | 757 | −22 % | −9 % |
| ex2_slowpre | 1094 | −18 % | −13 % |
| inv_base8 | 102 | −9.5 % | −11.5 % |
| inv_weak | 114 | −5 % | −11 % |
| inv_skewp | 100 | −0.5 % (pad never returns; pulses merge) | +1 % |
| inv_stage4 | 83 | −2 % | −16 % |

Pulse 1 agrees with the single-pulse matrix within a few percent for every build (the scorer
now locates pulse 1's own peak; a plain argmax picked the taller pulse 2 and shifted every
window by one pulse, which is what the earlier "−12 % on pulse 1" was). On the ex2 family
the measured map halves the settled-train error but 5–13 % remains: these trains are at the
50 %-depth width, deeper than ex2's own 858 ps train, so the recovery term is larger. On the
inv family track 2 is no better than track 1 on trains either.

## Drive law: square root (p = 0.5)

`recovery_law_probe.py --step-input` with the cliff check: fitted to the real gate, p = 0.5
gives gate max 0.99/0.96/0.91/0.85/0.80 at 135…104 ps (transistor 1.00/0.99/0.97/0.94/0.88;
linear law 0.98/0.94/0.84/0.64/0.40; square law collapses), pulse-1 width 96 ps (90),
settled 128 (133), residual 6–10 % (3–9 %), same full-swing rms. ngspice needs the law
shifted (pow(x + 1e-3, p) − 1e-3^p; the derivative of x^0.5 at 0 is refused). On ex2 the
square-root law is wrong: +6 / +9 / +10 / +4 / −5 % with 200 ps lag.

## inv_chain closed on both counts (2026-09-14): square-root law + real-gate fit + one pad point

`real_silicon_K7_calibpad104_p0.5` (K = 7 stages fitted to the real last-stage step response,
drive law h = clip((x−vt)/(1−vt))^0.5 with the 1e-6 shift, measured map, pad point at 104 ps
which only scaled the drive by 1.01):

| | 135 | 119 | 111 | 106 | 104 ps | train settled | full-swing pad rms |
|---|---|---|---|---|---|---|---|
| shipped | −8 | −8 | −2 | +11 | +31 % | — | 20 mV |
| linear law, real-gate fit (`real_silicon_K7`) | +2 | +4 | −5 | −95 | −100 % | +1.7 % | 22 mV |
| square-root, real-gate fit, no calibration | +2 | +6 | +8 | −16 | −21 % | −0.9 % | 23 mV |
| **square-root, real-gate fit + pad point** | **+3** | **+7** | **+10** | **−5** | **+1 %** | **−0.6 %** | **19 mV** |
| square-root, tables fit + pad point | −4 | −2 | +3 | −11 | −8 % | −21 % | 27 mV |

The square-root law removes the hard cliff (gate max 0.80 at 104 ps vs the linear law's 0.40;
transistor 0.88), and the real-gate fit carries the draining tail (x_lin 0.41) that the tables
cannot supply. The two together are the first inv_chain build within ±10 % on every single
pulse AND on the train. The tables route with the same law is still −21 % on the train (x_lin
0.10): for inv-type chips the tail must come from a train measurement.

Note the 1e-3 shift used first weakened the law near threshold by ~25 % and put the cliff back
(0.54 / 0.35); with 1e-6 ngspice agrees with the python probe.

Stand-in for a train-calibrated tail: the tables fit with x_lin pinned at the real-gate value
(`ibis_silicon_K7_xlin0.41_calibpad104_p0.5`) is fine on single pulses (−4 / −5 / −1 / −7 / −1 %)
but still −22.7 % on the train. The tail is not one number: the table-derived target gate
differs from the real step in a way that pinning x_lin does not repair (its s_up/s_dn come out
16.6/18.0 against 19.5/19.0). For inv-type chips the measurement that carries the recovery
is the last runner's full-swing step response itself (one probed run), not a pinned tail.

## Real-stage fit on the ex2 family (2026-09-14): trains closed, timing open

Chain fitted to the variant's probed last stage (`--source real`, plain law, x_lin free, pad
point at 50 %; `variant_silicon_maps.py --source real --p 1 --free-xlin`):

| variant | single-pulse peak 90 → 50 % | lag ps | train settled: track 1 / track 2 / real stage |
|---|---|---|---|
| ex2 (matrix) | −2 / −3 / −4 / −4 / +1 | 57 … 85 | −9.5 / −3.4 / **−0.7** |
| ex2_base | −2 / −3 / −5 / −5 / −3 | 66 … 82 | −13 / −5.5 / **+2.1** |
| ex2_weak | 0 / −1 / −1 / −3 / −1 | 150 … 163 | −12 / −9.5 / **+2.8** |
| ex2_nomiller | −2 / −3 / −4 / −5 / −2 | 67 … 86 | −14 / −6.3 / **+1.7** |
| ex2_skewp | 0 / −1 / −1 / −2 / +1 | 118 … 125 | −22 / −9.4 / **+0.5** |
| ex2_slowpre | −1 / 0 / −1 / −1 / −2 | −77 … −29 | −18 / −13 / **−6.6** |

The real last-stage step response carries the recovery on the ex2 family exactly as on
inv_chain: every train within 7 %, most within 3 %. The cost is single-pulse timing: the
real-stage chain lands at a low threshold (vt 0.27 vs 0.53 from the tables) and is 60–160 ps
late (slowpre: early) where the table-fitted chain is within 12 ps. Peaks are right; the whole
pulse is shifted. Next: find where the shift comes from (rise or fall of the chain gate vs
the real gate under stress) and whether a threshold from the tables + tail from the real step
gives both.

Return-time calibration (`--calib-fall`, scale s_dn until the stressed pad's half-peak return
matches, then re-calibrate the peak): on ex2's real-stage chain the return time closes (−5 ps)
but the peak drops 36 %, the drive re-scale restores it and the lag flips to −40…−84 ps
(early) with the full-swing rms at 81 mV. The discharge rate alone is too blunt a knob: the
stressed return and the peak are coupled through the stage. Negative result; not adopted.

## inv family with the inv-type recipe (real last-stage fit, square-root law, one pad point; 2026-09-14)

`variant_silicon_maps.py --only inv_* --source real --p 0.5 --free-xlin`:

| variant | single-pulse peak (shallow → 50 %) | lag ps | full-swing rms (shipped) |
|---|---|---|---|
| inv_base8 (K 7, 7 depths) | +2 / +3 / +5 / +6 / +7 / +4 / −1 | 18 … 26 | 27 (10) mV |
| inv_weak | +1 / +2 / +4 / +5 / −2 | 27 … 35 | 29 (7) |
| inv_skewp | +1 / +2 / +5 / +5 / −3 | 20 … 29 | 27 (8) |
| inv_stage4 (K 4, 7 depths) | +1 / +1 / +1 / +1 / +1 / +1 / 0 | 29 … 32 | 49 (9) |

Every inv variant within +7 % at every depth with the same recipe as inv_chain; inv_stage4
within 1.5 %. The full-swing pad rms is 2–5× the shipped model's (the chain is a coarser
replay of the tables than the tables themselves); acceptable for now, to revisit when an
error budget is set.

## All nine variants on trains, three builds (variant_train_check.py, 2026-09-14 evening)

Settled pulses 4–8, peak error vs the transistor:

| variant | track 1 (file + pad point) | track 2 (+ measured map) | real last stage + pad point |
|---|---|---|---|
| ex2_base | −13 | −5.5 | **+2.1** |
| ex2_weak | −12 | −9.5 | **+2.8** |
| ex2_nomiller | −14 | −6.3 | **+1.7** |
| ex2_skewp | −22 | −9.4 | **+0.5** |
| ex2_slowpre | −18 | −13 | **−6.6** |
| inv_base8 (sqrt) | −9.5 | −11.5 | **−1.7** |
| inv_weak (sqrt) | −4.7 | −11 | **−3.1** |
| inv_skewp (sqrt) | −0.5 | +1.4 | **+1.7** |
| inv_stage4 (sqrt) | −1.9 | −16 | **+1.2** |

With the chain fitted to the real last stage's full-swing step (plain law on the ex2 family,
square-root law on the inv family) and one pad point, every one of the eleven push-pull
buffers is within 7 % on the settled train (nine within 3.5 %) and within ±7 % on single-pulse
peaks. The remaining single-pulse cost is timing on the ex2 family (60–160 ps lag; peaks
right), where the table-fitted chain is within 12 ps. Pulse-1 numbers match the single-pulse
matrix.

**Toward one framework.** The recipe is now the same for all eleven except the drive-law
exponent (1 vs 0.5). The wrong exponent shows up after the pad-point calibration as a large
residual single-pulse error (ex2 with 0.5: +10 %; inv_chain with 1: −95 % cliff), so the
exponent can be chosen automatically from the same one stressed run: fit both, calibrate both,
keep the one with the smaller calibrated error. Untested as a procedure; every ingredient is
already measured. io_buf (linear predriver) still needs its own command form.

## Why the real-stage chain is late on ex2, and the fix (joint_fit_probe.py, 2026-09-14)

Python chain, K = 3, plain law, targets = the probed transistor. Fitted to the full-swing
step only (what `--source real` does), the last stage returns 52–58 ps late on every stressed
width (peaks within 0.04): that is the pad lag. Adding the stressed gate at one width to the
fit moves vt 0.28 → 0.34 and s_up/s_dn ×1.07 (x_lin unchanged, 0.46) and closes the return to
+14…+28 ps, with the train widening unchanged (settled 1076 vs 1096 ps before; real 988).
So the full-swing step under-determines the threshold, and the pad point should set it:
`--calib-timing` bisects vt on the stressed pad's return time, refitting the other three
numbers at full swing for each candidate, then the peak is set as before.

`--calib-timing` result on ex2: with the other three numbers refitted at full swing for each
candidate threshold, the stressed pad's return time barely moves (vt 0.07 → +190 ps, 0.27 →
+103, 0.52 → +101): no bracket, threshold left as fitted, lag unchanged (57–85 ps). Under the
full-swing constraint the threshold is not the lever on the pad's return; the python joint fit
gained its 40 ps on the GATE return by moving vt and both rates together, and only that
combination (stressed-gate information) reaches the pad. Open: the real-stage chain on
ex2-type chips keeps a 60–85 ps lag on single pulses with peaks and trains right; closing it
needs either the stressed last-stage probe in the fit or a richer stage law.

## Six open items, 2026-09-14 (evening) — results as they land

**Item 6, converter clamp: done.** `subcircuit.py` now writes `pwl(min(max(V(DIE,VSS), lo), hi), …)`
for B1–B4 (helper `clamped_die_str`). The regenerated open-drain gate-state model runs the
1 kΩ rise-then-fall bench without the hand patch: rest 0.080 V, 2.673 V at 17 ns, fall 50 %
1.227 ns, identical to the 09-11 hand-clamped diagnostic (`opendrain_risefall_2026-09-11/
gatestate_clamped_converter`). The C_comp half (5 pF declared vs 0.25 pF released) is a
characterisation item for s2ibispy, not the converter.

**Item 4, io_buf through the bucket chain: negative.** K = 6 stages fitted to io_buf's real
last stage: full-swing fit rms 0.065 (ex2/inv: 0.003–0.007), threshold collapses to 0, single
pulses +2 … +38 % with 150–200 ps lag. The decelerating linear ramp is not a row of buckets.
io_buf keeps the recorded-step form; the full-swing fit rms is the automatic tell (an order
of magnitude worse) that selects it.

**Item 5, full-swing accuracy (full_swing_check.py):** the real-stage chain is within 12–16 ps
on both edges of ex2 and 9–11 ps on inv_chain, rms 25–37 mV over the edge windows; the
file-fitted chain is 46–58 ps early on ex2. Both sit ~15–20 mV high on the settled high
level (the measured map's end value). Acceptable pending an error budget.

**Item 2, exponent selection:** on inv_chain the plain law with the real-stage fit AND the pad
point (`real_silicon_K7_calibpad104`) gives +2 / +6 / +9 / −5 / +2 %, lag ≤ 11 ps, full-swing
rms 14.9 mV (below shipped), train −2.1 %: as good as the square-root build. The pad point
lowered vt from 0.55 to 0.49 and stepped off the cliff. If the inv variants agree, the
exponent is not needed at all (one law for all eleven).

**Item 1, ex2 timing: closed at the reference level by the joint fit.** `--joint-stress 810`
(chain fitted to the full-swing step AND the probed stressed last stage at 810 ps, then the
pad point): single pulses −2 / −2 / −3 / −2 / +3 %, lag 18–42 ps (was 57–85), train settled
−1.0 %, full-swing rms 25.7 mV. The extra measurement is one stressed probe of the last stage
(the same node already probed at full swing, one more run). Being extended to the ex2
variants with `variant_silicon_maps.py --joint`. Side result: the square-root law with the
real-stage fit and pad point is also acceptable on ex2 (−2 / −2 / −2 / −1 / +3 %, lag 37–53
ps), so the exponent matters far less once the fit comes from the real stage.

**Item 2, exponent selection: resolved by becoming unnecessary.** `auto_exponent.py` scores
each exponent on what the recipe can see (calibrated peak, its lag, full-swing rms):

| | p = 1 | p = 0.5 | picked |
|---|---|---|---|
| ex2 | +0.9 %, 85 ps, 23.9 mV → 14.2 | +3.3 %, 53 ps, 29.3 mV → 14.5 | 1 |
| inv_chain | +1.6 %, 5 ps, 14.9 mV → 5.1 | +1.0 %, 15 ps, 18.9 mV → 6.3 | 1 |

With the chain fitted to the real last stage and the pad point setting the threshold, both
laws land within a few percent on both families, and the plain law scores slightly better on
both. The earlier need for the square root came from fits that could not lower the threshold
(cliff at 0.55); the pad point does that (0.55 → 0.49 on inv_chain). One law, no selector,
pending the inv-variant confirmation (`variant_silicon_maps.py --only inv_* --source real --p 1`).

**inv variants, plain law vs square root (real-stage fit + pad point):**

| variant | single pulses, plain | train, plain | train, sqrt |
|---|---|---|---|
| inv_base8 | +1 … +8 / +0.5 % | −1.8 % | −1.7 % |
| inv_weak | +1 … +6 / +1 % | −4.2 % | −3.1 % |
| inv_skewp | 0 … +6 / −1 % | +1.5 % | +1.7 % |
| inv_stage4 | +2 … +7 / −1 % | +8.1 % | +1.2 % |

One law (plain) holds within ±8 % on every buffer, single pulses and trains; the square root
is a refinement worth up to 7 % on the fast four-stage variant. The framework does not need
an exponent choice; the selector stays as an optional polish.

**Item 1 on the ex2 family (joint fit, one stressed last-stage probe per variant at 50 %):**

| variant | single-pulse peaks 90 → 50 % | lag ps (before: real-stage fit) |
|---|---|---|
| ex2_base | −2 / −3 / −4 / −4 / −2 | 22 … 33 (66 … 82) |
| ex2_weak | −8 / −10 / −12 / −8 / −1 | 0 … 33 (150 … 163) |
| ex2_nomiller | −2 / −3 / −4 / −5 / −2 | 20 … 33 (67 … 86) |
| ex2_skewp | −4 / −5 / −5 / −5 / 0 | 23 … 36 (118 … 125) |
| ex2_slowpre | −1 / 0 / 0 / +1 / +2 | −17 … 47 (−77 … −29) |

Timing closes across the family (lags now 20–36 ps except slowpre's spread); ex2_weak trades
its timing for −8 … −12 % peaks at the milder widths (its joint fit lands at vt 0.51, the
others at 0.34–0.45). Trains being scored.

Joint-fit builds on the ex2-family trains (settled): base +0.8, nomiller +0.5, slowpre −4.9
(all better or equal), but skewp −8.0 (was +0.5) and weak −17 (was +2.8). On those two the
stressed probe pulls the fit to a higher threshold (weak 0.51, skewp 0.45) with less
residual, so the recovery goes as the timing comes. Verdict for item 1: the joint fit closes
timing on all five and keeps the train on three; the four-number identical-stage law cannot
give both on ex2_weak and ex2_skewp. Choice per buffer today: real-stage fit (train within
3 %, 60–160 ps lag) or joint fit (lag ≤ 36 ps, train −8 / −17 %). A fifth stage number (a
separate tail time constant) is the next candidate, not tried.

**Item 3, io_buf pull-down chain (`gate_step_prototype.py --gdn-chain 3`):** GDN driven by 3
current-limited stages fitted to the real n3 step (vt 0.69, x_lin 0.44, rms 0.024) instead of
the replayed linear step; GUP keeps the recorded ramp. The pad's second hump moves from ~0.45
ns late to ~0.2 ns late and is still slightly too tall at 1505 ps; full-swing rms 20.9 mV
(was 24). The rise-scale bisection stalls ngspice at one candidate (the known io_buf stall),
so `--k-rise` takes the scale from the earlier calibration (1.056).

---

## 2026-09-17, item 5 (full-swing settled level): diagnosed, and it is the measured map

The open item read "the stage models track the full-swing edges within 16 ps but sit 15-20 mV
high on the settled level". Three measurements locate it, and it is not the stage chain.

**1. It is not the command layer.** `full_swing_check.py` reports the same high-level error for
two completely different command layers on the same buffer: ex2 file-fitted chain +20 mV and
real-stage chain +19 mV, despite edge errors of -58/-46 ps and -12/+16 ps respectively.
inv_chain: +14 mV for both. An error that does not move when the command layer is replaced is
not in the command layer.

**2. It is not the IBIS tables.** Solving the pull-up table against the actual bench load
(50 ohm, the full-swing probe deck) at the transistor's own settled pad voltage:

| device | transistor settled | load current | table I_pu at that voltage | error |
|---|---|---|---|---|
| ex2 | 1.5450 V | 30.900 mA | 30.892 mA | 0.03 % |
| inv_chain | 1.4220 V | 28.440 mA | 28.449 mA | 0.03 % |

Neither file declares a power clamp or a ground clamp (`iv_power_clamp` and `iv_gnd_clamp` are
both None), so at DC the pad equation is just Ku*I_pu + Kd*I_pd. The table reproduces the
transistor's DC operating point essentially exactly.

**3. It is the measured (silicon) Ku/Kd map, through Kd.** Reading every existing full-swing
build at 12 ns splits cleanly in two by which map it uses, on both devices:

| device | map | out at 12 ns | vs transistor | Ku | Kd |
|---|---|---|---|---|---|
| ex2 (1.5450 V) | prior (assumed) | 1.5421 V | -2.9 mV | 1.0006 | -0.0000 |
| ex2 | silicon (measured) | 1.5654 V | +20.4 mV | 1.0029 | **-0.0144** |
| inv_chain (1.4220 V) | prior | 1.4209 V | -1.1 mV | 0.9997 | -0.0000 |
| inv_chain | silicon | 1.4359 V | +13.9 mV | 1.0004 | **-0.0166** |

Every `*_prior*` build lands within 3 mV; every `*_silicon*` build is 14-20 mV high. At the
settled point the pull-down is fully off, so Kd must be 0; the measured map returns -0.0144,
which makes the pull-down branch *source* current and pushes the pad up. Ku also sits slightly
above 1 (1.0029). This is the same negative-coefficient artifact already documented at the
low-gate end of the solved Ku (gate-to-drain feedthrough plus conditioning): it is harmless
where the model does not read the map, and not harmless at the fully-on end, which the settled
level reads directly.

**Fix to test:** anchor the measured map endpoints (Ku and Kd exactly 0 at the off end, 1 at the
on end) rather than letting the solve's residual set them. Must be validated on the stressed
peaks too, not only the settled level, because the negative region carries the feedthrough bump.

## 2026-09-17, open-drain C_comp: the "20x" claim is a conflation, and the real gap is 3.0 vs 1.75

Chasing the open-drain C_comp characterisation item turned up a number being carried across
devices. Four distinct quantities are in play and three of them had been collapsed into one:

| quantity | value | where it comes from |
|---|---|---|
| declared in the open-drain file | **5.0 pF** | `ex2_opendrain.ibs`, `C_comp 5.0000pF` |
| single-fixture loop value, open-drain bench | **3.0 pF** | `opendrain_silicon_map.py`; the Kd-vs-gate map collapses to one curve on all eight widths (rms 0.008) against rms 0.034 at the declared 5.0 pF |
| two-fixture push-pull solve, same die | **1.75 pF** | recorded caveat in `opendrain_gatestate_2026-09-10/FINDINGS.md` |
| released / high-Z pad capacitance | **0.25 pF — but this is io_buf** | `cv_capacitance_2026-09-04`; `extract_pad_capacitance.high_z()` is commented "io_buf only" |

**The correction.** The standing claim that the open-drain file's C_comp is "twenty times the
released-state value" is 5.0 / 0.25, and that 0.25 pF is io_buf's high-Z measurement, not the
open-drain part's. Searching the scripts and every FINDINGS file for the number turns up only
io_buf sources for it. No released-state measurement of the open-drain part has been found.
The `--ccomp 0p25` open-drain runs of 2026-09-11 therefore rest on a borrowed number, and the
figure caption they produce ("C_comp 0.25 pF (measured, NMOS off)") overstates what was
measured on that device.

**What is actually established.** On the open-drain bench, 3.0 pF is supported by evidence
independent of the declaration: at 3.0 pF the measured Kd collapses onto a single curve against
its own gate across eight pulse widths, and at the declared 5.0 pF it does not. So the file's
5.0 pF is too large by a factor of about 1.7, not 20.

**What is still open** is the recorded caveat, unchanged: the single-fixture loop solve says
3.0 pF and the two-fixture push-pull solve on the same die says 1.75 pF. The two solves absorb
the voltage-dependent capacitance differently. That factor of 1.7 between two solves of the
same die is the real characterisation item, and it is not resolved by any run made so far.

**Next step:** measure the open-drain part's released-state C(V) the way io_buf's was measured
(ramp current minus a DC sweep at the same bias, divided by the ramp slope), which needs an
output-disable path on the open-drain netlist; `high_z()` currently supports io_buf only.

## 2026-09-17, item 5 CLOSED: anchoring the measured map ends

`gate_chain_prototype.py --anchor-maps` rescales each measured map so it is exactly 0 at the
off end and 1 at the on end, leaving the interior shape alone (`anchor_maps`). Measured at
12 ns on the full-swing run:

| device | build | settled pad | vs transistor | Ku | Kd |
|---|---|---|---|---|---|
| ex2 (1.5450 V) | plain | 1.5641 V | +19.1 mV | 1.0029 | -0.0144 |
| ex2 | **anchored** | 1.5473 V | **+2.3 mV** | 1.0026 | -0.0021 |
| inv_chain (1.4220 V) | plain | 1.4359 V | +13.9 mV | 1.0004 | -0.0166 |
| inv_chain | **anchored** | 1.4211 V | **-0.9 mV** | 1.0000 | -0.0000 |

Full-swing pad rms over the whole window improves with it: ex2 23.9 -> 15.1 mV, inv_chain
14.9 -> 14.1 mV (shipped 15.4 / 20.1).

**inv_chain gets it for free.** Anchored single pulses -0.8 / +2.1 / +4.7 / -7.0 / +0.6 % with
lags -3 / 4 / 7 / -4 / 4 ps, against +2 / +6 / +9 / -5 / +2 % before. Better on both.

**On ex2 it costs the stressed peaks:** -8.8 / -10.1 / -9.6 / -8.5 / -2.2 % against
-2.0 / -3.1 / -3.8 / -3.8 / +0.9 % before (lags improve, 57-85 -> 42-78 ps). The cause is
visible in the log and is NOT the map shape: with the anchored map the threshold bisection has
no bracket at d810 (vt 0 gives -17.3 %, vt 0.7 gives -99.0 %), so `calibrate_pad` falls back to
scaling the drive by 1.010 instead of placing the threshold. The calibration path changed, not
the physics. Re-testing ex2 with a calibration that can still bracket is the open follow-up.

## 2026-09-17, item 1 (the fifth stage number): the tail ratio works, partially

`--dn-ratio R` makes the discharge-direction resistive fraction `x_lin * R`, so a stage goes
resistive earlier on the way down, drains more slowly at the end, and keeps residual charge
between pulses without changing the rise. It is the fifth number the 09-14 verdict asked for.
Built on the two variants where timing and train recovery could not both be had, on top of the
joint fit, with `--fix-xlin 0.45`.

Single pulses, peaks at 90 -> 50 % stress and lags:

| variant | build | peaks % | lags ps |
|---|---|---|---|
| ex2_weak | joint (R = 1) | -8 / -10 / -12 / -8 / -1 | 0 … 33 |
| ex2_weak | joint + R = 2 | -4.0 / -5.9 / -9.1 / -3.6 / -3.0 | -13 … 38 |
| ex2_skewp | joint (R = 1) | -4 / -5 / -5 / -5 / 0 | 23 … 36 |
| ex2_skewp | joint + R = 2 | -1.6 / -1.3 / -0.4 / -0.3 / -1.8 | 0 … 32 |

Settled train (8 pulses, 50 % duty), R = 1.5 only, since the scorer took the lexically first
tail build; R = 2 and R = 3 are being scored now:

| variant | real stage | joint (R = 1) | joint + tail (R = 1.5) |
|---|---|---|---|
| ex2_weak | +2.8 % (lag 150-163 ps) | -17.1 % (lag 0-33) | **-12.1 %** |
| ex2_skewp | +0.5 % (lag 118-125 ps) | -8.0 % (lag 23-36) | **-2.1 %** |

**Verdict so far.** On ex2_skewp the fifth number closes the trade: lag 14-46 ps *and* a settled
train within 2.1 %, where four numbers forced a choice between 118-125 ps lag or -8 %. On
ex2_weak it recovers 5 points of train (-17.1 -> -12.1) and improves every single-pulse peak,
but does not close it.

**Cost, and it is real:** the tail ratio makes full swing worse. Full-swing pad rms goes
29.7 -> 37.6-46.1 mV on ex2_weak and 25.2 -> 37.6-42.8 mV on ex2_skewp (shipped 7.9 / 8.6).
A slower drain at the end of every stage is not what the full-swing edge wants. Whether the
anchored map recovers part of that is untested.

### Addendum, same day: every tail ratio scored, and R = 2 is the answer

The first train run scored only R = 1.5: `builds()` takes `hits[0]`, so one `_dn*` pattern row
silently picked the lexically first ratio. `variant_train_check.PATTERNS` now carries one row
per ratio. Settled train, 8 pulses at 50 % duty (pulse 1 / settled, %):

| variant | real stage | joint, R = 1 | R = 1.5 | **R = 2** | R = 3 |
|---|---|---|---|---|---|
| ex2_weak | -1.3 / +2.8 | -0.6 / -17.1 | +0.1 / -12.1 | **-2.9 / -7.9** | -3.2 / -7.7 |
| ex2_skewp | +1.8 / +0.5 | +1.2 / -8.0 | +8.8 / -2.1 | **-0.7 / -1.6** | -0.7 / -1.5 |

R = 3 is indistinguishable from R = 2 on both, so the knob saturates; R = 1.5 is not enough on
either, and on ex2_skewp it distorts pulse 1 (+8.8 %).

**Item 1 verdict: the fifth number closes the trade.** Before, four numbers forced a choice per
buffer:

| | four numbers, real-stage fit | four numbers, joint fit | five numbers, joint + R = 2 |
|---|---|---|---|
| ex2_weak | train +2.8 %, lag 150-163 ps | train -17.1 %, lag 0-33 ps | **train -7.9 %, lag -13…38 ps** |
| ex2_skewp | train +0.5 %, lag 118-125 ps | train -8.0 %, lag 23-36 ps | **train -1.6 %, lag 0…32 ps** |

Both now sit inside the recipe's stated bands at the same time (settled train within 8 %,
single-pulse peaks within 8 %: weak -4.0 / -5.9 / -9.1 / -3.6 / -3.0, skewp -1.6 / -1.3 / -0.4 /
-0.3 / -1.8). ex2_skewp is closed outright; ex2_weak is inside the band rather than comfortably
inside it.

**The cost stands:** full-swing pad rms 29.7 -> 45.6 mV (ex2_weak) and 25.2 -> 42.5 mV
(ex2_skewp), against 7.9 / 8.6 for the shipped model. A slower drain at the end of every stage
is not what the full-swing edge wants. Not yet regression-tested on the seven variants that
already worked; that run is in flight.

**Correction to the item 5 table above (same day).** That table mixed two reference points: the
transistor level came from `full_swing_check` which reads at 14.5 ns, while the model values
were read at 12 ns, and the plateau droops slightly between them. It also quoted 1.5654 V for
"ex2 measured map", which is the *file-fitted* build `ibis_silicon_K3_xlin0.45_calibpad810`, not
the real-stage build the rest of the row describes. Read consistently at 12 ns, for the
real-stage builds (`real_silicon_K3_calibpad810`, `real_silicon_K7_calibpad104`):

| device | transistor | assumed map | measured, as solved | measured, ends anchored |
|---|---|---|---|---|
| ex2 | 1.5451 V | 1.5421 V (-3.0 mV) | 1.5641 V (+19.0 mV) | 1.5473 V (+2.2 mV) |
| inv_chain | 1.4222 V | 1.4209 V (-1.3 mV) | 1.4359 V (+13.6 mV) | 1.4211 V (-1.2 mV) |

The conclusion is unchanged; only the third significant figure moves. `scripts/build_settled_level_figure.py`
draws this window and computes its own numbers from the same runs, so the figure and the table agree.

**Correction: anchoring does cost ex2's stressed peaks. My earlier explanation was wrong.**

The item 5 entry above blamed ex2's peak loss on the threshold bisection losing its bracket and
falling back to drive scaling, and said "the calibration path changed, not the physics". A
matched pair built at the same depth refutes that: the *plain* build falls back too.

| build at d858 | bracket | fallback | peaks 975 → 810 ps | lags ps | full-swing rms |
|---|---|---|---|---|---|
| plain | none (vt 0 gives -21.2 %) | drive x1.021 | -1.3 / -1.0 / +0.1 / +2.0 / +7.1 | 54 … 98 | 23.6 mV |
| anchored | none (vt 0 gives -24.1 %) | drive x1.045 | -5.9 / -4.4 / +0.2 / +6.2 / +15.4 | 30 … 112 | 29.2 mV |

Both lose the bracket, so the fallback is not caused by anchoring, and the peak difference is
real. It reproduces at the other depth (d810: plain -2.0 / -3.1 / -3.8 / -3.8 / +0.9, anchored
-8.8 / -10.1 / -9.6 / -8.5 / -2.2). The likely mechanism is the clip: ex2's stressed peak draws
on the early, sub-threshold part of the Ku map, which is exactly the negative region that
anchoring removes. On inv_chain, whose stages are far faster than the pulse, that region is
never read and anchoring is free.

**Also note** the full-swing rms over the window is not a clean indicator of this: it is
dominated by edge timing, which moves with the drive-scale fallback. It improved with anchoring
at d810 (23.9 -> 15.1 mV) and worsened at d858 (23.6 -> 29.2 mV) on the same buffer. The
settled plateau read at 12 ns is the clean measurement, and that one is unambiguous.

**Standing recommendation:** anchor the map ends on inv-type buffers, where it is free and
improves the stressed peaks as well. On ex2-type buffers the settled level and the stressed
peaks now pull in opposite directions; anchoring only the *off* end (Kd to 0, leaving the
sub-threshold Ku region alone) is the obvious next variant and is untested.

## 2026-09-17, io_buf pull-down hump: a baseline metric, and a surprise at mild widths

The remaining io_buf item was recorded as "the hump arrives ~0.2 ns late and is slightly too
tall at 1505 ps", with no metric attached. Defined one: after the main pad excursion, take the
largest local maximum in the following 5 ns, and report its time from the input reversal and
its height. Build `real_prior_slots3_gdnchain3_k1.0559`, transistor references from the matrix,
existing runs only:

| width ps | transistor hump | model hump | late by | taller by |
|---:|---|---|---:|---:|
| 2354 | 1.898 ns, 0.052 V | none found | — | — |
| 2090 | 1.882 ns, 0.052 V | none found | — | — |
| 1853 | 1.836 ns, 0.052 V | none found | — | — |
| 1666 | 1.788 ns, 0.052 V | 2.060 ns, 0.058 V | +272 ps | +6 mV |
| 1505 | 1.696 ns, 0.052 V | 2.058 ns, 0.058 V | +362 ps | +6 mV |

Two things stand out. The transistor's hump is remarkably stable: 0.052 V at every width, moving
only 200 ps across the whole stress range. And the model reproduces it only at the two deepest
widths, where it is 272-362 ps late rather than the ~200 ps previously recorded.

**The three "none found" entries are not yet interpreted.** Either the model genuinely has no
release hump at mild widths, which would be a different defect from a late hump, or the detector
misses a shoulder that never turns into a true local maximum. Diagnosis in flight; do not quote
the table above as a hump-timing result until that is settled.

`--gdn-dn-ratio R` has been added to `gate_step_prototype.py`: it sets the tail ratio for the
pull-down chain only, before the chain is fitted and before `stage_block` emits it. The hump is
the pull-down path releasing, and the tail ratio is exactly a knob on how a stage releases, so
it is the obvious lever. Not yet run, deliberately: a metric that silently fails on three of
five widths cannot judge it.

**Correction, same day: the hump table above was my detector failing, not the model.**

The "none found" entries were a bug in the metric. It located the main excursion as the sample
furthest from the window's first sample, but the window began *at* the reversal, where the pad
is already at its excursion; so the "main peak" landed near the end of the window and the hump
search ran off it. The model has a release hump at every width. Re-measured, main excursion
taken in the first 0.7 ns after the reversal and the hump as the maximum from 0.9 to 3.2 ns:

| width ps | transistor hump | model hump | late by | taller by |
|---:|---|---|---:|---:|
| 2354 | 1.898 ns, 0.0519 V | 2.060 ns, 0.0600 V | +162 ps | +8.0 mV |
| 2090 | 1.882 ns, 0.0518 V | 2.060 ns, 0.0597 V | +178 ps | +7.9 mV |
| 1853 | 1.836 ns, 0.0518 V | 2.060 ns, 0.0598 V | +224 ps | +8.0 mV |
| 1666 | 1.788 ns, 0.0518 V | 2.060 ns, 0.0582 V | +272 ps | +6.4 mV |
| 1505 | 1.696 ns, 0.0517 V | 2.058 ns, 0.0580 V | +362 ps | +6.3 mV |

**The real defect is not a fixed lateness.** The transistor's hump walks 202 ps earlier across
the stress range (1.898 -> 1.696 ns) at a constant 0.0518 V. The model's sits at 2.058-2.060 ns
whatever the width. The lateness therefore grows from 162 to 362 ps purely because the model's
release time does not move with stress.

That is the same class of defect as the shipped model's GUP in section 2 of the walkthrough: an
internal state whose trajectory barely depends on how far the pulse got. Here it is on the
pull-down path, and it says the pull-down chain is reaching full charge at every one of these
widths, so it always releases from the same level and therefore at the same time. If that is
right, the lever is the pull-down chain's threshold (which decides whether it is caught part-way)
rather than its drain rate. The tail-ratio run now in flight tests the drain-rate half.

## 2026-09-17, the gentler anchor: hypothesis refuted, and the real tension named

`--anchor-mode off` clips only the pull-down maps at zero and leaves the pull-up map exactly as
solved. The prediction was that this would keep the settled-level fix while restoring ex2's
stressed peaks, because ex2's peak is built below turn-on where the solved Ku goes negative.

**Wrong.** With Ku untouched, ex2's peaks are still lost:

| ex2 build | settled | peaks 975 → 810 ps | full-swing rms |
|---|---|---|---|
| plain | +19.0 mV | -2.0 / -3.1 / -3.8 / -3.8 / +0.9 | 23.9 mV |
| anchor both ends | +2.2 mV | -8.8 / -10.1 / -9.6 / -8.5 / -2.2 | 15.1 mV |
| **anchor off end only (Ku untouched)** | **+2.5 mV** | **-9.1 / -10.3 / -9.9 / -8.9 / -2.6** | 16.8 mV |

The two anchored rows agree to within 0.4 %, so the pull-up map's sub-threshold region is not
what the peak was drawing on. **It is the Kd clip.** The solved Kd goes negative around the
pull-down's off state (-0.0144 at GDN 0 on ex2, -0.0166 on inv_chain), and that negative
excursion means the pull-down branch *sources* current. During the reversal that sourced current
is part of how the model reaches its stressed peak; at DC the same value is simply wrong and
lifts the settled level by 19 mV.

**So the settled level and ex2's stressed peak pull on the same number in opposite directions.**
Both cannot be had by clipping. inv_chain is unaffected either way (settled -1.1 mV, peaks
-1.1 / +1.6 / +4.0 / -8.0 / -0.6, essentially the same as the full anchor).

**Not yet tried:** clip the map only *at* its off endpoint rather than across the whole curve.
`anchor_maps_off` applies `clip(y, 0, None)` to every sample, so it removes the negative region
wherever it occurs, not only at GDN 0. If the negative excursion is narrow around the off state
and the stressed peak draws from a different part of the curve, an endpoint-only anchor would
separate them. If it is broad, the two really are the same number and the honest answer is that
the measured Kd map is absorbing something (NMOS feedthrough, or C_comp mis-attribution) that
the pad equation has no other term for.

**Recommendation unchanged for inv-type buffers: anchor. For ex2-type: do not, pending the
endpoint-only test.**

## 2026-09-17, io_buf hump vs the tail ratio: negative, and it says where the lever is

`--gdn-dn-ratio R` gives the pull-down chain its own tail ratio. Hump time from the input
reversal, and its error against the transistor:

| width ps | transistor | R = 1 | R = 2 | R = 3 |
|---:|---|---|---|---|
| 2354 | 1.898 ns | 2.060 ns (+162 ps) | 2.082 ns (+184) | 2.066 ns (+168) |
| 2090 | 1.882 ns | 2.060 ns (+178 ps) | 2.084 ns (+202) | 2.068 ns (+186) |
| 1853 | 1.836 ns | 2.060 ns (+224 ps) | 2.082 ns (+246) | 2.066 ns (+230) |
| 1666 | 1.788 ns | 2.060 ns (+272 ps) | 2.086 ns (+298) | 2.068 ns (+280) |
| 1505 | 1.696 ns | 2.058 ns (+362 ps) | 2.086 ns (+390) | 2.068 ns (+372) |

The hump stays pinned near 2.06-2.09 ns at every ratio; R = 2 is slightly worse than R = 1 and
R = 3 is marginally worse. Single-pulse peaks and lags are unchanged to 0.1 % (2.9 / 4.7 / 4.4 /
-0.0 / 0.8 against 2.9 / 4.8 / 4.4 / 0.0 / 0.9) and full-swing rms is 24.6 mV for all three.

**The fit compensates, which is the real tell.** The pull-down chain fits landed at
(s_up 1.60, s_dn 1.01, vt 0.46, x_lin 0.09) for R = 2 and (2.63, 4.29, 0.70, 0.58) for R = 3 --
wildly different stage numbers producing the same pad to within 0.1 %. The pad does not
constrain this chain at all. The reason is the same one the hump timing shows: over this whole
width range the pull-down chain **reaches the same state every time**, so it always releases
from the same level and therefore at the same moment, and its internal rates never get exercised.

**Conclusion: the tail ratio is the wrong lever here.** It changes how fast a stage drains, not
where it drains *from*. The io_buf hump needs whatever decides how far the pull-down path gets
before the reversal -- its threshold, or the fact that it is driven by a replayed recorded step
rather than by something that can be interrupted. This is the section 2 defect exactly, and on
this path it is still open.

## 2026-09-17, io_buf hump vs the pull-down threshold: also negative, and now the cause is clear

`--gdn-vt V` overrides the pull-down chain threshold after its fit (the other three numbers and
the fit residual are untouched, so only the threshold moves). Hump time and height:

| width ps | transistor | fitted vt | vt 0.50 | vt 0.62 | vt 0.72 |
|---:|---|---|---|---|---|
| 2354 | 1.898 ns, 0.0519 V | 2.060, 0.0600 (+162) | 2.110, 0.0337 (+212) | 1.976, 0.0446 (+78) | 2.106, 0.0669 (+208) |
| 2090 | 1.882 ns, 0.0518 V | 2.060, 0.0597 (+178) | 2.112, 0.0336 (+230) | 1.976, 0.0444 (+94) | 2.106, 0.0668 (+224) |
| 1853 | 1.836 ns, 0.0518 V | 2.060, 0.0598 (+224) | 2.108, 0.0337 (+272) | 1.976, 0.0445 (+140) | 2.106, 0.0668 (+270) |
| 1666 | 1.788 ns, 0.0518 V | 2.060, 0.0582 (+272) | 2.122, 0.0332 (+334) | 1.988, 0.0431 (+200) | 2.106, 0.0652 (+318) |
| 1505 | 1.696 ns, 0.0517 V | 2.058, 0.0580 (+362) | 2.124, 0.0332 (+428) | 1.978, 0.0430 (+282) | 2.104, 0.0650 (+408) |

**The decisive number is the walk across the five widths:**

| | transistor | fitted vt | vt 0.50 | vt 0.62 | vt 0.72 |
|---|---:|---:|---:|---:|---:|
| hump moves | **202 ps** | 2 ps | 16 ps | 12 ps | 2 ps |

vt 0.62 looks like a win on lateness alone (+78 … +282 ps against +162 … +362), but its hump is
0.043-0.045 V against the transistor's 0.052 V, 8 mV too short, where the fitted build is 8 mV
too tall and vt 0.72 is 15 mV too tall. Every threshold trades absolute position against height
and none of them restores the walk. Single-pulse peaks and lags are identical to 0.1 % across
all four builds, so the pad excursion does not see this parameter at all.

**Cause.** Over this whole width range (1505-2354 ps) the model's pull-down chain finishes
before the input reverses, so it always releases from the same level and therefore at the same
moment. No parameter of a chain that always finishes can produce a release that depends on how
far it got. Both levers are now excluded by measurement: the drain rate (tail ratio) and the
level it drains from (threshold).

**This is the io_buf tell again.** The pull-down chain's fit residual against the real gate is
0.024, against 0.003-0.007 for the ex2 and inv_chain predrivers -- the same order-of-magnitude
gap that put io_buf on a step-replay command layer rather than a stage chain in the first place.
The pull-down path is not a row of current-limited stages either. Fixing the hump means giving
that path a command that can be interrupted, not retuning a chain that cannot.

## 2026-09-17, item 1 regression: the fifth number is a per-buffer remedy, not a default

R = 2 built on the seven variants that already worked, then all nine scored on trains.
Settled train, % (pulse 1 in brackets where it moved materially):

**ex2 family -- controlled comparison (joint R = 1 vs joint + tail R = 2):**

| variant | joint, R = 1 | joint + tail, R = 2 | verdict |
|---|---:|---:|---|
| ex2_base | +0.8 | +3.8 | slightly worse, both in band |
| ex2_weak | **-17.1** | **-7.9** | rescued |
| ex2_nomiller | +0.5 | +3.4 | slightly worse, both in band |
| ex2_skewp | **-8.0** | **-1.6** | rescued |
| ex2_slowpre | -4.9 | +3.4 | smaller in magnitude |

**inv family -- NOT a controlled comparison.** No joint-only build exists for these, so the only
baseline is the plain real-stage fit, and the tail column changes two things at once:

| variant | real stage (R = 1, no joint) | joint + tail, R = 2 |
|---|---:|---:|
| inv_base8 | -1.8 (pulse 1 +6.9) | **+6.1** (pulse 1 +16.1) |
| inv_weak | -4.2 | **+16.0** |
| inv_skewp | +1.5 | +1.6 |
| inv_stage4 | +8.1 | **+18.1** |

Full-swing rms degrades with them: inv_weak 12.3 mV (shipped 6.8), inv_skewp 16.3 (7.6),
inv_stage4 53.3 (8.8).

**Verdict: do not adopt R = 2 as a default.** Where the comparison is clean, on the ex2 family,
it rescues the two buffers that could not otherwise hold timing and recovery together and costs
the other three a few points of train while leaving them in band. On the inv family the tail
builds are much worse, but that comparison confounds the joint fit with the tail ratio, so the
tail ratio alone is **not** proven to be the cause. A controlled inv run (joint, R = 1) is in
flight to separate them.

Standing recommendation: apply the fifth number per buffer, as the remedy for the specific
failure mode it was introduced for -- a joint fit that buys single-pulse timing at the cost of
train recovery -- and not as a global switch. It costs no extra bench measurement either way,
since it is fitted from the recordings already taken.

### Addendum: the inv confound resolved, and the blame splits by variant

The regression entry above flagged that the inv comparison changed two things at once. A
controlled run (`variant_silicon_maps.py --only inv_* --source real --joint`, R = 1) supplies
the missing baseline. Settled train, %:

| variant | real stage | **joint, R = 1** | joint + tail, R = 2 | what moved it |
|---|---:|---:|---:|---|
| inv_base8 | -1.8 | **+4.2** | +6.1 | mostly the joint fit |
| inv_weak | -4.2 | **-5.2** | +16.0 | **the tail ratio** |
| inv_skewp | +1.5 | **+1.4** | +1.6 | neither |
| inv_stage4 | +8.1 | **-18.7** | +18.1 | **the joint fit** |

So neither change is globally safe and neither is globally guilty:

* **inv_weak** is the one clean case against the tail ratio: the joint fit alone is harmless
  (-5.2 against -4.2) and adding R = 2 sends the settled train to +16.0 %.
* **inv_stage4 is a warning about the joint fit itself**, independent of the tail. The joint fit
  alone swings the settled train 27 points, +8.1 -> -18.7 %, while buying excellent single
  pulses (peaks 1.0 / 0.1 / 0.1 / 0.4 / 0.8 / 1.4 / -0.2 %, lags 14-19 ps). That is the same
  timing-versus-recovery trade the fifth number was introduced for, and here the fifth number
  does **not** resolve it: it overshoots to +18.1 % rather than landing between.
* **inv_base8** moves mostly on the joint fit (-1.8 -> +4.2), the tail adding 1.9 more.
* **inv_skewp** is insensitive to both.

**Sharpened recommendation.** The joint fit buys single-pulse timing and costs train recovery on
ex2_weak, ex2_skewp, inv_base8 and inv_stage4. The fifth number resolves that trade on the two
ex2 variants, does not resolve it on inv_stage4, and is actively harmful on inv_weak where there
was no trade to resolve. Both the joint fit and the tail ratio are therefore per-buffer choices
that must be verified on that buffer's train, not switches to enable because a class of buffer
seemed to need them. The full-swing fit residual already selects the command layer; nothing yet
selects these two, and that selection is the next piece of the one-framework goal.

### Correction: the open-drain released-state measurement needs no output-enable path

The open-drain C_comp entry above said the next step "needs an output-disable path on the
open-drain netlist; `high_z()` currently supports io_buf only". The second half is true, the
first half is not, and it named the wrong blocker.

`extract_pad_capacitance.high_z()` drives an OE pin because **io_buf has one**. The open-drain
part does not need one: its output stage is NMOS-only to ground (`mx15`, `mx17`, `mx19` as
`out n4 gnd gnd nfet`, with `mx16`/`mx18` as `gnd n4 out gnd`, and no PMOS anywhere on `out`),
so holding the input at the level that leaves n4 low turns the pull-down off and the pad is
released by construction. The released state is the rest state.

What the measurement actually needs:

* an entry in `run_three_buffer_realistic_pulse_campaign.DEVICES` (frozen dataclass, ~11 fields
  including the component and model names and the .ibs paths, all of which exist at
  `results/ex2_variants_2026-09-03/opendrain/ibis/ex2_opendrain.ibs`);
* nothing new in `extract_pad_capacitance.core_lines`: its fallback branch already wraps a flat
  `buffer.sp` as `.subckt ex2_buffer in out vdd gnd`, and the open-drain netlist at
  `results/ex2_variants_2026-09-03/opendrain/inputs/buffer.sp` is that same flat form (no
  `.subckt` line of its own);
* a released-state variant of `capacitance()` that holds `in` off rather than asserting an OE
  pin, then the identical method: C(V) = (I_ramp - I_dc) / (dV/dt) at matched bias, which is
  what produced io_buf's 0.25 pF.

That would give the open-drain part a **directly measured** released-state capacitance, so the
3.0 pF (single-fixture loop) against 1.75 pF (two-fixture push-pull) disagreement could be
adjudicated against a measurement instead of against the other solve. Feasibility is confirmed;
the build is not started.

## 2026-09-17, CORRECTION: anchoring is not free on inv_chain. It is a trade on both buffers.

The item 5 entries above concluded, from single pulses only, that anchoring the measured map ends
is "free on inv_chain and improves its stressed peaks as well". Trains were never run on those
builds. They have now been added to `track2_train_check.BUILDS` and scored on the 8-pulse train:

| device | build | pulse 1 | settled | peak shift |
|---|---|---:|---:|---:|
| ex2, 858 ps | real last stage + pad point | -3.9 % | **-0.7 %** | -6 ps |
| ex2 | map ends anchored | -9.7 % | **-6.0 %** | -24 ps |
| ex2 | pull-down end only | -10.0 % | -6.1 % | -25 ps |
| inv_chain, 111 ps | real gate + pad point | +9.0 % | **-2.1 %** | +2 ps |
| inv_chain | map ends anchored | **+4.7 %** | **-5.3 %** | -0 ps |
| inv_chain | pull-down end only | +4.0 % | -7.1 % | -2 ps |

**So "free on inv_chain" was wrong.** On inv_chain anchoring halves the pulse-1 error, +9.0 to
+4.7 %, and costs 3.2 points of settled train, -2.1 to -5.3 %. That is a trade, not a gift. On
ex2 it is simply a loss on both, the settled train going -0.7 to -6.0 % on top of the stressed
peak cost already recorded.

**Revised verdict.** Anchoring the map ends fixes the DC settled level on both buffers, +19.0 to
+2.2 mV on ex2 and +13.6 to -1.2 on inv_chain, and costs train accuracy on both. It is therefore
a deliberate choice between a correct DC level and correct stressed behaviour, not an improvement
to switch on. The two anchor modes are indistinguishable on trains as they were on single pulses
(-6.0 against -6.1 on ex2, -5.3 against -7.1 on inv_chain), which again says the pull-up map's
sub-threshold region is not what is being paid for; it is the Kd negative region.

**Method note:** this is the third time in this session that a conclusion drawn from one class of
measurement did not survive the other. Single pulses said anchoring was free on inv_chain; the
train says otherwise. Peaks and trains have to be scored together before any recipe element is
called an improvement.

## 2026-09-17, the two input-edge rates: audited, and mostly fine

Prompted by the question of whether it is acceptable that ex2, inv_chain and io_buf run at 50 ps
input edges while the nine variants run at 1 ps.

**The comparisons are internally valid.** Both sides of every comparison see that buffer's edge:
the transistor deck and `gp.run_ours` both take it from `gp.EDGE_PS`. The 2026-09-08 bench error
was a *reference* run that broke that rule, which is a different thing.

**Stress levels are matched across families, verified by measurement rather than by label.** A
case labelled "depth 50" is one where the transistor pad actually reached 50 % of its own full
swing, in both families. Measured for all nine variants against their own `full_swing` run:

| family | result |
|---|---|
| ex2_base, ex2_weak, ex2_nomiller, ex2_skewp, ex2_slowpre | every selected case within 0.5 points of its label |
| inv_base8, inv_weak, inv_skewp, inv_stage4 | every selected case within 3.1 points of its label |

and for the matrix buffers, computed directly: ex2 810 ps = 50 %, 858 = 71 %, 975 = 91 %;
inv_chain 104 ps = 49 %, 111 = 71 %, 135 = 90 %; io_buf 1505 ps = 37 %, 2090 = 71 %, 2354 = 80 %.
So an error percentage quoted at a given stress level means the same thing in both families.

**Stale duplicate case directories exist and are inert.** inv_stage4 has three `depth50_*` folders
measuring 50.9 %, 61.2 % and 77.9 %, and two `depth70_*` measuring 69.9 % and 77.9 %; inv_base8 is
similar. `gp.cases()` iterates by mtime into a dict keyed by depth, so newest wins, and it selects
the correct one in all nine variants. They are a trap for a future reader, not a present error.

**The native-IBIS reference does exist on the variants** (`native` and `native_rwf1` directories
under every depth case), so the 1 ps choice did not cost the second reference.

**ex2_base is NOT the same netlist as ex2.** md5 73620cbe (matrix ex2) against 8bf8a58b
(ex2_base). So the two edge rates cannot be compared for free by reading ex2 against ex2_base;
they are different circuits. Confirmed edges from the decks themselves: matrix ex2 rises
5n -> 5.05n (50 ps), ex2_base rises 5n -> 5.001n (1 ps).

**What is still open:** whether model accuracy itself depends on the edge rate. Nothing measured
so far tests it, because no buffer has been run at both. The bounded test is to take one existing
model unchanged and run it and its transistor at both edge rates, then compare peak error against
achieved stress. If the two error-versus-stress curves overlay, the 1 ps choice costs nothing.

## 2026-09-17, open-drain C_comp: the released state is now MEASURED on that part

`scripts/opendrain_released_capacitance.py`, the same ramp-minus-DC-sweep method that produced
io_buf's numbers, applied to the open-drain netlist for the first time. No output-enable is
needed: that output stage is NMOS-only to ground, so holding the input off is the released
state. Both input levels were swept rather than assumed, and the released one identified by its
conduction current:

| input held at | DC current at mid-rail | C at mid-rail | C range | state |
|---|---:|---:|---|---|
| 3.3 V | **0.0000 mA** | **0.234 pF** | 0.229 - 0.288 pF, flat | released, pull-down off |
| 0.0 V | 44.2014 mA | not meaningful | -0.147 - 0.584 pF | driven; conduction dominates the difference |

**The released-state pad capacitance of the open-drain part is 0.234 pF.** Flat across bias, the
same signature io_buf showed at 0.23-0.25 pF.

**This partly reinstates a claim I had struck.** The standing "the file declares twenty times the
released value" was recorded on 2026-09-17 as a conflation, because the 0.25 pF it divided into
was io_buf's number quoted for a different part with no measurement behind it. That objection was
correct: the claim was unsupported when it was made. It is now supported, by a measurement on
this part, and the ratio is 5.0 / 0.234 = **21x**.

**It does not resolve the two-solve gap, and it reframes it.** The released floor is a different
quantity from the loop values. Against 0.234 pF:

| value | ratio to the released floor |
|---|---:|
| declared in the file, 5.0 pF | 21x |
| single-fixture loop solve, 3.0 pF | 13x |
| two-fixture push-pull solve, 1.75 pF | 7.5x |

io_buf's driven state ran 4.5x its released state (0.25 -> 1.12 pF). For the open-drain loop
solve of 3.0 pF to be pad capacitance, the driven state would have to be about 13x the released
one. That is not proof, because the driven state of this part could not be measured by this
method (44 mA of conduction swamps the ramp-minus-DC difference), but it is strong evidence that
**both solves are absorbing something that is not pad capacitance**, and the declaration more so.

**Next:** measure the driven state of this part by a method that tolerates conduction, e.g. a
small-signal AC analysis at a fixed bias, so the driven/released ratio can be compared against
io_buf's 4.5x and the solve values judged directly.

## 2026-09-17, io_buf hump: the stage count is the third lever excluded

`gate_step_prototype.py --gdn-chain K` for K = 2, 5, 7 against the existing K = 3, scored on the
walk of the release hump across the five widths:

| build | hump walk | range |
|---|---:|---|
| transistor | **202 ps** | 1.696 - 1.898 ns |
| K = 2 | 10 ps | 2.088 - 2.098 ns |
| K = 3 | 2 ps | 2.058 - 2.060 ns |
| K = 5 | 2 ps | 2.066 - 2.068 ns |
| K = 7 | 4 ps | 2.072 - 2.076 ns |

Single-pulse peaks are identical to 0.1 % across all four (2.9 / 4.8 / 4.4 / 0.0 / 0.8) and the
full-swing pad rms is 24.6 mV for every one of them.

**The fits are wildly different and the pad cannot tell.** K = 2 lands on s_up 1.10, vt 0.700,
x_lin 0.084; K = 7 lands on s_up 5.35, vt 0.112, x_lin 1.008. Those are not small differences,
and they produce the same pad to within a tenth of a percent. The pad does not constrain this
chain at any depth.

**Three levers are now excluded by measurement:** the discharge tail ratio, the stage threshold,
and the stage count. None of them makes the release time respond to stress.

**Why the chain form cannot do it, stated plainly.** The chain is driven by the comparator, which
holds for the whole pulse, and these pulses are 1505-2354 ps. Any chain fast enough to reproduce
the measured full-swing step response finishes long before the input reverses, so its state at
the reversal is the same every time and it always releases from the same level. The transistor's
pull-down path does not: it is caught progressively further from where it started as the pulse
shortens, which is exactly the 202 ps walk. A form that always completes cannot reproduce a
release that depends on how far it got, for any values of its parameters.

**So this is a structural limit, not a tuning problem**, and the remaining option is the one the
fit residual already pointed at: give that path a command that carries pulse width, as the
step-replay form does for the pull-up, rather than a chain.

## 2026-09-17, edge-rate sensitivity: measured, and it mostly acts through stress

`scripts/edge_rate_check.py`. One existing model per family, unchanged, run with its transistor at
both 1 ps and 50 ps over the same widths. Peak error and the stress actually achieved:

**ex2_base** (`real_silicon_K3_calibpad50`), threshold near mid-supply:

| width | 1 ps stress / err | 50 ps stress / err | d(stress) | d(err) |
|---:|---|---|---:|---:|
| 975 ps | 90.0 % / -1.9 % | 90.2 % / -2.2 % | +0.2 | -0.3 |
| 895 ps | 79.5 % / -3.2 % | 80.0 % / -3.9 % | +0.5 | -0.7 |
| 857 ps | 69.5 % / -4.5 % | 70.2 % / -5.7 % | +0.7 | -1.2 |
| 832 ps | 59.9 % / -5.0 % | 60.7 % / -6.7 % | +0.8 | -1.6 |
| 812 ps | 50.0 % / -2.7 % | 51.1 % / -5.5 % | +1.1 | **-2.8** |

**inv_base8** (`real_silicon_K7_calibpad50`), threshold at 1.4 V on a 1.8 V part:

| width | 1 ps stress / err | 50 ps stress / err | d(stress) | d(err) |
|---:|---|---|---:|---:|
| 170 ps | 96.9 % / +1.0 % | 96.8 % / +1.1 % | -0.1 | +0.1 |
| 133 ps | 89.4 % / +2.5 % | 89.0 % / +2.7 % | -0.4 | +0.2 |
| 121 ps | 83.1 % / +4.5 % | 82.3 % / +4.5 % | -0.8 | 0.0 |
| 117 ps | 79.6 % / +5.5 % | 78.7 % / +6.1 % | -0.9 | +0.6 |
| 109 ps | 69.5 % / +7.6 % | 67.2 % / +8.0 % | -2.3 | +0.4 |
| 105 ps | 59.5 % / +6.2 % | 55.4 % / +0.8 % | -4.1 | -5.4 |
| 102 ps | 50.3 % / +0.5 % | 43.1 % / **-10.3 %** | -7.2 | -10.8 |

**The edge acts mostly through the stress it produces, not directly on accuracy.** Wherever the
edge moved the achieved stress by under 1 point, the error moved by at most 0.6 points, on both
buffers. Where it moved the stress by 4 to 7 points, on inv_base8's two shortest widths, the
error moved by 5 to 11 points. That is expected: at the same width a 50 ps edge on a part whose
threshold sits well below mid-supply produces a shorter effective pulse, so it lands at deeper
stress, and error follows stress.

**This supports quoting errors at matched stress**, which is what the walkthrough does, and it
supports the audit conclusion that the two edge rates do not invalidate the comparisons.

**One residual is not explained by stress.** ex2_base's deepest width shifts stress by only
1.1 points and moves error by 2.8. The 1 ps error-versus-stress curve is non-monotonic near the
bottom there (-5.0 % at 59.9 %, -2.7 % at 50.0 %), so a simple interpolation is unreliable, but
2.8 points is larger than the neighbouring slope accounts for.

**Caveat governing all of it:** these models were calibrated at 1 ps and then run at 50 ps, so
part of the degradation may be calibration transfer rather than intrinsic edge sensitivity. The
deepest inv_base8 point at 43.1 % is also outside the stress range the model was calibrated over.
Separating the two needs a rebuild calibrated at 50 ps against the 50 ps transistor runs, which
now exist under `results/edge_rate_check_2026-09-17/`. Not done.

## 2026-09-17, io_buf hump: EVERY command form pins it, which refutes my own explanation

Measured the hump walk across the five widths for every io_buf build on disk, chain and
step-replay alike. Transistor walks 202 ps (1.696 to 1.898 ns):

| build | pull-down form | walk | range |
|---|---|---:|---|
| ibis_prior_calibpad1505 | step replay | 18 ps | 2.214 - 2.232 ns |
| real_prior_calibpad1505 | step replay | 4 ps | 2.072 - 2.076 ns |
| real_prior_calibpad1505_slots3 | step replay | 4 ps | 2.074 - 2.078 ns |
| real_prior_dres | step replay | 2 ps | 2.068 - 2.070 ns |
| real_prior_slots3_gdnchain2_k1.0559 | chain, K = 2 | 10 ps | 2.088 - 2.098 ns |
| real_prior_slots3_gdnchain3_k1.0559 | chain, K = 3 | 2 ps | 2.058 - 2.060 ns |
| real_prior_slots3_gdnchain5_k1.0559 | chain, K = 5 | 2 ps | 2.066 - 2.068 ns |
| real_prior_slots3_gdnchain7_k1.0559 | chain, K = 7 | 4 ps | 2.072 - 2.076 ns |
| the three gdnvt and two gdndn variants | chain | 2 - 16 ps | 1.976 - 2.124 ns |

**This refutes the explanation I recorded and published earlier today.** I wrote that the chain
form is structurally incapable *because it always finishes before the reversal, so it always
releases from the same level*, and the implication was that a command carrying pulse-width
information would do better. Step replay carries exactly that information: it superposes the
last N edges, so its state at the reversal depends on how long the pulse was. It walks 4 ps.
Thirteen builds spanning two completely different command forms and five tuned parameters all
land between 2 and 18 ps against 202.

**So the cause is not the command form, and my reasoning about why was wrong.** Something common
to both forms pins the release. The candidates are downstream of the command: the Kd map, or the
pad equation, or the pad node itself (C_comp discharging into the load, which would set a time
constant that does not care how the gate got there).

**Not yet identified.** A first attempt to localise it by timing GDN and Kd failed on its own
metric: the level-crossing routine returned no value at all for the chain build and an
implausible 0 ps walk at 0.028 ns for the replay build. That is the third metric bug this
session, caught the same way as the others, by the numbers being physically impossible rather
than merely surprising. Diagnosis continues by dumping the traces instead of detecting features
in them.

## 2026-09-17, io_buf hump DIAGNOSED: the memory exists and is erased before it is used

Dumping the traces instead of detecting features in them settles it. Transistor first, its own
pull-down path (n1 -> nand_n3 -> n3), normalised, at the mildest and deepest widths:

| | 1505 ps (37 % stress) | 2354 ps (80 % stress) |
|---|---|---|
| n1 at the reversal | 0.854, still rising | 0.978, essentially complete |
| nand_n3 release, 50 % | ~1.4 ns | ~1.6 ns |
| n3 release, 50 % | **~1.79 ns** | **~1.98 ns** |
| pad hump | 1.696 ns | 1.898 ns |

The causal chain is plain: the short pulse does not give n1 time to finish, so it decays from a
lower level, crosses the NAND threshold sooner, and the whole pull-down path releases ~190 ps
earlier. That is the 202 ps hump walk, and it originates in the predriver being caught part-way.

Model next, same build (`real_prior_slots3_gdnchain3_k1.0559`), GDN being inverted so that GDN
rising is the pull-down turning off:

| | d1505 | d2354 |
|---|---|---|
| GDN at the reversal | **0.366** | **0.005** |
| GDN by 0.9 ns after it | 0.002 | 0.000 |
| GDN release begins | ~1.4 ns | ~1.4 ns |
| GDN 50 % crossing | **2.00 ns** | **2.00 ns** |

**The model's command does carry the pulse-width memory.** GDN sits at 0.366 at the reversal in
the deep case against 0.005 in the mild one. That is exactly the information needed. But it
decays to 0.002 within 0.9 ns, and the release does not begin until about 1.4 ns, so by the time
the release happens the two cases are identical and it fires at 2.00 ns in both.

**The model is calibrated to the mild case and misses the deep one.** Its 2.00 ns matches the
transistor's 1.98 ns at 80 % stress and misses the 1.79 ns at 37 % stress by 210 ps.

**This explains every negative result on this path.** Changing the command form did not help
because both forms trigger the release from the falling edge after a dead time. Slowing the drain
with the tail ratio did not help because it is not the drain rate that loses the information.
Moving the threshold did not help, nor did the stage count, because none of them shortens the
dead time between the reversal and the release.

**What would:** the release must start from a state that still reflects how far the path got,
which means the residual must survive until the release begins, or the release must begin sooner.
That is a relationship between two time constants in the command, not a value of any single
parameter, which is consistent with all five swept parameters failing.

## 2026-09-17, io_buf: a number correction, and the release is independent of the residual

**Correction to the entry above.** I quoted "GDN at the reversal 0.366 (deep) against 0.005
(mild)". 0.366 is the value 200 ps *before* the reversal, not at it. Read at the reversal the
values are **0.140** and **0.002**. The conclusion is unchanged, since 0.140 against 0.002 is
still a real difference that decays to ~0.002 before the release begins, but the figure was wrong
and is corrected here and on the walkthrough. That is the fourth number this session misread from
a sampling offset, all four caught by re-reading the trace rather than the summary.

**The release time does not depend on the residual at all.** GDN through the dead time, at the
deepest width, for the three tail ratios:

| build | GDN at rev | +0.3 ns | +0.6 ns | +0.9 ns | release, 50 % |
|---|---:|---:|---:|---:|---:|
| R = 1 | 0.140 | 0.031 | 0.007 | 0.002 | 2.000 ns |
| R = 2 | 0.111 | 0.001 | 0.000 | 0.000 | 2.022 ns |
| R = 3 | 0.158 | 0.043 | 0.012 | 0.006 | 1.974 ns |

and at the mildest width the residual is 0.002, 0.000, 0.004 with releases at 2.006, 2.022 and
1.982 ns.

The tail ratio does move the residual, and not even monotonically: R = 2 leaves *less* residual
than R = 1 and drains it faster. Yet the release fires within 25 ps of 2.0 ns in every case, and
the walk between deepest and mildest is 6, 0 and 8 ps.

**So the mechanism is now pinned down precisely.** The release is triggered by the input edge
propagating through the chain and is independent of the level the chain happens to be sitting at
when the reversal arrives. That is a stronger statement than "the residual decays before it is
used": even when the residual is deliberately made larger and slower (R = 3, still 0.006 at
+0.9 ns), the release does not move. The pulse-width memory and the release trigger are simply
not coupled in this command form.

**What that rules out and what it leaves.** It rules out every parameter that acts on the
residual, which is all five swept so far, and explains all five null results at once. What is
left is to couple them: the release must be *triggered* by the state of the path rather than by
the input edge, which is a change to the structure of the command, not to any of its numbers.

## 2026-09-17, open-drain C_comp CLOSED: neither solve is pad capacitance

The driven state is measurable after all, by ramping fast enough that displacement current
competes with the fixed 44.2 mA of conduction. The released state is carried at every rate as a
control, since it is known to be 0.234 pF and any rate where it drifts is a rate where the
quasi-static assumption has broken down.

| ramp | dV/dt | displacement | released C (control) | drift | driven C |
|---:|---:|---:|---:|---:|---:|
| 2.00 ns | 1.65 V/ns | 0.39 mA | 0.234 pF | 0.000 | -0.144 pF (meaningless) |
| 0.50 ns | 6.60 V/ns | 1.54 mA | 0.231 pF | -0.003 | 0.364 pF |
| 0.20 ns | 16.50 V/ns | 3.86 mA | 0.234 pF | -0.000 | 0.315 pF |
| 0.05 ns | 66.00 V/ns | 15.44 mA | 0.229 pF | -0.005 | 0.280 pF |
| 0.02 ns | 165.0 V/ns | 38.61 mA | 0.219 pF | **-0.015** | 0.231 pF |
| 0.01 ns | 330.0 V/ns | 77.22 mA | 0.211 pF | **-0.023** | 0.232 pF |

**The control marks the limit.** It holds within 5 fF down to 0.05 ns, then droops 15 and 23 fF,
about 10 %, at the two fastest rates. So the method is trustworthy to 0.05 ns and the last two
rows read slightly low.

**The driven value converges to about 0.23 pF**, the last two rows agreeing to 1 fF, and allowing
for the control droop it sits in the 0.23-0.26 pF band.

**So this part has almost no state dependence**, driven 0.23 pF against released 0.234 pF, where
io_buf ran 0.25 -> 1.12 pF, a factor of 4.5. That was the assumption the earlier reasoning leaned
on, and it does not hold here.

**Neither solve can be pad capacitance. The item is closed.**

| value | ratio to the measured pad capacitance (~0.23 pF) |
|---|---:|
| declared in the file, 5.0 pF | 22x |
| single-fixture loop solve, 3.0 pF | 13x |
| two-fixture push-pull solve, 1.75 pF | 7.6x |

The measured pad capacitance never exceeds 0.36 pF at any rate in either state. The long-standing
question was "which solve is right, 3.0 or 1.75?". The answer is neither: both are absorbing
something that is not pad capacitance, and the declaration more so. The 1.7x disagreement between
the two solves is a disagreement between two wrong numbers, which is why no amount of comparing
them to each other settled it.

**What this does not say.** It does not identify what the solves are absorbing. The loop solve
value of 3.0 pF does make the measured Kd collapse onto a single curve across eight widths
(r.m.s. 0.008 against 0.034 at the declared 5.0 pF), so it is doing useful work as a fitting
parameter. It is simply not the pad capacitance, and should not be recorded as C_comp.

---

## 2026-09-17, method animations: three scenes from real runs, and the axis-label bug

The two tracks were only ever explained in prose and static figures. These are three animated
scenes in which **every frame is a real solver iteration replayed from runs on disk** - no frame
is drawn by hand to illustrate a point. All three are ex2.

| scene | what moves | source | lands on |
|---|---|---|---:|
| FitSearch | the four stage numbers, trial by trial | 177 trials logged live, the 40 that improved | rms 0.0098 |
| Bisection | the stage threshold, iteration by iteration | the 10 `it*` directories the calibration wrote | vt 0.487, peak +1.4 % |
| MapBuild | a cursor sweeping time, tracing Ku against the gate | 540 solved instants, two fixtures | the map itself |

**The bisection scene is the one that earns its keep.** The pulse is cut short so the pad never
reaches the rail, peaking at 0.7707 V, and that peak height is the entire measurement. Watching
ten grey curves fan out and converge makes the "one stressed run places the threshold" claim
visible in a way the sentence never did.

**manim's own GIF export is unusable and mp4 is ~100x smaller** at the same visual quality. This
is a property of the export, not of the content, and is worth remembering before rendering
anything longer.

| scene | manim GIF, 480p15 | mp4, 720p30 | ratio |
|---|---:|---:|---:|
| FitSearch | 18.9 MB | 0.23 MB | 82x |
| Bisection | 16.6 MB | 0.19 MB | 87x |
| MapBuild | 21.6 MB | 0.15 MB | 144x |

**The layout bug, worth recording because it is not obvious.** The first render put axis labels
on top of the data and tick numbers struck through the axis names. The cause: the labels were
positioned with `next_to(ax.x_axis, DOWN)`, and **manim draws `ax.x_axis` and `ax.y_axis` through
the data origin, not along the edge of the plot**. On a plot whose x range starts at -0.7 - the
bisection scene - that line sits in the middle of the data, so everything hung off it landed
there too. The fix is to position against the Axes *bounding box* (`next_to(ax, DOWN)`) and to
place tick labels from `ax.c2p(v, y_range[0])` instead. Both helpers in `scripts/method_scenes.py`
now do this, and the docstring says why.

A second, subtler one: moving the parameter readouts to `to_corner(UP+LEFT)` put their top edge
at y~3.55, inside the title band at y 3.4-3.7. Screen corners are not empty just because the plot
is - the readouts are now anchored to empty regions *inside* each plot via `c2p`.

**What this does not say.** These show the mechanism on the buffer that works best. They are not
an error budget: inv_chain still needs the measured map to land, and io_buf's release timing is
wrong for a structural reason none of the parameters animated here can reach.

Written by `scripts/method_scenes.py` (manim CE 0.21.0, LaTeX-free) from `method_data.npz`,
exported by `scripts/export_method_animation_data.py`.

Published as **Two Tracks, Animated**:
https://claude.ai/code/artifact/8496a22a-fd40-490f-bf11-cade419f63e0

---

## 2026-09-17, the method film, and what the payoff has to be measured against

The three separate clips are superseded by one continuous film of nine beats, `Method` in
`scripts/film_scenes.py`, covering the buffer itself, both tracks, and the result. Track 2 in
the clips was only its last step; it now runs four beats, the important one being the solve.

**The payoff cannot be "track 1 against track 2" at the calibration width.** The first attempt
contrasted the file-only build with the measured-map build at d810 and found nothing to show:

| build at d810 | pad peak |
|---|---:|
| `ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810` | **-0.10 %** |
| `real_silicon_K3_calibpad810` | **+0.89 %** |

Both were **calibrated on this pulse's own pad peak**, so both land on it by construction and
the comparison is circular. The honest bar is the model that ships today, on the same pulse:
**+73.74 %** against the transistor's 0.7707 V. That is beat 9.

**The solve snapshot is unusually clean.** At 6.250 ns the two fixtures hold the pad at
**0.393 V and 2.988 V at the same instant**, giving Ku 0.503, Kd 0.119 at a 2x2 condition
number of **1.9**. That is what makes the beat legible: the two operating points are far apart,
so the two rows are visibly independent rather than nearly parallel. The animation point is
that the I-V tables are *identical* between the rows - only the load differs, and the load is
what moves the pad to a second operating point.

**Three manim defects worth not repeating**, all found by extracting frames rather than by
reading the code:

| symptom | cause |
|---|---|
| axis renders as a solid black block | `y_range` step left at 1.0 over a ~100 mA span: ~100 tick marks |
| "pull-up table" captioning the pull-down curve | captions placed at fixed plot corners; the IBIS convention puts pull-up below zero and pull-down above, so the corners swap them |
| caption floating unattached to any curve | caption anchored to a fixed y while its curve was elsewhere |

The rule that came out of it: anchor a caption to its own curve's data, or to a region of the
axes proven empty - never to a corner, and never to a y picked by eye.

**And one verification trap.** `ffmpeg -ss T -i in.mp4` seeks to the nearest keyframe and can
decode a smeared frame; the text in it appears doubled and reads as a render bug that is not
there. `ffmpeg -i in.mp4 -ss T` decodes exactly. Use the second form for frame checks.

**What this does not say.** Every beat is ex2. The film shows the mechanism, not the error
budget, and beat 9 is one width of one buffer.

---

## 2026-09-17, why the hidden half must be rebuilt: the native Ku is a clock, not a state

This was the one claim the walkthrough asserted without evidence. It is measurable, and the
measurement is already on disk in `results/stress_method_matrix_2026-08-20/delay_cmd/waveforms/
ex2_short_high_w{975,895,858,830,810}ps.csv`.

| width | silicon Ku peak | native Ku peak | native peak time |
|---:|---:|---:|---:|
| 975 ps | 1.2162 | 1.2467 | 6.384 ns |
| 895 ps | 1.1766 | 1.2518 | 6.389 ns |
| 858 ps | 1.1138 | 1.2524 | 6.387 ns |
| 830 ps | 1.0126 | 1.2615 | 6.381 ns |
| 810 ps | **0.8790** | **1.2581** | **6.379 ns** |

**Across a 165 ps change in pulse width the native IBIS Ku peaks within 1.2 % of itself and at
the same instant within 10 ps, while the silicon Ku collapses 28 %.** The stock netlist says why
outright: `B16 N5 0 V = time*{time_scale}` is a literal clock, `B18` is elapsed time since the
latched edge, and `B20 KUR0 ... pwl(V(NX), ...)` indexes the V-T table by that elapsed time.
There is no state node and no capacitor in the path. An interrupted transition therefore has no
representation in it: the schedule simply runs.

**The repo's `shipped/` baseline is not the stock build** and the distinction matters. It is
`InputDrivenTwoStateGateDelayCommandFull`, whose Ku comes from a map of GUP plus an
elapsed-time-keyed residual. But its GUP is still a clock: fixed-delay T-line copies of the
input driving a fixed-tau RC toward a 0/1 target. Measured, GUP turns on at 6.09 ns in every
run, and `max |GUP - GUP_full|` over 5.0-6.5 ns is 0.00055 at d975 and 0.00499 at d810 - the
short pulse rides the identical trajectory until the scheduled off-command lands. Its internal
gate max moves 5 points across the sweep where silicon moves 18.

## 2026-09-17, isolating what the measured map is worth

**The chain pair cannot isolate it.** `real_ibis` vs `real_silicon_K3_calibpad810` differ in
**seven** lines, not four: the four maps, plus `BSTG1/2/3` where s_up 1.79747 -> 1.81502 and
s_dn 1.64968 -> 1.66579, both exactly x1.009766 - the `calibrate_pad` drive-scale fallback.
`vt = 0.269804` and `x_lin = 0.403784` are identical in both. So "differ only in the maps" is
almost true, and the honest wording is "same command chain to within a 1 % drive scale".

**A clean pair exists** in `results/gate_cascade_prototype_2026-09-09/ex2_c1.7/`: both replay
the same measured gate, no chain and no calibration, and differ in nothing but the maps.

| build | d975 | d895 | d858 | d830 | d810 |
|---|---:|---:|---:|---:|---:|
| `gate_replay` (maps from the file) | -3.3 | -4.7 | -5.8 | -5.4 | -5.5 |
| `gate_replay_silicon_full` (measured maps) | +1.2 | +1.1 | +1.0 | -1.3 | -4.7 |

That gap is the map's own contribution, with everything else held fixed.

**Also worth recording: the vt bisection does not always fire.** For
`real_silicon_K3_calibpad810` it did not - `it01` probes vt = 0, `it02` probes vt = 0.7, the
bracket test `e_lo >= 0 >= e_hi` fails, and the run takes the drive-scale branch, leaving
vt = 0.269804 untouched. It does fire for the file-only build, which is the one the film shows:
its ten iterations run 0.528, 0.0, 0.7, 0.35, 0.525, 0.4375, 0.4813, 0.5031, 0.4922, 0.4867.

## 2026-09-17, the benches are not all the same, and the film now says so

| run | load | stimulus | probes |
|---|---|---|---|
| `predriver_stages_2026-09-09/ex2/full` | 50 ohm **and 2 pF** | 10 ns, 50 ps edges | in, n2, n3, n4, pad |
| `.../hspice_references/ex2/transistor/r50_c2pf/short_high_w810ps_810ps` | 50 ohm **and 2 pF** | 810 ps | in, pad, n4 |
| `full_swing_fixtures_2026-09-09/ex2/vfix_0` and `vfix_vcc` | 50 ohm to a **forced rail, no capacitor** | 10 ns | in, pad |

The first two are the same bench and the same load the model runs into. **The third is not**: the
Ku/Kd maps are extracted on a resistive-only, voltage-forced fixture and then applied on an R+C
bench. That is a real assumption and it now appears on screen rather than being passed over.

One trap for anyone reading the decks: `predriver_stages_2026-09-09/ex2/full/run.sp` carries the
stale `.title ex2 transistor short_high_w810ps_810ps`, but its PWL is the full-swing 10 ns pulse.

**And the fit was never rising-only.** `fit_chain_to` builds `grid = arange(4.0, 21.0, 0.002)`
with the input high 5.025-15.025 ns and takes the r.m.s. over the whole grid, so the rise, the
plateau, the fall and ~6 ns of recovery are one residual. `s_dn` multiplies `h(1-u)`, which is
~0 while the input is high, so the falling edge is the only thing that constrains it. The first
cut of the film cropped the display to the rise, which misrepresented this; it now runs to 13 ns.

---

## 2026-09-17, the same motivation one level down, at the gate

The Ku-clock evidence recorded above is correct but it is not the version to *show*. It asks a
viewer to compare five overlapping curves of a quantity the film has not defined yet. The same
claim is available at the gate - the node a viewer can watch propagate through the schematic -
and at the pad, where it needs no definitions at all.

| | transistor | shipped model |
|---|---:|---:|
| full-swing pad peak | 1.545 V | **1.544 V** |
| gate, full 10 ns pulse | 1.000 | 1.000 |
| gate, 810 ps pulse | **0.758** | **0.913** |

**On a complete transition the shipped model is within 1 mV of the transistor at the pad.** That
is worth showing *first*: the file alone really is enough for a full swing, and conceding that
is what gives the failure its force. Cut the pulse to 810 ps and the real gate stops at 0.758
and turns round, while the model's gate still reaches 0.913 - it never registers that the pulse
ended. The pad then overshoots by 73.7 %.

So the motivation reduces to two numbers: **0.758 against 0.913**. The missing half of the
buffer only matters once a transition is interrupted, and that is precisely when the state of
the gate - which the file does not carry - becomes the thing that decides the answer.

**Structural consequence for the film.** Act 1 is now buffer -> works -> breaks -> why -> bench,
with the real waveform drawn at each node as a probe walks the chain. The separate stage-waterfall
beat is folded into that walk, and the Ku-clock beat is dropped from the film (the evidence stays
here). Showing the model succeed before showing it fail is the part that was missing: without it,
"the file describes only half the buffer" does not imply that the other half needs rebuilding.

---

## 2026-09-17, correction: the full-swing agreement figure depends on the window

The entry above quotes the shipped model matching the transistor pad "within 1 mV" at full
swing, from peaks of 1.545 V and 1.544 V. That was measured over 4.8-9.0 ns, i.e. **the rising
edge only**. Widening the window to 4.8-18.0 ns so the film shows a whole transition - rise and
fall, framed like every stressed beat - moves both peaks and the gap:

| window | transistor | shipped model | gap |
|---|---:|---:|---:|
| 4.8-9.0 ns (rise only) | 1.545 V | 1.544 V | 1 mV |
| 4.8-18.0 ns (rise and fall) | 1.558 V | 1.554 V | **4 mV** |

Both are correct for their window; the second is the one the film now shows, and the one to
quote. The pad creeps slightly higher across the longer plateau, so the maximum over the wider
window is larger for both traces and the two no longer coincide as tightly.

**The general point is worth keeping.** A scene that computes its own annotation from the data
- `abs(si.max() - mo.max())` here - stays correct when the window changes. Prose written
alongside it does not, and there is nothing to warn you. Every number quoted in the page or in
these notes that was read off a windowed array should be re-checked whenever that window moves.

---

## 2026-09-17, how the film is structured now, and two lessons about explaining this method

Final structure, sixteen beats. Every beat is a real recording or a real solver iteration.

| act | beats |
|---|---|
| the buffer | the real waveform propagating in -> n2 -> n3 -> n4 -> pad; **it works** on a full transition (1.558 V vs 1.554 V); **it breaks** at 810 ps (+73.7 %); **why** - the real gate stops at 0.758, the model's reaches 0.913; **two things are missing** |
| track 1 | opening (the `?` becomes a chain of identical stages, four numbers named, roadmap); record the real gate; the four numbers one at a time; fit three; place the fourth |
| track 2 | opening (the output stage has no memory, the file implies one Ku-vs-gate curve, ask the transistor instead); Ku and the gate one against the other; four maps; measured vs file; the map's worth across five widths |
| payoff | ships today +73.7 %, this method +0.9 % |

**Lesson 1 - name the gaps, not the solutions.** The "two things are missing" beat first labelled
its two callouts "track 1" and "track 2". A reviewer caught it at once: the tracks are what
*supply* the missing things, so labelling the gap with the solution's name collapses the
distinction the beat exists to draw. It now says *how the gate moves* and *how the pad follows
it*, and each track is introduced when it arrives.

**Lesson 2 - each track needs its own opening, with motivation before method.** Without one, the
first concrete beat of a track (a bench, a fixture) appears from nowhere: the viewer sees a
procedure with no stated purpose. The opening says what gap this track fills and sketches the
whole method in one screen, so every subsequent beat reads as a step in a plan already stated.
The same opening is also where the four stage numbers are first *named*, which is what made the
one-at-a-time sweep legible - it had been showing effects of quantities never introduced.

**Dropped from the film**: the two-fixture Ku/Kd extraction and the two-equation solve. Both are
correct and the two-equation beat was a good one, but the reviewer's point stands: that
extraction is standard and can be assumed known, and its presence made track 2 read as a
lecture on IBIS extraction rather than on what this method adds. The measured-map beat now
states in its subcaption where the gate comes from - node n4, probed on the transistor - which
was the one thing genuinely missing from track 2's explanation.

The four superseded scene methods (`beat_clock`, `beat_stages`, `beat_fixtures`, `beat_solve`)
have been removed from `scripts/film_scenes.py`; their evidence is recorded in the entries above.

---

## 2026-09-17, manim collapses word spaces below ~20 pt - and it is not the font

Every small label in the film rendered with its spaces gone: "the buffer" as *thebuffer*,
"probing gate node n4" as one word. Captions at 27 pt were never affected. Two test scenes,
same string at 17 pt:

| variant | spaces |
|---|---|
| default, Georgia, Times New Roman, Cambria, Palatino Linotype, Segoe UI | all collapse the same way |
| `disable_ligatures=True` | no change |
| `MarkupText` | no change |
| 15 pt | worse |
| **`Text(s, font_size=34).scale(0.5)`** | **clean** |
| `Text(s, font_size=51).scale(1/3)` | clean |

**So the cause is size rounding in manim's glyph layout, not font metrics** - six fonts
agreeing rules the font out, and the fix scaling with render size rules the layout in. The
size dependence was the tell: a metrics defect would have hit 27 pt too.

The fix is one module-level subclass that every label in `scripts/film_scenes.py` routes through:

```python
class Text(_Text):
    def __init__(self, text, font_size=48, **kwargs):
        super().__init__(text, font_size=font_size * 2, **kwargs)
        self.scale(0.5)
```

Two consequences worth knowing. Corrected spacing makes every small label slightly **wider**
than it rendered before, so anything that just fitted may now overflow - the dense beats
(track 1's opening, the knob glosses, the roadmaps) need re-checking after the change, not
assuming. And the collapse was invisible in the code: the strings were correct throughout.
It only shows in extracted frames, which is one more reason frame checks are not optional.

## 2026-09-17, what the stress run is actually for - a correction to my own hypothesis

I had planned to show that the full swing "cannot see" the threshold vt. The export says
otherwise. Sweeping vt over 0.15..0.82 with the other three numbers held at their fitted values:

| stimulus | what vt changes | size of the effect |
|---|---|---|
| full 10 ns swing | WHEN the gate rises - a timing shift | rms 0.276 between the extremes |
| 810 ps pulse | HOW FAR the gate gets before turning round | peaks **0.81, 0.81, 0.66, 0.03, 0.00** |

**The full swing does see vt - as a timing shift.** But s_up shifts the timing too, so the two
trade off and the full-swing fit pins vt only loosely; that is consistent with the fitted vt
differing between builds (0.51 here, 0.27 for the real_silicon build). On the short pulse vt
decides whether the gate moves at all, an effect nothing else can mimic. So the honest
statement is not "invisible on the full swing" but **"pinned loosely by the full swing, hard
by the short pulse"** - and that is what the film's beat now says.

## 2026-09-17, track 1's own result, and the honest reason track 2 exists

| build, K=3 | 975 | 895 | 858 | 830 | **810** | gate at 810 (model/real) |
|---|---:|---:|---:|---:|---:|---:|
| file-only (`ibis_prior_..._calibpad810`) | -6.9 | -8.6 | -7.4 | -4.8 | -0.1 | 0.74 / 0.76 |
| measured maps (`real_silicon_K3_calibpad810`) | -2.0 | -3.1 | -3.8 | -3.8 | +0.9 | 0.76 / 0.76 |

The 810 column is where both were calibrated, so it proves nothing. **The other four widths
are the test**, and there track 1 runs 5-9 % low while the measured-map build runs 2-4 % low -
yet **both track the gate well**. That is the precise shortfall: track 1 gets the gate's
*motion* right and the gate-to-*pad* map wrong, because that map is still the file's guess.
It is exactly the gap track 2 fills, and the film now shows it at the end of track 1 rather
than leaving the transition to track 2 unmotivated.

Also recorded: HSPICE's own native IBIS buffer on the same 810 ps pulse peaks at **+70.7 %**
against the shipped pybis build's +73.7 %. Both fail together, which is the point the "it
breaks" beat now makes - the failure is the replay approach, not a defect in either model.

---

## 2026-09-17, the model lineage, stated precisely - a correction to how the film named things

The film had been calling pybis-as-shipped "the model that ships today" and this method "the
gate-state model", as if the architecture were the contribution. A reviewer caught the looseness
at three separate points. The precise lineage:

| model | Ku comes from | the gate node |
|---|---|---|
| HSPICE native IBIS | a table indexed by elapsed time | none - pure replay |
| pybis as it shipped (`InputDrivenTwoStateGateDelayCommandFull`) | a map of a gate node | **exists** - but driven by two fixed T-line delays into a fixed-tau RC, i.e. still a clock |
| this method | a map of a gate node | driven by a chain of stages fitted to the real gate (track 1), read through a measured map (track 2) |

**So pybis as shipped already WAS a gate-state model.** It had the right idea - a node whose
position selects Ku - and its failure (+73.7 % at 810 ps, gate reaching 0.913 where the real one
stops at 0.758) came from what drove that node, not from the idea. This method keeps the node
and changes two things: how it moves, and which map reads it. That is a more honest and more
useful description than "we built a gate-state model", and the film now says it: the shipped
build is "the last gate-state" throughout, the architecture beat presents it as *the last
method* with its flaw box and its right-idea box both highlighted, and the file-implied Ku
curve is labelled as "the file's map, as track 1 used it".

**Two presentation changes that follow from the same review.** The 810 ps stimulus is no longer
shown at the bench: at that point in the film nothing has motivated a short pulse, so it read
as unexplained. It arrives with the threshold, after the sweep has shown that a full swing pins
vt only loosely. And track 1's result is now shown as waveforms rather than a peak-error chart,
on two panels - 810 ps where the threshold was placed (-0.1 %, by construction) and 895 ps which
it never saw (-8.6 %) - with the payoff drawn on the *same* two panels so the comparison is
direct:

| at 895 ps, never calibrated | peak error |
|---|---:|
| last gate-state | +13.3 % |
| track 1 alone | -8.6 % |
| both tracks | **-3.1 %** |

**Sound.** A quiet ambient pad is generated by `scripts/make_film_bgm.py` (two low chords
crossfading on a 64 s cycle, per-voice amplitude and detune drift, moving-average low-pass,
10 s fade-out, peak 0.16) and mixed in through `Scene.add_sound`. Generated rather than
licensed, so there is nothing to clear.

**A trap in `add_sound`, found the hard way.** manim sets the output length to the LONGER of the
animations and the audio. The first BGM was 210 s against ~198 s of animation, and the render
came out at exactly 3:30.03 - the last twelve seconds a frozen final frame under fading music.
The tell was the duration matching the wav to the hundredth of a second. So the pad must be
generated *shorter* than the film (`make_film_bgm.py 196` here), letting the animations set the
length and the music fade out just before the end. Regenerate it whenever the film's run time
grows past it, or the tail goes silent; never longer, or the tail freezes.

**The synthetic pad was replaced by a real recording.** Five sines through a moving average is a
drone, not music, and the reviewer said so. Two public-domain-class recordings of Satie's
Gymnopedie No. 1 were pulled from Wikimedia Commons, with the licence read from the Commons API
(`extmetadata.LicenseShortName` / `AttributionRequired`) rather than from a search summary:

| file | licence | attribution | rate | peak / mean | length |
|---|---|---|---|---|---|
| `satie_gymnopedie1_alciatore_PD.ogg` (Robin Alciatore) | public domain | none | 44.1 kHz | -6.8 / -29.0 dB | 183.6 s |
| `satie_gymnopedie1_teknopazzo_CC0.ogg` (Teknopazzo) | CC0 1.0 | none | 22.05 kHz | -0.5 / -22.6 dB | 204.8 s |

The Alciatore is the better file - full bandwidth, clean headroom - but it is 14 s shorter than
the film, and that 14 s is the entire payoff beat: the music would stop as the final reveal
begins. The Teknopazzo is lossless FLAC at half the sample rate, so nothing above 11 kHz - a
mild softness on solo piano - and covers the whole film once trimmed to 196 s with a 7 s fade.
Coverage won. Both files are kept under `results/method_animations_2026-09-17/bgm_source/`,
and `scripts/make_film_bgm.py --source` switches between them. The composition (1888) is
public domain; neither recording requires attribution, and the page credits them anyway.

## 2026-09-18 — the reversal-entry family, added to the 09-17 deck

The "Reversal Methods Logbook" is not a file. The failed reversal-entry rules of June–August
live in five folders: `stress_method_matrix_2026-08-20` (fourteen methods scored on the
thirty stressed cases; `summary.csv`, `per_case.csv`, per-method waveforms),
`ibis_intro_figures_2026-08-25/figures_methods`, `io_buf_value_match_misalignment_demo_2026-06-25`,
`io_buf_value_matched_replay_redo_2026-06-25` and `three_buffer_pad_matched_replay_v2_2026-08-04`.
The 09-17 deck's first build missed all of them; slides 16–17 now carry them.

Two things learned re-reading the matrix:

* `time_match` (818 mV) and `value_match_full` (373 mV) are the ungated `...ReplayFull`
  builders. On `io_buf_short_high_w1634ps` t-matching starts at t = 0 with Ku = 0.94, Kd =
  0.03 — pad on the wrong rail before the pulse — and value-matching starts with Kd = 0 and
  jumps Ku to 0.73 at the edge. Those scores are build defects, not the rule. The gated builds
  (`time_match_hybrid`, `coeff_match`) are what to quote: at 1634 ps they land 29 % and 23 %
  low (0.511 / 0.555 V against 0.722), native 17 % low, shipped −1.4 %, legacy and gate-match
  on the rail (1.16 / 1.21 V).
* The false pass is in the matrix's own columns: `coeff_match` pad RMSE 33 mV against
  legacy's 66 on that case, with Kd RMSE 0.238 against native's 0.026 — on every stressed
  io_buf short_high row (0.24–0.25).

Also: the `short_low` rows of the io_buf waveform CSVs report identical peaks (1.617 V at
10.11 ns) at every width for every method — that is the first full transition, not the
stressed one. Do not quote those files for the pull-down direction without checking.

## 2026-09-18 — the 09-17 animation mixed two builds (correction)

Found while building the 09-18 deck. The method animation (`scripts/film_scenes.py`,
`export_method_animation_data.py`) and its page present track 1 as "fitted stage chain from the
IBIS file + one stressed pad run", but:

- its **fit** step (`fit_data`) fits four numbers (2.590 / 2.375 / 0.512 / 0.658) to the
  **probed** gate n4 - that is the `--source real` fit, which needs the transistor. The
  file-only track-1 build (`ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810`) fits three
  numbers in the Ku domain to the file's full-swing Ku(t): s_up 2.190, s_dn 2.124, vt 0.528,
  x_lin fixed 0.45 (rms 0.023). Its **bisection** step (vt 0.528 -> 0.487) *is* the file-only
  build's calibration.
- its **"both tracks"** result (+0.9 % at 810, -3.1 % at 895, and -2.0 / -3.1 / -3.8 / -3.8 /
  +0.9 across the widths) is `real_silicon_K3_calibpad810` - stages fitted to the probed gate
  plus the measured curve. The study's track 2 above is `ibis_silicon_K3_xlin0.45_calibpad810`
  (file stages + measured curve): -0.2 / -0.0 / -0.7 / -1.7 / +0.2.
- Track 1's curve shape (vt 0.57, alpha 0.64) is ex2's measured-curve fit; "file only" holds
  for the stages and the threshold, not the two shape numbers.

The 09-18 deck's slides 28-30 use the correct builds. The animation and page are unchanged.
