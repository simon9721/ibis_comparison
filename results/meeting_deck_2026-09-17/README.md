# Meeting deck — 17 September 2026

`inside_the_buffer_2026-09-17.pptx`, built by `scripts/build_0917_deck.py` from figures made
by `scripts/build_0917_deck_figures.py`. 29 slides: 26 in the flow, 3 backup.

**This deck stops before the solution, on purpose.** It shows what the transistor's internal
nodes do under a pulse cut short, that driving our model from the transistor's own gate fixes
it, why our gate is not that node, the question that leaves, and the experiments that did not
answer it. Track 1, track 2 and the four-number stage fit are not on these slides.

## Structure: one buffer at a time, the same four steps each

The first build was ordered by kind of evidence — all the stage walks, then the lessons, then
the replays — so every step of the argument changed buffer, and slide 8 (io_buf's hump)
arrived five slides before the question it answers. The reflow orders it by buffer:

| step | ex2 (810 ps) | inv_chain (104 ps) | io_buf (2090 ps) |
|---|---|---|---|
| 1 the pulse down the chain | 5 | 9 | 14 (two panels: pull-up path, pull-down path) |
| 2 the real gate against ours, and the Ku it produces | 6 | 10 | 15 (both gates, Ku and Kd) |
| 3 put the real gate in | 8 | 11 (the failure alone) | 16 (the bump boxed) |
| 4 what that buffer adds | 7 the output stage only follows the gate | 12 why: one gate value, two Ku; 13 with the transistor's curves | 17 the bump: the schedule, seen on the pad |

On ex2 the static-map slide (7) comes before the test (8), because the test is the evidence for
it: a curve taken at full swing, driven by the real truncated gate, lands within -3...-6 %.

| # | slide | figure |
|---|---|---|
| 1-2 | title, contents | |
| 3 | the failure, in one slide - ex2 810 ps | `recap_pad`, `recap_kukd` |
| 4 | what we probed - the one schematic, native shapes | |
| 5-8 | ex2, steps 1-4 | `walk_ex2`, `gate_step_ex2`, `static_map_ex2`, `replay_ex2` |
| 9-13 | inv_chain, steps 1-4 and 4 continued | `walk_inv_chain`, `gate_step_inv_chain`, `replay_inv_fail`, `inv_why`, `replay_inv_fixed` |
| 14-17 | io_buf, steps 1-4 | `walk_io_buf`, `gate_step_io_buf`, `replay_iobuf`, `iobuf_bump` |
| 18 | three buffers, side by side - the only cross-buffer slide | (numbers, all from 5-17) |
| 19 | the question | (text) |
| 20-23 | tried after looking inside, in order (09-08 -> 09-10): measured C_comp; slow the gate; RC cascade; gate from the file, superposed | `ccomp_ex2`, `slew_ex2`, `cascade_pair`, `superpose_ex2` |
| 24-25 | the same, in one table; where this leaves us | |
| 26-29 | backup, before looking inside: reversal-entry rules; value-matching; timing parameters; pu_off | `reversal_rules`, `value_match_split`, (numbers), `pu_off_conflict` |

Every figure in the flow is drawn by `build_0917_deck_figures.py` at slide size; the only
reused study figure is `pu_off_conflict`, in backup. Still built but no longer placed:
`gate_vs_real_*`, `gate_vs_real_three`, `ku_vs_gate`, `replay_inv`, `inv_map`.

The backup slides are the methods from before the probe. They answer a different question
(which rule to apply at a reversal, which knob to turn) and the deck no longer leads to them.

**io_buf's section is at 2090 ps, not its deepest width**: the gate test ran only at 2354 and
2090 ps; ngspice stalls on the deeper three.

## Section 5: what we tried after looking inside (09-18 request)

After the question the deck shows only what was tried once the transistor was being probed,
in the order it was tried. Boundary and order are from `review_2026-09-09/README.md`: 02 (the
real gate probed, 09-08) onward. Four slides, one waveform each:

1. **Measured C_comp** (`ex2_ccomp_correction_2026-09-08`): 858 ps, ours +22.3 % at the
   declared 5 pF, +26.4 % at the measured 1.7.
2. **Slow the gate** (`gate_cascade_prototype_2026-09-09/ex2/slew500ps`, and the gate-ramp
   form from `gate_ramp_prototype_2026-09-09`): +66.6 to +48.7 %.
3. **RC cascade**: ex2 -2.6 % (a fit); inv_base8 at 102 ps -97.6 %, delay + one 60 ps stage
   +22.2 % against +65.1 %.
4. **Gate from the file through a MOSFET-shaped curve, then superposed**
   (`physics_map_gate_2026-09-10`, recomputed from its runs): ex2 0.989 against a real
   0.758.

The residual depth rule and one-gate-for-both-sides are table rows only. The current-limited
stage (review 11C onward) is the solution and is left for the next deck.

**Two ex2 baselines: it is C_comp (resolved 09-18).** Our model on ex2 at 810 ps is +73.7 %
at the measured C_comp of 1.7 pF (`gate_cascade_prototype_2026-09-09/ex2_c1.7`, the ex2 section,
slides 5-8 and 18) and +66.6-66.8 % at the declared 5 pF (the cascade folder's `ex2/shipped`,
slides 21-22, and the matrix run behind slide 3's figure). An earlier version of this note said
"it is not C_comp": that assumed slide 3's +73.7 % came from its own figure's run. It did not -
slide 3 quoted the 1.7 pF number over a 5 pF figure. Slide 3 now reads +66.8 %, next to
native's +70.7 % at the same 5 pF.

## What was wrong in the first build, so it is not repeated

* **Bullets quoting a different width from their figure**, five times. The cascade and
  slowed-gate slides were caught on the first pass; the three stage walks were not. They
  reused the 09-11 deck's 70 %-depth figures (858 / 111 / 2090 ps) under bullets written from
  the deepest width (n4 "stops at 0.76" over a figure where it reaches 0.84). Now every
  section uses one width and every bullet was read against its rendered figure.
  `build_stage_walk_figures.py --target 0.50` draws the 810 and 104 ps walks.
* **A table in another study's unit.** The old "three mechanisms" table came from
  `gate_physics_2026-09-08`: excursion ÷ supply on the 50→90 %-depth widths. Everything else
  in the deck is the node's own 0→1 swing on the 09-10 widths, so it said io_buf's deepest
  gate was 0.42 where slide 13 said 0.67. Replaced by slide 17, whose every number is on one
  of the twelve slides before it.
* **"To 0.01"** for the static map under a cut pulse had no source and is gone. The replay is
  the evidence. The C_comp condition (single-valued at the measured 1.7 pF, not the declared
  5) is in slide 7's notes.
* **The file's curve at 70 % gate is 0.28**, read from the subcircuit the replay ran
  (`KUGATE_ON` in `driver_replay_full.sub`), not the 0.19 in the first build's notes.
* **Section 5 claimed every attempt aimed at the gate's motion**; three of eight did. The
  section tags now say which is which.

## The reversal-entry family

The failed reversal-entry rules of June–August have no write-up of their own; they live in
`stress_method_matrix_2026-08-20` (scoreboard, per-method waveforms),
`ibis_intro_figures_2026-08-25`, `io_buf_value_match_misalignment_demo_2026-06-25`,
`io_buf_value_matched_replay_redo_2026-06-25` and
`three_buffer_pad_matched_replay_v2_2026-08-04`. One trap: `time_match` (818 mV) and
`value_match_full` (373 mV) are the ungated `...ReplayFull` builders, which come up on the
wrong rail before the pulse (Ku = 0.94 in the low state). Slide 19 uses the gated builds,
`time_match_hybrid` and `coeff_match`, as the 08-25 figures did.

## What the 09-18 review corrected

**"Two errors cancel on io_buf" was wrong.** The first two builds compared gate LEVELS (real
0.83 / ours 0.65 at 2090 ps; 0.67 / 0.40 at the deepest width) and explained io_buf's good
peak as a cancellation. The question that exposed it: if the gates differ that much, why does
the pad match? Because our Ku curve is not an independent measurement. `subcircuit.py` builds
it by pairing the file's Ku(t) with our own gate's full-swing ramp, so on an uninterrupted
edge curve(gate) reproduces the file's Ku(t) exactly, whatever level our gate sits at: a lower
gate simply gets a steeper curve. Measured on io_buf's rise, Ku is 0.05 / 0.33 / 0.58 on the
transistor against 0.04 / 0.29 / 0.57 on ours. What the pad does see is WHEN our gate turns
round:

| | ours turns round late by | real gate's 10-90 rise | share |
|---|---|---|---|
| ex2, 810 ps | 189 ps | 658 ps | 29 % |
| inv_chain, 104 ps | 29 ps | 52 ps | 56 % |
| io_buf, 2090 ps | 51 ps | 2685 ps | 2 % |

Same schedule on all three; it is negligible against a 2.7 ns ramp. Step 2 on every buffer now
has a Ku row under the gate row and is headed by the turn-round, not the level.

**"The file's curve is late" was half an explanation.** At full swing the file's Ku and the
transistor's agree to 7 ps. What collapses inv_chain's replay is that the model keeps one Ku
curve for a rising gate and one for a falling gate, and from the file they disagree: at gate
0.83 the rising curve gives Ku 0.64 and the falling curve 0.16 (transistor: 0.92 and 0.76). A
full swing only ever uses one at a time. A 104 ps pulse has to jump between them at the top,
at 0.326 ns with the gate still rising, and Ku peaks at 0.48 instead of 0.83. Slide 12 is
drawn in time (`inv_why`), not against the gate. The file's value at 70 % gate is 0.28, from
`KUGATE_ON` in the subcircuit that ran.

**The bump is the pull-down turning back on**, not "releasing". On the transistor it moves
202 ps across the five widths (+1.90 to +1.70 ns after the reversal); on ours 5 ps (+2.02).
It is on the deck because it is the same defect as ex2's - a schedule where the buffer has a
state - on the one io_buf event the peak cannot see. `iobuf_bump` is rebuilt at slide size;
slide 16's figure boxes it on the pad.

**Other changes from the review.** A failure slide shows only the failure: inv_chain's step 3
is the collapsed pad alone, and the fix is its own slide after the why. io_buf's walk is two
panels, pull-up path and pull-down path, and its step 2 shows both gates with Ku and Kd. Every
walk is now drawn by the figures script with the gate node in the schematic's orange. The
rules slide drops gate-matching (it leaves the transistor 0.7 ns before the reversal) and the
shipped build. The transistor's Ku/Kd is masked from -20 to +90 ps around each edge.

**One trap in the tooling.** Backslash sequences in an inline heredoc patch arrive in Python
already unescaped, so a newline escape lands in the target file as a real line break. Patches
with backslashes go through a file.

## Style

* **Waveforms over time, transistor against model, on every evidence slide.** A curve against
  the gate (slides 7, 12) appears only as the explanation after a waveform. Bullets and
  legends say "curve", not "map".
* **One schematic**, slide 4, drawn with the kit's `add_box`/`add_arrow`.
* No bar charts or scatter plots in the flow; `pu_off_conflict` is a parameter sweep and is
  in backup.
* Our model is **purple**; the real gate put into it is teal; a curve measured on the
  transistor, and the build that uses it, green; a prototype under test amber.
* **The wrong turns stay on the slides with their corrections.**

## Figure scale

Draw at the placed size: 12.2 × 5.2 in full width, 6.0 × 4.9 half, 200 dpi, 14–17 pt. Study
figures are 17–22 in wide with ~10 pt labels and land at 5–7 pt on a slide; where raw runs
exist the figure is rebuilt from raw at slide size. Reused as they are: the 09-11
`stage_walk` set (14 × 4.6), `iobuf_hump` (15 × 4.7), `pu_off_conflict` (9 × 5.5).

## Layout

`points()` returns the y it actually used and figures are placed from it: 0.30 in per line at
17 pt, 110 characters per line. A fixed y under a fixed height per bullet put figures through
wrapped text on eight slides of the first render.

**Do not send the deck without looking at it.** python-pptx reports no overlaps on slides
whose bullets run under their figures, and cannot see a bullet that disagrees with its figure.

## Rebuild

```
py -3.14 scripts/build_stage_walk_figures.py --target 0.50 --dev ex2 inv_chain
py -3.14 scripts/build_0917_deck_figures.py
py -3.14 scripts/build_0917_deck.py
powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
    -Deck results/meeting_deck_2026-09-17/inside_the_buffer_2026-09-17.pptx
```

Every number on the slides is quoted from a FINDINGS.md or a sweep.csv under `results/`, or
printed by the figure script from the runs it plots; the slide notes name the folder. Nothing
was re-simulated.
