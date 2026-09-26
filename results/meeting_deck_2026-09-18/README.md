# Meeting deck — 18 September 2026

Simon's own deck, `0918_Simon_IBIS.pptx` (from `\minerfiles...\Downloads`), with the figures his
comments asked for placed into a copy: `0918_Simon_IBIS_figures.pptx`. The original was not
modified. Figures: `scripts/build_0918_deck_figures.py` -> `figures/`; placement: a one-off
python-pptx script (the image on slide 3 is swapped in place; slides 4-5 re-sized; the empty
content placeholders on 10/11/13/14/16/17 replaced by the figure). The five comments are kept.

| slide | comment | figure |
|---|---|---|
| 3 | keep transistor, native, cmd_clean named gate_state_fixed | `recap_pad` - same size and axes as the 09-04 figure, so the hand-drawn arrows and boxes stay on target; the two highlighter strokes on the old legend were removed |
| 4 | base ex2 at five stress levels, variant-figure style | `ex2_stress_levels` |
| 5 | same for inv_chain | `inv_chain_stress_levels` |
| 6 / 7 / 8 | (no comment; titled "Internal stages probing") | `schematic_{io_buf,ex2,inv_chain}` - gate-level, drawn from the netlists the probes ran (`predriver_stages_2026-09-09/*/full/`), every probed node named as on slides 9 / 12 / 15, the output-stage gate(s) orange, W in um. io_buf's pull-up path is a NAND of in and oe (the 09-09 notes called it "NOR-like"; the netlist says NAND) |
| 10 / 13 / 16 | four panels: real gate, GUP, Ku, pad | `four_panel_{io_buf,ex2,inv_chain}` |
| 11 / 14 / 17 | the same with the real gate as GUP (io_buf: GUP and GDN) | `real_gate_{io_buf,ex2,inv_chain}` |

**Bench.** Every figure is on the main bench (3.3 V, 50 ohm || 2 pF, 50 ps edges) at the file's
declared C_comp. Slides 4-5 do not use the variant bench of the 09-11 figure: it has 1 ps edges,
native HSPICE is dead on ex2 there, and its 70 % case reads +27 % against +22.5 % here - the
same 858 ps pulse as slides 12-14. Slides 10-17 are at 70 % stress, the widths of Simon's
stage-walk slides 9 / 12 / 15: io_buf 2090 ps, ex2 858 ps, inv_chain 111 ps.

**inv_chain caveat.** On the main bench our model is closer than native on inv_chain (70 %:
-1 % against +32 %). That is not the model being right: the IBIS file declares Vinh 2.0 V on a
1.8 V part, so our input comparator fires late and trims every pulse by 29 ps, which cancels
most of the overshoot (`review_2026-09-09`, 12B: with the threshold at mid-supply the shipped
error doubles, +31 -> +66 % at 104 ps). It is also why slide 17's real-gate replay reads
-32.9 %: the replay bypasses the comparator.

**ex2 numbers.** At the declared 5 pF our model is +66.8 % at 810 ps and +22.3 % at 858 ps;
the 09-17 deck's ex2 section used the measured 1.7 pF (+73.7 % / +26.4 %).

## Rebuild

```
py -3.14 scripts/build_0918_deck_figures.py
```

## Added 09-18 afternoon: slides 18-30

Appended after Simon's slide 17 on his own layout (`content_1`); his slides 1-17 are untouched
apart from the figures placed in them. Scripts: `scripts/deck_0918/place_figures.py` (figures
into slides 3-17, from a copy of his original) and `add_slides.py` (runs the former, then
appends 18-30). Figures: `build_0918_deck_figures.py`.

| # | slide | figure |
|---|---|---|
| 18 | inv_chain: why the real gate makes it worse | `inv_why_111` |
| 19 | inv_chain: the real gate with the transistor's own Ku curves | `inv_fixed_111` |
| 20 | three buffers, side by side | (table) |
| 21 | How to reproduce: the question | (text) |
| 22-25 | Tried 1-4: measured C_comp; slow the gate; RC cascade; gate from the file, superposed | 09-17 `ccomp_ex2`, `slew_ex2` (redrawn here as `gate_state_fixed`), 09-17 `cascade_pair`, `superpose_ex2` |
| 26 | what we tried, in one table | (table) |
| 27-29 | the method on ex2: track 1, track 2, both tracks | `method_track1`, 09-17 `static_map_ex2`, `method_result` |
| 30 | backup: why our model beats native on inv_chain (Vinh) | `vinh_inv` |

**C_comp on the inv_chain slides (18-19) is 0.6 pF, not the declared 0.47.** The measured Ku
curve needs the C_comp at which Ku-vs-gate is single-valued (0.6 by the loop method). The
declared-value replay was tried on 09-18: its first full-swing pass ran with a collapsing
timestep (500 MB of output in 9 minutes, where each stressed-width run in the folder is ~14 MB) and was
stopped, the partial output deleted, and slide 17's file-curve runs checked unchanged
(-32.9 %). At 0.6 pF the same pair reads -41.4 % (file's curves) and +4.5 % (measured).
Slide 20 carries the dagger for it.

**The method section (27-29) is at C_comp 1.7 pF** (the measured ex2 value), as the 09-17
film and the track studies were; hence our model's +73.7 % at 810 ps there against +66.8 %
at the declared 5 pF on slide 4. Slide 29's notes say so.

**Template line-break setting.** The template allows Latin text to wrap mid-word (an East Asian
default): "swing" broke as "sw / ing". `add_slides.py` sets `latinLnBrk="0"` on every paragraph of
the new slides only. Simon's own slides are left as they are.

**v2 (`0918_Simon_IBIS_figures_v2.pptx`), slide 18 corrected.** The first version said "at full
swing only one curve is ever used". Wrong: a full swing uses ku_rise on its rising edge and
ku_fall on its falling edge; the old figure only showed the rising edge. The point is that a
full swing hands over between the two only at gate = 1, where both give 1. The figure now has
three panels (full-swing rise, full-swing fall, 111 ps pulse). Measured on both full-swing edges
(0.6 pF runs): the file's Ku crosses 0.5 6.9 ps after the transistor's on the rise and 18.9 ps
before it on the fall (pad 50 % crossing +14 / -12 ps). The 19 ps early ku_fall is why it reads
0.49 at gate 0.95: inv_chain's gate falls from 0.95 to about 0.6 in roughly that time. v2 is a
new file because the first was open in PowerPoint; render in `slides_v2/`.

**v2, new slide 19: "Why only inv_chain: the same handoff, three gate speeds"** (`three_handoffs`).
All three buffers switch ku_rise -> ku_fall on a short pulse. Top row: the full-swing falling
edge, where ku_fall is built, in one 400 ps window for all three (gate 90->10 %: ex2 800 ps,
inv_chain 73, io_buf 449). Bottom row: the 70 % pulse around the switch. The file's Ku is off
the transistor's by +5 / +9 ps on ex2 (rise / fall) and +7 / -19 ps on inv_chain; times the
gate's speed near the top that is <= 0.01 of ex2's gate and 0.22 of inv_chain's. Hence the
handoff: ex2 0.80 -> 0.74, inv_chain 0.96 -> 0.49, io_buf 0.70 -> 0.73. With no timing error
there is no jump even on a fast gate: inv_chain's transistor curves hand over 0.98 -> 0.93.
At the declared 5 pF ex2's file curves do jump (1.16 -> 0.59, visible on slide 14): the wrong
C_comp distorts them; the pad still lands at -6 %, not decomposed. Deck is now 31 slides; the
old 19-30 are 20-31.

**v3 (`0918_Simon_IBIS_figures_v3.pptx`), the method slides 28-30 corrected.** v2 is open in
PowerPoint, hence a new file; render in `slides_v3/`.

- Slide 28 (track 1) showed a fit of four stage numbers to the *probed* gate n4. That is not
  track 1. The track-1 build (`ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810`) fits in the
  Ku domain: three stages drive the MOSFET-shaped curve, and three numbers (s_up 2.190, s_dn
  2.124, vt 0.528; x_lin fixed 0.45) are fitted so the model's Ku matches the file's own
  full-swing Ku(t), rms 0.023 - no internal node. Numbers read from the build's `calib/it00`;
  the figure re-simulates the chain from them (`track1_file_fit`). The threshold bisection
  (right panel) was already this build's.
- Slide 30's "tracks 1 + 2" was `real_silicon_K3_calibpad810` (+0.9 / -3.1 %), whose stages
  are fitted to the probed gate. Now `ibis_silicon_K3_xlin0.45_calibpad810` - track 1's stages
  with the measured curve, the 09-13 study's track 2: +0.2 % at 810 ps, -0.0 % at 895.
- Caveat now in slide 28's notes: track 1's curve shape (vt 0.57, alpha 0.64) was fitted to
  ex2's measured curve; the universal (0.5, 0.7) needs no transistor but has not been run
  through the pad calibration on ex2.
- The 09-17 animation and its page carry the same two errors (fit step, "both tracks"
  numbers); not changed.

**Explainer figure `how_mapping_works.png` (not in the deck).** How a gate-state model turns the
file's Ku(t) into Ku(gate), for our GUP (row A) and for the transistor's real gate (row B).
ex2, C_comp 1.7 pF (at the declared 5 pF the file's Ku overshoots to 1.23). Column 1: full-swing
rising edge, the file's Ku(t) paired with the gate at the same instants (markers). Column 2: the
curves the runs used (KUGATE_ON / KUGATE_OFF read from each netlist); the markers land on ku_rise,
confirming the pairing. Column 3: the 858 ps pulse, Ku = curve(gate) (KUGATE_BASE; the residual
adds <= 0.09) against the transistor's Ku re-solved from the matrix fixtures at 1.7 pF (the
matrix CSV's silicon_ku is solved at 5 pF). Pad: row A +26.4 %, row B -5.8 %.
