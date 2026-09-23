# Can track 1 find the predriver stage count from the IBIS file? - findings

*2026-09-21* · plan `PLAN.md` · script `scripts/stage_count_from_file.py`

## Step 1: the file narrows K to a band, it does not pin it

Fit K = 1 ... 10 identical current-limited stages to each buffer's own full-swing Ku(t) (the
file-only fit of the track-1 builds), then take the smallest K within 5 % of the best rms (the
existing `pick_K` rule). `step1_summary.csv`, `step1_rms_vs_K.png`.

Sanity check: K = 3 on ex2 at the track-1 settings reproduces the existing build's numbers
exactly (s_up 2.19, s_dn 2.12, vt 0.53, rms 0.0233).

| buffer (netlist K) | track-1 settings: pick | strictly file-only: pick |
|---|---:|---:|
| ex2 (3) | 4 | 6 |
| ex2_base (3) | 5 | 6 |
| ex2_nomiller (3) | 5 | 6 |
| ex2_skewp (3) | 5 | 6 |
| ex2_slowpre (3) | 2 | 4 |
| ex2_weak (3) | 6 | 7 |
| inv_chain (7) | 6 | 6 |
| inv_base8 (7) | 9 | 6 |
| inv_skewp (7) | 8 | 6 |
| inv_weak (7) | 8 | **7** |
| inv_stage4 (3) | 4 | 4 |
| io_buf pull-up (1) | **1** | **1** |
| io_buf pull-down (3) | 4 | **3** |

**The plateau rule recovers the netlist count on 1 of 13 chains with the track-1 settings and
3 of 13 strictly file-only.** It is not a stage counter.

What the curves do show (`step1_rms_vs_K.png`): the rms falls steeply, then flattens, and the
**knee sits at or next to the netlist count** - at 3 for the ex2 family and inv_stage4, at 5-7
for the 7-stage chains, at 1 for io_buf's pull-up. Beyond the knee the rms keeps creeping down
by a few per cent (ex2: 0.0233 at K = 3, best 0.0215 at K = 5), so "within 5 % of the best"
lands one to three stages past it. The file therefore bounds K to about +-2 of the truth; it does
not single it out. The 09-10 result that the plateau lands exactly on 3 and 7 was a fit to the
**probed** gate, whose knee is sharper.

Not done, on purpose: tuning the rule (a looser tolerance, a knee detector) until it matches
these 13 known answers would be fitting the answer key. Whether K needs to be exact is step 2.

## Step 2: a wrong K matters - and the one stressed pad run already identifies it

69 builds at the track-1 settings, K swept over each family's range (ex2 family 2...7,
7-stage inverter chains 5...10, inv_stage4 2...6, io_buf pull-down 2...5 with pull-up 1), each
with its stage threshold placed by the one stressed pad run, scored on the five stressed widths
and the full swing. `step2_summary.csv` (every build), `step2_selectors.csv`, `step2_picks.csv`,
`step2_scores_vs_K.png`.

Pipeline check: ex2 at K = 3 reproduces the existing track-1 build exactly (-6.9 / -8.6 / -7.4 /
-4.8 / -0.1 %, lag 14-17 ps, full swing 24.4 mV).

### The peak hides a wrong K

The calibration forces the stressed peak into line at almost any K, so the peak error barely
ranks the builds - and sometimes prefers the wrong count. ex2 at K = 4 has a better peak (worst
0.5 %) than at its netlist K = 3 (worst 8.6 %), while its pad falls 262-300 ps late and its
full swing is off by 181 mV rms (K = 3: 15 ps, 24 mV). Across the ex2 family a wrong K costs
hundreds of ps of timing (K - 1: about -200 ps; K + 1: +220...+300 ps, 300 being the lag
search's cap) and 3-15x the full-swing error. On the inverter chains the cost is gentler, 20-35
ps per stage, because each stage there is fast.

### Selecting K from what track 1 already has

| selector | netlist K recovered | where it differs |
|---|---:|---|
| **timing at the calibration width** - the same one stressed pad run (best-alignment lag of the pad's falling leg) | **9 of 11** | inv_skewp, inv_weak: 8 instead of 7 |
| full-swing pad rms against the **shipped** model (which reproduces the IBIS tables; file only) | 8 of 11 | inv_base8 8; inv_skewp, inv_weak 9 |
| worst stressed peak error | 2 of 11 | scattered 2...9 |
| (step 1: the Ku-fit plateau rule) | 1 of 13 | 1-3 stages high |

Where the timing selector picks 8 instead of 7, the K = 8 build is as good or better than the
netlist one: inv_skewp worst peak 8.1 % against 7.5 %, full swing 14 against 36 mV; inv_weak
5.9 % against 5.5 %, 15 against 28 mV. Those two variants change the predriver's drive
(skewp: PMOS half width; weak: half drive at every stage), so the stage count that best
describes them need not be the number of inverters. **K is an effective parameter; the timing
of the one stressed run finds the value that works.**

io_buf: the pull-down chain's count (2...5) changes nothing on these scores - identical to
0.1 % and 1 ps. The short-high pulses and their falling leg do not exercise the pull-down path's
depth; its count would have to be read from a short-low pulse or from the timing of the
pull-down turn-on bump. Not tested here.

### What this changes in the recipe

Track 1 does not need the stage count from the netlist. With the IBIS file and the one stressed
pad run it already uses:

1. fit K = 1 ... 10 to the file's Ku(t); keep the band around the knee (step 1),
2. for each K in the band, place the threshold on the stressed run's peak (as now),
3. keep the K whose pad also matches that run's **timing**.

Step 2 is one ngspice bisection per candidate K - about ten short runs each. On these 11
buffers it recovers the netlist count on 9 and an equally good effective count on the other 2.

## Step 3: strictly file-only - K is still found, the accuracy is not kept

Step 2 again with the two non-file inputs removed: the C_comp declared in each IBIS file (ex2
family 5 pF against the loop-measured 1.7; inverter chains 0.47 against 0.3-0.6) and one
universal curve shape (vt 0.5, alpha 0.7) for every buffer. Same K ranges, resistive
fraction, calibration width. Models generated from the IBIS files into `file_only_models/`.
`step3_summary.csv`, `step3_selectors.csv`, `step3_picks.csv`, `step3_scores_vs_K.png`.

**Selecting K survives.**

| selector | step 2 (track-1 settings) | step 3 (file only) | where step 3 differs |
|---|---:|---:|---|
| timing at the calibration width | 9 of 11 | **9 of 11** | ex2_weak 2 (by 1 ps: -82 against +83); inv_chain 6 |
| full swing against the shipped model | 8 of 11 | **10 of 11** | inv_chain 6 |
| worst stressed peak | 2 of 11 | 0 of 11 | |

inv_chain's 6 is again an effective count, not a miss: at these settings K = 6 beats K = 7 on
every score (worst peak 12.8 against 15.0 %, timing 14-25 against 45-59 ps, full swing 2.6
against 54 mV).

**The accuracy does not survive on the ex2 family.** Worst stressed peak error at the netlist K:

| buffer | step 2 (track-1 settings) | step 3 (file only) |
|---|---:|---:|
| ex2 | 8.6 | 13.8 |
| ex2_base | 6.8 | 13.3 |
| ex2_slowpre | 4.9 | 4.8 |
| ex2_skewp | 9.9 | 20.4 |
| ex2_weak | 8.0 | 19.4 |
| ex2_nomiller | 6.9 | 14.1 |
| inv_chain | 25.8 | 15.0 (K = 6: 12.8) |
| inv_base8 | 6.9 | 12.5 |
| inv_stage4 | 4.6 | 3.6 |
| inv_skewp | 7.5 | 9.5 |
| inv_weak | 5.5 | 6.1 |
| io_buf | 7.7 | 8.3 |
| **within +-10 %** | **11 of 12** | **5 of 12** |

The ex2-family misses are one-sided: 12-22 % low at the mildest widths, near zero at the 50 %
width where the threshold is placed. Step 3 changed two inputs at once, so which one costs the
accuracy is not separated. The likely one is C_comp: at the declared 5 pF the file-derived Ku
overshoots to 1.23-1.74 on the ex2 family (displacement current booked as Ku), and the chain is
fitted to that Ku.

## Step 4 (09-22): the loss is C_comp; the curve shape costs a few points on two inverter variants

Step 3 changed two inputs at once. Step 4 changes one at a time, at the netlist K,
pad-calibrated and scored as before: **4a** the declared C_comp with the family curve shape,
**4b** the loop-measured C_comp with the universal shape. 22 builds; io_buf's C_comp is the
declared one in every pass, so its 4a and 4b are its step-2 and step-3 builds.
`step4_split.csv`, `step4_split.png`, `step4a_summary.csv`, `step4b_summary.csv`.

Worst stressed peak error at the netlist K (%):

| buffer | step 2: measured C_comp, family shape | **4a: declared C_comp** | **4b: universal shape** | step 3: both file-only |
|---|---:|---:|---:|---:|
| ex2 | 8.6 | 12.6 | 8.0 | 13.8 |
| ex2_base | 6.8 | 12.5 | 6.6 | 13.3 |
| ex2_slowpre | 4.9 | 6.4 | 4.4 | 4.8 |
| ex2_skewp | 9.9 | 19.9 | 10.9 | 20.4 |
| ex2_weak | 8.0 | 18.8 | 10.4 | 19.4 |
| ex2_nomiller | 6.9 | 12.5 | 5.9 | 14.1 |
| inv_chain | 25.8 | 13.4 | 28.6 | 15.0 |
| inv_base8 | 6.9 | 7.4 | 10.6 | 12.5 |
| inv_stage4 | 4.6 | 5.1 | 2.4 | 3.6 |
| inv_skewp | 7.5 | 7.6 | 10.9 | 9.5 |
| inv_weak | 5.5 | 5.3 | 4.3 | 6.1 |
| io_buf | 7.7 | 7.7 | 8.3 | 8.3 |
| **within ±10 %** | **11 of 12** | **6 of 12** | **7 of 12** | **5 of 12** |

*(Corrected by step 7 on 09-22: the table now uses models generated by today's converter
throughout. Only inv_chain moved - step 2 from 7.2 to 25.8 %, step 4b from 8.4 to 28.6 % - so
the counts fell by one. Every other buffer is identical to the decimal, which also shows the
I-V clamping the converter added changes nothing on its own.)*

* **ex2 family and inv_chain: the declared C_comp is the whole loss.** The declared C_comp
  alone (4a) lands within 1.6 points of step 3 on all seven. The universal shape alone (4b)
  stays within 2.4 points of step 2 (worst: ex2_weak 8.0 -> 10.4). The declared C_comp also
  moves the timing: at the calibration width the ex2 family's pad arrives 36-110 ps late
  under 4a, against -2...+53 ps in step 2.
* **inv_base8 and inv_skewp: the shape costs 3-4 points, C_comp nothing.** The universal
  shape adds 3.7 and 3.4 points (the family shape saturates at 0.87 of the gate swing, the
  universal one does not); the declared C_comp adds 0.5 and 0.1.
* **inv_stage4 and inv_weak: neither matters** (every pass within 2.4-6.1 %).
* **The stressed peak is not the whole picture.** On ex2, ex2_base and ex2_nomiller the
  universal shape roughly doubles the full-swing pad rms against the transistor (24 -> 51,
  32 -> 58, 35 -> 62 mV) while their peaks hold. On inv_skewp and inv_weak the track-1
  settings have the worst full swing of the four passes (36 and 28 mV, against 7-10 mV); their
  peaks do not show it.

**With the loop-measured C_comp and one universal shape, 8 of 12 stay within ±10 %; the four
misses are at 10.4-10.9 %.** C_comp is the input track 1 still takes from the probed gate.

## Step 8 (09-23): choosing K and the shape together fixes inv_chain

Step 6 chose K by the pad run's timing with the shape fixed at the universal default; the
09-22 shape grid showed the same selector picks a better shape where the shape matters. Both
come from one observation, so step 8 searches them together: every K in the file's plateau band
x three shapes (the universal default and the grid's two best), 102 builds, of which step 6's
34 are reused. The pair with the smallest |lag| at the calibration width wins.
`step8_all.csv`, `step8_picks.csv`.

| buffer | K / netlist | shape chosen | worst peak | with the universal shape | best pair in the grid |
|---|---|---|---:|---:|---|
| ex2 | 3 / 3 | 0.5 / 0.7 | 8.3 % | 8.3 | 2.3 % (K5, 0.5/0.7) |
| ex2_base | 3 / 3 | 0.5 / 0.7 | 7.0 % | 7.0 | 2.2 % (K4) |
| ex2_slowpre | 3 / 3 | 0.5 / 0.7 | 5.4 % | 5.4 | 2.5 % (K4) |
| ex2_skewp | 3 / 3 | 0.5 / 0.7 | 10.0 % | 10.0 | 1.2 % (K4, 0.4/0.9) |
| ex2_weak | 3 / 3 | 0.4 / 0.9 | **10.7 %** | 8.7 | 1.9 % (K5, 0.4/0.6) |
| ex2_nomiller | 3 / 3 | 0.5 / 0.7 | 7.2 % | 7.2 | 1.9 % (K4) |
| **inv_chain** | 6 / 7 | 0.4 / 0.9 | **5.1 %** | 34.2 | 5.1 % (the pick) |
| inv_base8 | 7 / 7 | 0.4 / 0.6 | 8.4 % | 9.6 | 2.4 % (K5) |
| inv_stage4 | 3 / 3 | 0.4 / 0.9 | 3.2 % | 3.7 | 2.9 % (K3, 0.4/0.6) |
| inv_skewp | 7 / 7 | 0.4 / 0.6 | 8.1 % | 9.9 | 4.2 % (K6) |
| inv_weak | 7 / 7 | 0.4 / 0.6 | 4.1 % | 5.1 | 1.9 % (K6) |
| io_buf | 1 / 1 | 0.4 / 0.9 | 6.1 % | 7.7 | 6.1 % (the pick) |
| **within ±10 %** | | | **11 of 12** | | |

**inv_chain goes from 34.2 % to 5.1 %** - peaks -0.7 / +2.5 / +5.1 / -0.9 / -3.6, lag -9 ps,
and its full-swing rms improves as well (35.8 against 54.0 mV). Its gate now rolls off with the
pulse width, 1.00 / 0.98 / 0.95 / 0.87 / 0.80 against the transistor's 1.00 / 0.99 / 0.97 /
0.94 / 0.88, instead of pinning at 1.00 until it collapses.

**So inv_chain's failure was the map shape, not the discharge.** The 09-22 diagnosis - the gate
staying up too long, the pad error tracking the gate's area - was the symptom of a wrong
(map, gate) pairing: the tables fix only the product, and with the universal shape the implied
gate was square where the real one rolls off. A faster final stage helped (25.8 -> 16.6 %)
because it acts on the same coupling; changing the shape removes the cause.

Note also that this file-only build now beats the **track-1** build on inv_chain (5.1 against
25.8 %), which uses the loop-measured C_comp, the measured family shape and the netlist K.

Two things the table does not hide:

* **ex2_weak regresses**, 8.7 -> 10.7 %: the timing selector chose 0.4/0.9 where the universal
  shape scored better on the peak. The count stays 11 of 12 because inv_chain enters as
  ex2_weak leaves.
* **The selector is not finding the best pair.** The grid contains builds at 1.2-4.2 % on nine
  buffers; the timing picks them on only two. Timing is what makes K identifiable at all, but
  it is a loose proxy for the peak, and a selector that used both is the obvious next step.

## Step 6 (09-22): the whole chain from the file - 11 of 12

Steps 1-5 each tested one link while holding the others at a known value. Step 6 runs the
chain end to end, with nothing from the netlist or the probed gate:

1. **C_comp** from the file's Ku overshoot knee (`scripts/ccomp_from_file.py`), the tighter of
   the Ku and Kd readings - an estimate, not a cap, so it can correct upward as well;
2. **K** fitted 1...10 against *that* model's full-swing Ku(t); the band is every K whose rms
   is within 25 % of the best, smallest three built (`plateau_band`);
3. **the stage threshold** calibrated on the one stressed pad run;
4. **K chosen** from the same run's pad timing;
5. the universal curve shape throughout.

`step6_endtoend.csv`, `step6_summary.csv`, run log `step6_run.log`.

| buffer | C_comp (file) | K selected | K netlist | worst peak | lag at calib |
|---|---:|---:|---:|---:|---:|
| ex2 | 2.64 | 3 | 3 | 8.3 % | -7 ps |
| ex2_base | 2.49 | 3 | 3 | 7.0 % | -2 ps |
| ex2_slowpre | 4.65 | 3 | 3 | 5.4 % | +8 ps |
| ex2_skewp | 1.44 | 3 | 3 | 10.0 % | -27 ps |
| ex2_weak | 1.27 | 3 | 3 | 8.7 % | +17 ps |
| ex2_nomiller | 2.30 | 3 | 3 | 7.2 % | -11 ps |
| **inv_chain** | 0.66 | **6** | 7 | **34.2 %** | +55 ps |
| inv_base8 | 0.37 | 7 | 7 | 9.6 % | +13 ps |
| inv_stage4 | 0.43 | 3 | 3 | 3.7 % | +2 ps |
| inv_skewp | 0.24 | 7 | 7 | 9.9 % | +18 ps |
| inv_weak | 0.35 | 7 | 7 | 5.1 % | +15 ps |
| io_buf | 1.68 | 1 | 1 | 7.7 % | -47 ps |
| **within ±10 %** | | **11 of 12** | | | |

The 11 of 12 counts inv_chain as the miss. Its 26-34 % is real but has nothing to do with
track 1 - see below.

**The stage count comes out right on 11 of 12** without ever being told it, and the timing
selector is what earns it. On the ex2 family the stressed peak alone would have chosen K = 4
(2 %) over K = 3 (8 %) every time - and that build arrives 200 ps late with double the
full-swing error. The peak is flattened by the threshold calibration at any K; the timing is
not.

**The band matters as much as the estimate.** The first attempt built the fit's plateau pick
+- 1, which on the ex2 family is 4-6 against a netlist 3, so the selector never saw a workable
K. The band from the fit curve itself (within 25 % of the best rms) contains the netlist count
on all 12 buffers. The per-family ranges of steps 2-3 were *not* used: they were drawn to
cover the netlist counts, which would have smuggled the answer in.

**C_comp hardly matters once K is right.** ex2_slowpre's estimate is 4.65 pF against a
measured 1.7 and it still scores 5.4 %.

### inv_chain's 26 % is not a step-6 failure: it is the Vinh defect, unmasked

inv_chain scores 34.2 % at the selected K = 6 and 26.3 % at K = 7, against 8.4 % in step 4b.
Controls (`inv_chain_control_2026-09-22/`), all at K = 7:

| build | worst peak |
|---|---:|
| step 4b: C_comp 0.60, model cached from 2026-09-09 | 8.4 % |
| this pipeline: C_comp 0.60, model generated today | 28.6 % |
| this pipeline: C_comp 0.66, model generated today | 26.3 % |
| today's model with `input_threshold` forced back to 1.4 | **8.4 %** |

So C_comp is not the cause - 0.60 and 0.66 agree - and neither is the pipeline. **The whole
difference is the converter's input threshold.** The 09-09 models use `input_threshold=1.4`,
from the 2 V Vinh this 1.8 V part's IBIS declares; today's converter clamps it to 0.9. The
defect and its mechanism were already known (`track2_train_check_2026-09-13`: the false
threshold cuts ~29 ps off every pulse); this quantifies what it was worth on the score:
**8.4 % against 28.6 %, a threefold understatement** on a buffer calibrated at 104 ps.

**Which passes this touches.** Steps 2 and 4b read the cached 09-09 models; steps 3, 4a, 5 and
6 generate their own with today's converter. The threshold differs only on the five
inverter-chain buffers (1.4 -> 0.9); the ex2 family and io_buf are identical in both. So:

* the ex2 family and io_buf rows of every table here are consistent;
* for the five inverter chains, any comparison that mixes a step-2/4b number with a
  step-3/4a/5/6 number is comparing two converter versions. Within each group it is sound.

inv_chain aside, this means **the model's real error on inv_chain is about 26-29 %, not the
7-8 % steps 2-5 reported** - and that is a property of the shipped gate-state build, not of
track 1. Step 7 rebuilds steps 2 and 4b on today's converter so the tables compare one
version.

### What inv_chain's error actually is: a gate cliff where the transistor has a ramp

Per width (135 / 119 / 111 / 106 / 104 ps), from the step-6 sweep:

| | 135 | 119 | 111 | 106 | 104 |
|---|---:|---:|---:|---:|---:|
| transistor gate maximum | 1.00 | 0.99 | 0.97 | 0.94 | 0.88 |
| our gate maximum (K = 6) | 1.00 | 1.00 | 1.00 | 1.00 | 0.84 |
| pad peak error | +2.4 | +8.7 | +19.5 | **+34.2** | +15.9 % |
| the shipped model, same widths | +1.6 | +7.1 | +18.0 | +36.5 | +65.1 % |

The real gate rolls off gently as the pulse narrows; ours stays pinned at 1.00 until it
collapses at the last width. At 106 ps a gate deficit of 0.06 costs 34 % on the pad, in line
with the known sensitivity (~4 % pad per 0.01 of gate). ex2, where the same recipe works,
tracks the partial gate at every width (0.91/0.84/0.80/0.75/0.71 against 0.94/0.88/0.84/0.80/
0.76) and stays within 8 %.

So inv_chain's failure is not the stage count - K = 6, 7 and 8 all sit at 1.00 at 106 ps - and
not C_comp. It is the same pulse-swallowing cliff seen on 09-10: between passing the pulse
whole and swallowing it, our chain has no gradual region. Our chain still beats the shipped
model only at the deepest width (+15.9 against +65.1).

**The rebuild (step 7) then moved the diagnosis.** At the track-1 settings with today's
converter, inv_chain is **25.8 %**, not the 7.2 % the cached build reported:

| | 135 | 119 | 111 | 106 | 104 |
|---|---:|---:|---:|---:|---:|
| shipped model, pad | +1.7 | +8.4 | +18.2 | +36.7 | +65.9 % |
| our chain K = 7, pad | +3.0 | +9.6 | +19.2 | **+25.8** | +4.1 % |
| our gate / transistor gate | 1.00/1.00 | 1.00/0.99 | 0.99/0.97 | **0.95/0.94** | 0.77/0.88 |

At the worst width the gate is right (0.95 against 0.94) and the pad is still 26 % high; at
the narrowest the gate is 0.11 *low* and the pad is only 4 % high. **The pad error does not
follow the gate error**, so the gate cliff is not the main cause on this buffer - the Ku-vs-gate
map is. That is inv_chain's known handoff discontinuity: the file's falling Ku curve sits 19 ps
early against the gate, so ku_fall reads 0.49 where ku_rise reads 0.96 at the same gate.

Next test, in order: (1) one Ku curve used both ways (ku_fall := ku_rise, and the average of
the two) - if the 26 % collapses, the handoff is the cause; (2) the calibration width, which
is currently the deepest and sits at the cliff edge - it also answers which stressed pulse the
single characterisation run should use.

## Step 5 (09-22): C_comp from the file, and track 1 reaches 9 of 12

`scripts/ccomp_from_file.py` reads a C_comp out of each IBIS file (the largest value whose
solved Ku stays within 2 % of 1, capped at the declared value); step 5 rebuilds at it with the
universal shape. Full table and the estimator's own findings:
`results/ccomp_from_file_2026-09-22/FINDINGS.md`. Within ±10 %: **9 of 12**, against 8 with
the loop-measured C_comp (4b) and 5 with the declared one (step 3). On the ex2 family the
estimate matches or beats the measured value; inv_chain is the one failure, because the cap at
the declared value cannot correct upward (0.468 declared, 0.6 measured, 0.66 from its knee).

## Conclusion (09-21, steps 4-5 added 09-22)

1. **The stage count is not a missing input.** The IBIS file bounds it to about +-2; the one
   stressed pad run track 1 already needs picks it, from its timing - 9 of 11 in both settings,
   the rest an equally good or better effective count. The stressed peak alone cannot.
2. **Track 1 is not yet file-only.** Without the loop-measured C_comp and the family curve
   shapes, 5 of 12 buffers stay within +-10 % (12 of 12 with them); the ex2 family falls to
   13-20 % low.
3. The open item is therefore C_comp and the curve shape, not K. **Step 4 separated them: it is
   C_comp.** The declared C_comp alone reproduces step 3's loss on the ex2 family and inv_chain;
   one universal curve shape costs 3-4 points on two inverter variants and little elsewhere.
4. **Step 5 closed most of that gap.** The Ku bound does give a file-only C_comp - as an upper
   limit, not a vanishing point: the overshoot grows with C_comp, and the declared 5 pF is
   rejected by the ex2 family's own files (Ku 1.24-1.78). Rebuilt at that estimate, a model
   made from nothing but the file and one pad run holds 9 of 12 within ±10 %.
5. Open: take the knee as the estimate instead of a cap, so it can correct upward as well
   (inv_chain, the one failure); and the curve shape, which is what still costs inv_base8 and
   inv_skewp 3-4 points.

### Run notes (09-21)

* **Disk full.** Step 3's first attempt filled drive C: at about 18:30 (0 bytes free of
  ~1 TB; this study held 16 GB, 1,890 ngspice raws). 35 of 69 builds failed. Freed 9.2 GB by
  deleting the threshold search's intermediate raws (`calib*/itNN/run.raw`, 1,049 files) in
  step2/ and step3/ - nothing reads them after a build; their decks, netlists and logs were
  kept. `build_job` now deletes its own build's intermediate raws when it finishes.
  (Simon's Optic_sim `train.py` had stopped writing at 18:14, before the disk filled.)
* **Race on shared folders.** The restart failed with "no .SUBCKT line": every build re-wrote
  the shipped model's netlist copy in the shared reference folders before reading it, and a
  parallel build of the same buffer read it mid-rewrite. Step 2 escaped because its job order
  spread each buffer's builds apart. Fixed in `gate_ramp_prototype.run_ours` (write only when
  the content changed) and by round-robin job order. A failed read raises, so no completed
  build in step 2 or 3 can carry a silently wrong result.
* The 34 builds completed before the disk filled were kept; the incomplete folders were removed
  before the rerun so no truncated output could be taken as a cache hit.

* **Three logs rewritten (09-22).** A dry run of the step-4 wiring called `build_job` with the
  simulation stubbed out, and it rewrote three existing logs as empty (`step2/logs/ex2_K3.log`,
  `step2/logs/io_buf_K1_Kd3.log`, `step3/logs/ex2_K3.log`). They were regenerated by re-running
  those three builds in a separate folder; every re-run `sweep.csv` was byte-identical to the
  original, so the builds are deterministic and no reported number changed.

### Not covered

* Step 2 ran at the **track-1 settings** - loop-measured C_comp and the family curve shapes,
  neither of which is in the file. The strictly file-only pass was run in step 1 only.
* The selector was evaluated on the same 11 buffers whose netlists are known; it was not tuned
  to them (the lag, the full-swing rms and the peak are the existing scores, untouched).
* io_buf's pull-down count (above).
