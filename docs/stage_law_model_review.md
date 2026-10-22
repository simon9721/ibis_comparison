# Does the stage-law model make sense? A review

*2026-10-22. Written against the state of the paper at v7 (`results/stage_law_doc_2026-10-01/`)
and the checks of `results/stage_law_model_checks_2026-10-22/`. Every number below is a stored
result; the file that holds it is named.*

The question was asked because the result looks good (within 10 % of the transistor-level pad
peak on twelve buffers, where the native element is at 20–100 %) while some of the numbers that
produce it, the "(0.57, 0.64)" map of earlier versions among them, were hard to trust. This
review goes through the model piece by piece and says, for each, what is physics, what is
assumed, what the data support, and what they do not.

## 1. Verdict in short

- **The structure is sound and is the right structure.** A chain of stages whose output is the
  gate of the output device, and a static map from the gate to the conducting fraction, is what
  a predriver *is*. The alternative, a coefficient replayed against time, has no state and
  cannot represent an interrupted transition; the +71 % of the native element on ex2 is not a
  tuning problem but a missing variable (the gate).
- **The stage law itself is the α-power inverter with two simplifications**, both stated and
  both weakly constrained by the file (Section 3). It is verified at the gate on two buffers
  where the gate can be probed: fitted at full swing only, it predicts the stressed gate of ex2
  within 0.04 at every width where linear superposition is off by 0.17 (Table VII of the paper).
- **The identification is honest about what the file cannot fix** (stage count, map shape,
  threshold), and the one measurement is used for exactly those. This is the strongest part of
  the paper, and it is also where the numbers that looked arbitrary come from: the file leaves
  the threshold free to slide, so the fitted threshold is wherever the assumed map lets the
  composition match, which is why eight of twelve fitted thresholds sat on the bound.
- **What should make a reader hesitate, and did make the user hesitate, is not the model but
  the constants around it.** Four built-in constants (x_lin, p, the three map shapes, the band
  rule) were chosen on the same twelve buffers the result is scored on; the test set is three
  designs plus nine single-change variants; and the pad result moves by three to five points of
  peak error when x_lin moves by 0.1 (Section 6). None of this is hidden in the paper, but it
  bounds how much the "12 of 12 within 10 %" means.
- **Two things were wrong in earlier versions and are fixed in v7.** The explanatory figures
  used a setting the method never uses (a map measured on the probed gate and a C_comp measured
  on the netlist), so two different "fitted thresholds" and two different maps appeared with no
  rule for which was which; and x_lin was fitted on two buffers and fixed on ten, an exception
  with no rule behind it. v7 uses one setting throughout and one x_lin on every buffer, and the
  uniform rule scores as well as the exception did (Section 6).

## 2. The derivation: what is physics and what is assumed

The stage law (19) is derived in four steps from Kirchhoff at the inverter's output node (1) and
the α-power law [Sakurai–Newton] for each device (2)–(5). The derivation is exact up to (15);
the paper's own check (one stage with p = α driven by a ramp reproduces the closed-form delay of
the α-power paper within 4 ps) says the algebra is right. Two approximations follow:

| | what is replaced | by | what it costs |
|---|---|---|---|
| A1 | the measured gate exponent α (1.10–1.63 on the four devices of Table II) | p = 1, linear in the drive above threshold | the shape of the rising edge for a slowly rising input; at full swing the input dwells at the rail where g^p = 1 for every p, so the file cannot see it |
| A2 | the saturation boundary x_0 g^{α/2}, which shrinks as the gate drive falls | a constant x_lin = 0.45 | the drive dependence of the ramp-to-tail knee; this is the "partial-drive regime" where inv_chain's stressed gate undershoots by 0.18 at 104 ps, and the paper names A2 as the candidate cause |

Plus A0 (one V_TH, α, x_0 for both devices of a stage; the α-power paper does the same) and A3
(K identical normalized stages; Section 3 below). The derivation is not where the risk is.

One inherited limit matters more than it looks: the α-power paper validates its model for fast
inputs and neglects the opposing device, and states it does not reproduce the region near and
below threshold. A truncated pulse holds every stage *near its threshold with both devices
conducting*, outside that regime. So the stage law's accuracy under stress rests on the tests of
Section V of the paper and not on the α-power paper's validation. The paper says this in Section
VI; it is the right caveat and should stay.

## 3. The identical-stage chain

A3 says the K stages share one parameter set (s_up, s_dn, v_t, x_lin, p). Real predrivers are
tapered (inv_chain is literally an eight-stage tapered chain), so stage rates differ; the model
pretends they do not. Three things justify keeping it:

1. **The file cannot support more.** A complete transition is two edges: two rates and one
   delay. The fit (26) has exactly three numbers to spend. With every stage free (4(K−1) more
   parameters) the fit on ex2 with K = 2 reaches a *lower* full-swing residual than the correct
   K = 3 identical chain, with one very slow stage and one fast one, and that chain extinguishes
   short pulses (stressed gate peak 0.228 where 0.758 is measured; Section IV-E of the paper).
   A3 removes that solution.
2. **The stage count is then the single structural unknown**, and the file ranks K only
   weakly: on ex2, K = 5 to 9 lie within 0.002 of each other and the minimum is at K = 6 for a
   three-stage netlist; on inv_chain K = 6 to 9 lie within 0.0008
   (`stage_count_from_file_2026-09-21/step1_summary.csv`, pass est_knee). The paper's answer is
   a band of three K and a selection by the measurement. On the twelve buffers the selected K
   equals the netlist count on all twelve after the uniform-x_lin change (it was eleven of
   twelve before: inv_chain selected 6 against 7 with x_lin fitted at 0.28).
3. **The internal gate it produces resembles the real one** without ever being fitted to it:
   0.03–0.05 low and 56–74 ps early on ex2; 0.01–0.14 low and 4–10 ps early on inv_chain
   (`results/stage_law_doc_2026-10-01/gate_internal_check.csv`, the selected builds). The
   inv_chain 0.14 is at the narrowest pulse and is the A2 regime again.

So A3 is a modelling choice forced by identifiability, and its price is paid in the partial-drive
regime of the narrowest pulses. That is where the remaining error of the method lives
(inv_chain's worst peak error is at its narrowest width in every candidate of the checks).

## 4. The static map

The claim that K_u is a function of the gate alone is the hinge of the whole model, because it
is what lets a chain that produces a gate produce a conducting fraction. The evidence is direct:
on the three buffers whose gate can be probed, K_u plotted against the gate traces one curve
whether the gate is rising or falling, within 0.07–0.11 (Section III-C of the paper;
`gate_physics` study). The residual loop width is what measures C_comp (ex2 ~1.7 pF against the
declared 5 pF), which is a separate finding of the project and is consistent with the map being
static.

Where the earlier versions went wrong is not the physics but the bookkeeping. The map measured
on ex2's probed gate fits the two-parameter formula at (0.57, 0.64). The method cannot measure
it (the file gives K_u against time, the map is K_u against the gate, and the file has no gate),
so it offers three shapes, (0.50, 0.70), (0.40, 0.60), (0.40, 0.90), and lets the measurement
choose. v5 and v6 explained the fit with the measured map and ran the procedure with the grid,
so "the fitted v_t of ex2" was 0.487 in one place and 0.700 in another, and the reader had no way
to know that both were right. v7 explains everything in the setting the procedure builds (C_comp
2.64 pF from the file, K = 3, map (0.50, 0.70)) and names the measured map only in words, as the
evidence for the static-map claim. The number (0.57, 0.64) survives only in the legend of Fig.
8(b) as the formula fitted to the measured curve.

What the data say about the shapes (`results/stage_law_doc_2026-10-01/shape_fileonly/`):

| buffer | K | residual of (26) over six shapes | selected by the measurement |
|---|---:|---|---|
| ex2 | 3 | 0.0233–0.0241 (4 % spread); the largest is (0.6, 0.6), the shape nearest the measured map | (0.5, 0.7), tied best at 0.0233 |
| inv_chain | 7 | 0.0080–0.0084 (5 % spread) | (0.4, 0.6), best at 0.0080 |

The file does not choose the map, and the small preference it has does not point at the measured
one. Two maps that fit the file alike, (0.6, 0.6) and (0.4, 0.6), give a K_u peak of 0.26 and of
0.00 under the same 810 ps pulse (Fig. 14 of the paper). This is the identification result in one
picture, and it is correct.

**Least well founded element:** the three shapes. Two of them were retained from an earlier
search scored on the same twelve buffers, and the measured maps of the three probed buffers all
fall inside the range the three span, which is reassuring on these buffers and says nothing about
others.

## 5. What the file identifies, and the threshold on its bound

The fit (26) has three free numbers and the file supplies two edges. The rates are well
determined (a 27 % change in s_up triples the residual on ex2); the threshold is not. On the
file-only landscape of ex2 (`fit_search_fileonly/landscape.npz`), at the fitted rates the
residual is 0.128 at v_t = 0, 0.0233 at the bound 0.7, and its minimum, 0.0231, is at v_t = 0.77,
*beyond* the bound. The bound is a constant of the method (0 ≤ v_t ≤ 0.7) and seven of the twelve
fitted thresholds sit on it (`fit_all.csv`, v7).

Does this matter? Three observations:

- The residual difference between the bound and the free optimum is 1 %, well inside the spread
  between map shapes (4 %). The file is not fighting the bound; it is indifferent.
- Calibration then lowers v_t on every buffer calibrated through the threshold (ex2: 0.700 →
  0.632). So the final threshold is set by the measurement, not by the file, and the bound only
  decides where the search starts from.
- The calibration curve (Fig. 17(a) of the paper) shows why the threshold is the right knob:
  the peak error runs from +40 % at v_t = 0 through +57 % near 0.35 down to −97 % at the bound,
  where the chain extinguishes the pulse. A bisection on the sign always finds the crossing, and
  the crossing is steep, so the calibrated v_t is well determined (±0.005 moves the peak by a
  few percent).

The honest statement, which v7 makes, is that v_t fitted to the file is an effective number with
no device meaning, that the file determines it poorly, and that the method does not rely on it.
The one place the bound could bite is a buffer whose true effective threshold is above 0.7; the
calibration can only lower v_t from the bound (or fall back to a rate scale), and such a buffer
would be calibrated through the fallback. io_buf is the existing example of the fallback (its
single-stage chain cannot bracket the peak with v_t; the rates are scaled by 1.09), and it scores
5.6 %.

## 6. x_lin: one rule, and the sensitivity

Until v6 the pad result fitted x_lin on inv_chain (0.28) and io_buf (0.41) and fixed it at 0.45
on the other ten. That was an exception without a rule. `scripts/stage_law_model_checks.py`
rebuilt every candidate of those two buffers with x_lin = 0.45 and let the procedure's own
selector choose (`results/stage_law_model_checks_2026-10-22/checks.csv`):

| buffer | selected with x_lin = 0.45 | worst peak, five widths | before (x_lin fitted) |
|---|---|---:|---:|
| inv_chain | K = 7, (0.4, 0.6) | 5.8 % | 5.1 % (K = 6, (0.4, 0.9), x_lin 0.28) |
| io_buf | K = 1, K_d = 3, (0.5, 0.7) | 5.6 % | 7.7 % (x_lin 0.41) |

One rule is as good as the exception (one buffer 0.7 points worse, one 2.1 points better), and
inv_chain now selects the netlist stage count. v7 uses the uniform rule everywhere.

The sensitivity is the finding to carry forward:

| candidate | x_lin 0.35 | 0.45 | 0.55 |
|---|---:|---:|---:|
| ex2, K = 3, (0.5, 0.7) | 5.5 % | 8.3 % | 10.4 % |
| inv_chain, K = 6, (0.4, 0.9) | 2.3 % | 4.9 % | 7.2 % |

Three to five points per 0.1, monotonic, and lower values score better on both. So 0.45 is not
the best value for the pad result on these buffers, which is worth saying because it means the
constant was *not* tuned to the result (it came from gate-domain fits of the probed stages:
0.37–0.47 on ex2, 0.52–0.63 on inv_chain, and the α-power paper's 0.5–0.55). It also means the
result would improve on these two buffers by moving x_lin down, which is exactly the kind of
tuning the project has refused to do, rightly: a value chosen on the pad result of the test
buffers would be circular. The useful next step is a *rule* for x_lin, from the file or from the
measurement, not a better constant. Candidates: the knee of the V–T waveform itself (the ratio of
the constant-slope part of the edge to the exponential tail is x_lin/s_up in one stage), which
the file has; or a second feature of the one measurement. Neither has been tried.

## 7. The calibration and the selection: one measurement, two decisions

The single stressed pad waveform is used twice: its peak sets v_t for each of nine candidates
(one degree of freedom at one width), and its shape over the pulse and the return selects among
the nine. Two things to check:

1. **Is the held-out part of the score real?** The score is the worst peak error over five
   widths, one of which is the calibration width. At the calibration width every candidate is at
   ~0 % by construction, so the worst error comes from the other four widths, which the procedure
   never sees. On ex2 the selected candidate is at −1.8 % at the calibration width and its worst
   error over the five widths is 8.3 % (`ledger_ex2.csv`); on inv_chain's selected candidate the
   five errors run from −5.4 % (the calibration width) to +5.8 % (`checks.csv`). So the held-out
   widths carry most of the score, not all of it: the bisection stops after ten runs and the
   calibration-width error is not always near zero. The five widths of one
   buffer sample one trajectory and are strongly correlated; the statistical weight is the number
   of buffers, which is three designs and nine variants of two of them (Section 8).
2. **Does the selector choose the right thing?** The waveform selector is within 2 mV of the
   best candidate each grid contains, averaged over the twelve buffers (50.6 mV against 48.7 mV
   mean pad rms at the five widths), and the peak-chasing alternative is at 223 mV. On ex2 the
   selected candidate's worst peak error is 8.3 % where the K = 4 and K = 5 candidates would
   have scored 2–3.5 %, but those arrive 97–300 ps late at the calibration width. The selector
   chooses timing over peak, which is the right choice for a waveform model and costs six points
   of the headline number on ex2. The paper says so.

The calibration mechanism itself is simple and I find no fault in it. One fragility: it needs
the measured pulse to be at about 50 % depth. Deeper pulses were not tested (Section V-C of the
paper), and the model's behaviour as the pulse is extinguished (the hard threshold of (17) cuts
it off abruptly where a transistor chain loses it gradually) is the untested region.

## 8. The circularity of the constants and the size of the test set

Four constants are built in: x_lin = 0.45, p = 1, the three map shapes, and the band rule (three
smallest K within 25 % of the best). All four were chosen with transistor-level knowledge of the
same twelve buffers. The band contains the netlist K on all twelve, "a property of the rule as
tuned and not an independent validation" in the paper's own words, and the same holds for the
shapes. The test set is effectively three independent designs; the nine variants each change one
property (device widths, PMOS skew, predriver widths, Miller capacitances, stage count) and are
valuable as a sensitivity test of the *method* but do not add independent evidence about the
*constants*.

This is the real limit of the evidence, and the paper states it (Sections V-C and VI). It is not a
reason to distrust the model; it is a reason not to generalize the 10 % until a buffer from
outside the set has been tried.

## 9. The native baseline

The native element is the bar, not the target, and the paper does not tune toward it. Two points
on the comparison are worth keeping in mind:

- On the five ex2 variant files the native element produced no waveform at all as generated;
  the starred numbers in Table X come from the same files with their V–T tables resampled onto
  200 rows (`results/native_revived_variants_2026-10-18/`). The cause is characterized (sub-mV
  sample-to-sample ripple at < 5 ps sampling kills the two-waveform solver; 0.3 mV rms of noise
  added to the shipped file kills it too, 0.1 mV does not) and the revived score depends on the
  edit by up to 9 points. The paper uses the least invasive edit and says so. The honest reading
  is that native's number on those five is "fails, and 34–64 % when revived".
- The native element's full-swing coefficient agrees with the converter's two-fixture solution
  within 0.003 rms (`native_full_swing/ex2_c2.64.npz`, v7), so the comparison at the pad is a
  comparison of the replay, not of two different solutions. That is the right baseline.

## 10. What would be convincing

In order of value:

1. **One buffer from outside the set**, with its IBIS file and one stressed pad run, built with
   the procedure unchanged and scored at five widths. A different process and a different
   predriver topology (a tapered chain with a different taper, or a buffer with a level shifter)
   would test the constants as nothing in the current set does.
2. **A rule for x_lin** read from the file or from the measurement (Section 6), replacing one
   constant by a derived quantity, with the sensitivity table as the yardstick.
3. **Pulse trains and other loads.** The project's earlier finding that errors re-settle in 3–4
   pulses (no accumulation) is encouraging but was made with an earlier model; the stage-law
   model has not been run on a train, and a train is where a predriver model should shine.
4. **A map measured on a buffer outside the set**, to see whether it falls inside the span of
   the three shapes. If it does not, the grid is the first thing to change.
5. **Deeper pulses** (30–40 % of the settled swing), where the hard threshold of the stage law
   extinguishes the pulse abruptly and the transistor does not.

## 11. Where the "(0.57, 0.64)" came from, for the record

ex2's map measured on its probed gate, fitted by the two-parameter formula: v_t,map = 0.57 (the
gate level at which the output device starts to conduct), a = 0.64 (the bend of the curve above
it). It was used in v5 and v6 to *explain* the fit with the best possible map, while the
*procedure* used the grid shape (0.50, 0.70). Nothing was wrong with either number; the error
was running two settings through one paper. v7 has one setting, and the probed map appears once,
in words, as the evidence that the map is static.

## Files

| what | where |
|---|---|
| the two checks (uniform x_lin, sensitivity) | `scripts/stage_law_model_checks.py`, `results/stage_law_model_checks_2026-10-22/{checks.csv, FINDINGS.md}` |
| file-only fit data (landscape, paths, six shapes, targets) | `results/stage_law_doc_2026-10-01/fileonly_fit_data.py` → `fit_search_fileonly/`, `shape_fileonly/` |
| the internal gate of the selected builds | `results/stage_law_doc_2026-10-01/gate_internal_check.{py,csv,png}` |
| the native coefficient at full swing, 2.64 pF file | `results/stage_law_doc_2026-10-01/native_full_swing.py` → `native_full_swing/ex2_c2.64.npz` |
| the paper, v7 | `results/stage_law_doc_2026-10-01/stage_law_paper_v7_ieee.docx`, `stage_law_paper_v7_draft.md` |
