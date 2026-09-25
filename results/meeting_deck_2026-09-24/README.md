# Meeting deck — 24 September 2026

`0924_track1_story.pptx`, 36 slides. Built by `scripts/build_0924_deck.py`; figures by
`scripts/build_0924_deck_figures.py`. Rendered to `slides/` with
`scripts/render_deck_slides.ps1`. Style and layout come from Simon's 09-18 deck; none of his
slides are carried over.

## Why this deck exists

Every earlier telling of track 1 started from the method and worked back to the evidence. This
one runs in the order the work actually went: probe the gate, measure the map, show the map
works, show why our own gate fails, and only then ask how to reproduce that gate from the file.

**Every content slide carries a figure.** That was a specific instruction after the first
version: a slide of bullets explains nothing, and the method half in particular was being
asserted rather than shown.

## Slides

| # | title |
|---|---|
| 1 | Reproducing the real gate from the IBIS file |
| 2 | 1 · We can look inside our own test chips |
| 3 | 2 · Measuring the map: pair Ku(t) with the gate, instant by instant |
| 4 | 3 · Does the measured map work?  ex2 |
| 5 | 3 · Does the measured map work?  inv_chain |
| 6 | 3 · So the output stage is not the problem |
| 7 | 4 · Why our gate fails: the real gate changes shape, GUP does not |
| 8 | 4 · What that shape difference does downstream |
| 9 | 5 · So the problem is now a precise one |
| 10 | 6 · What the file fixes, and what it leaves open |
| 11 | 7 · One more measurement, and a stressed pulse is the one |
| 12 | 8 · But a few samples need a family of shapes to choose from |
| 13 | 9 · What the stage law is a model of |
| 14 | 10 · The device's two voltages, in our two variables |
| 15 | 11 · What one MOSFET actually does |
| 16 | 12 · What we keep of that, and what we replace |
| 17 | 13 · Term by term: the transistor's equation and ours |
| 18 | 14 · The law, with where each piece came from |
| 19 | 15 · The four numbers that leaves |
| 20 | 16 · What each of the four actually does |
| 21 | 17 · Why a chain, and not one stage |
| 22 | 17 · So: K identical stages, then the file's own map |
| 23 | 18 · Before the recipe: C_comp is an input, and this file's is wrong |
| 24 | 19 · Recipe step 1 of 4 — fit the four numbers to the file's Ku(t) |
| 25 | 20 · Recipe step 2 of 4 — enumerate what the file cannot choose |
| 26 | 21 · Recipe step 3 of 4 — the stressed run sets the amplitude |
| 27 | 22 · Recipe step 4 of 4 — the same run picks one of the nine |
| 28 | 23 · The recipe, end to end |
| 29 | Result · ex2 |
| 30 | Result · inv_chain |
| 31 | Result · io_buf |
| 32 | Result · every buffer, worst of its stressed widths |
| 33 | Result · what this does not cover yet |
| 34 | Backup · where Ku(t) comes from |
| 35 | Backup · the nine candidates as waveforms |
| 36 | Backup · inv_chain's input threshold |

## Built on the 09-17 method film

The film (`results/method_animations_2026-09-17`, `scripts/film_scenes.py`) explains several
steps better than any earlier deck did, and `scripts/export_method_animation_data.py` had
already dumped its data to plain arrays. Five deck figures now come from that export, so the
slides teach the same way the film does:

| figure | the beat it carries | slide |
|---|---|---|
| `solve_ku` | two loads, two unknowns, one instant — where Ku(t) comes from at all | 10 |
| `prior_shape` | the measured map against the analytic shape track 1 must assume | 11 |
| `knobs` | what each of the four stage numbers does, swept one at a time | 15 |
| `fit_search` | the four numbers searched until the chain lands on the file's Ku(t) | 18 |
| `bisection` | the stressed run placing the threshold, every iteration it wrote | 20 |

`knobs` is drawn on a **truncated** pulse rather than a full transition. On a full swing the
discharge rate does nothing visible and the panel drew five identical curves; on the 810 ps
pulse all four numbers act, which is also the regime the deck is about.

## Other figures built here

`map_from_probe`, `works_levels_*`, `gate_shape_*`, `ku_consequence_*` (the evidence half);
`stage_nonlinear`, `sampling_grid`, `stage_law`, `model_blocks`, `k_choice`, `calib_select`
(the method); `map_summary`, `what_we_have`, `coverage` (the three slides that were otherwise
bullets only). All are drawn from runs already on disk — nothing is re-simulated.

## Two corrections worth knowing

**The "does it work" slides.** The first build drove the real gate through the **IBIS-implied**
map. On ex2 that is fine, −3 to −6 %. On inv_chain it collapses, −14 % at 135 ps to
−69 % at 104 ps, which would have contradicted the slide's own title. The build that works
is the real gate through the map **measured at full swing**: ex2 +1.2 to −4.7 %, inv_chain
+2.0 to +9.4 %. Both ingredients matter.

**k_choice.** It first drew the nine built models' full-swing Ku(t) captioned
"indistinguishable". They are not — they are post-calibration, and the calibration moves vt,
which moves the timing. What the file actually sees is the fit residual before any stressed run
touches the model, so the panel shows that instead.

## What the slide-by-slide review changed

A read-through of every slide found more than the figures. In order:

* **Where Ku(t) comes from** was a detour for an audience that already knows IBIS — moved to
  backup.
* **Two figures were plotting empty windows.** `fit_search` and `bisection` both drew a flat
  black line and nothing else, because I had assumed a 5 ns input offset that is not in the
  film's export: `fit_t` runs −0.4 to 13 ns with the input at 0, and `bis_t` is already
  measured from the edge. Both windows corrected.
* **The four numbers were described in prose.** They now have a slide of their own: the stage
  law written out with each term coloured, and a table giving each symbol, what it is, what it
  decides, and where its value comes from.
* **The stage equation had no source and K appeared unexplained.** The equation now follows the
  physics slide and is dissected on the definition slide; the block diagram no longer repeats
  it; and K is justified from the probed chain rather than asserted.
* **The C_comp slide showed a result, not an argument.** A bar chart of twelve buffers is
  replaced by the mechanism: solved peak Ku against assumed C_comp, with the Ku = 1 ceiling and
  the declared value sitting above it at 1.24.
* **The selection slide showed the winner but not the choosing.** It now ranks all nine
  candidates twice — on the whole waveform, where they run 59 to 425 mV, and on the peak,
  where every one is within 2.5 % and there is no order at all.

Two numbers were wrong and are corrected. The calibration slide quoted “97 % low” from a
different build than its own figure showed: in the film's data the fit lands on vt 0.528, which
leaves the pad **27.6 %** low, and −98.7 % is the far end of the *bracket*, not the starting
point. And the selection slide said the peak spread was “within 2 %” when it is 2.5 %.

### The second pass, slide by slide

Reading all twenty-seven rendered slides again found defects that only show up in the render.

* **Every bullet was bold.** `bullets()` took `**` as a flag on the whole line rather than as a
  span, so a line that opened with emphasis went bold end to end and emphasis in the middle of
  a line was silently dropped. It now splits on `**` and bolds the segments between the
  markers, so a bullet can put its weight on the clause that carries the claim. Only the last
  line that *opens* with emphasis takes the accent colour.
* **Legends sat on the evidence.** `ku_consequence` put a legend box in the upper right of each
  pad panel, which is exactly where the purple overshoot the slide exists to show goes; and
  `solve_ku`'s legend covered the pull-down branch for most of its travel. Both now label their
  curves directly, with one shared legend under the figure.
* **Labels ran off, or onto each other.** `works_levels`' in-panel names were wider than a
  3-inch panel; `sampling_grid` cut all five curves at the same height, so the five depth
  labels landed on one spot; `fit_search` wrote the fitted values across the marker trail; and
  `solve_ku`'s load markers sat where the pull-up curve runs. All placed clear.
* **inv_chain's panels were mostly empty.** The window was 1.2 ns wide for a 130 ps pulse.
* **One sentence was garbled** on the results slide — "We buy accuracy in stressed accuracy
  with full-swing accuracy" — and the backup slide claimed the nine candidates share *the
  measured peak* while the figure plainly shows them peaking at different times. They share the
  peak **height**; the calibration put it there. Both fixed, on the slide and in the figure.
* **Numeric cross-references were removed.** The numbers in the titles are section numbers, not
  slide numbers, so "(slide 7)" pointed at nothing; one was wrong outright. The two result
  slides also had no section marker while every other slide does — they now read `Result · …`.

### The third pass: the method half, again

* **The stage law now has a source.** Slide 13 is three facts about one CMOS inverter, each
  drawn and each contributing one factor; slide 14 multiplies them and dissects the result. The
  equation no longer appears asserted.
* **s_up and s_dn were described as currents. They are not.** `v` is normalised, so `dv/dt` is
  swings per nanosecond and `s_up` is a slope — ex2 fits 2.59/ns, 0.39 ns to cross a stage's
  swing flat out. The physics behind it is `I_sat/(C·V_swing)`, but no current is ever computed.
  `x_lin` is named for the MOSFET's **linear (triode) region**.
* **Does the file give vt?** It gives `Vinh`/`Vinl`, the input **pin's** thresholds, and the
  converter does use them, for the input comparator. `vt` is an **internal** stage's threshold
  and the file never describes that node. Now stated on the slide.
* **"Why a chain" now shows why.** Fit K = 1 as well as it can be fitted and it still misses the
  file's own Ku(t) by 4.6× the best error (rms 0.0920 against 0.0202): one stage is one ramp, it
  starts when the input does where the real Ku(t) waits, and bends over early. The file rules a
  single stage out on its own, with no stressed data.
* **C_comp is no longer a step.** It is an input the method assumes, with a Ku ≤ 1 validity
  check; when s2ibispy extracts it, it drops into the same slot. The recipe is now four numbered
  steps, and `docs/track1_recipe.md` carries the same mapping (S1 is the input; S2–S6 are the
  four steps).
* **"The chain" is now defined before it is used** — a slide of its own, immediately before the
  fit that talks about it — and the degeneracy slide ends on the resolution rather than the
  problem.
* **The calibration slide is a picture.** Which run (the deepest rung), what is taken off it
  (the peak), how it is used (bisection on vt), and what it buys — in three panels instead of
  three paragraphs.

### The results are now the three-way comparison

`three_way.png` puts transistor, HSPICE native IBIS and track 1 on one axis at the deepest
stressed pulse: native +71 %, +87 %, −20 % against track 1's −2 %, −4 %, +2 %.
`endtoend_3.png` does the same per buffer.

**Native does not converge on the five ex2 variants.** Its worst peak error reads −97 to
−100 % at *every* depth on those files, the mildest included, which is not a model error but
HSPICE's two-waveform solver dying on a 1 ps file (`docs/native_vt_waveform_modes.md`). Those
bars are drawn hatched and excluded from the comparison rather than scored as a 100 % win.
Native and track 1 are read from the same five widths per buffer:
`gate_cascade_prototype_2026-09-09/<dev>/sweep.csv` and
`selector_from_one_run_2026-09-23/selector_picks.csv`.

### The fourth pass: the equation, and results per buffer

* **What the equivalent circuit is a model OF.** Slide 13 now zooms in from ex2's own
  schematic: the predriver chain, one inverter of it drawn as transistors, and then — during a
  rise, with the NMOS off and the PMOS saturated — the current source into a capacitance. The
  current-source-and-capacitor picture arrives as a consequence instead of as an assertion.
* **Every symbol in the law now has a picture.** Slide 14 is the equation over three panels:
  `dv/dt` as a rise-over-run on the stage's own output (which is where "swings per nanosecond"
  comes from), `h(u)` as the share of full current against the input with the dead zone below
  `vt` shaded, and the taper against how far the output has got.
* **The parameter table moved to a slide of its own.** On slide 14 it was crowding the thing it
  was supposed to explain.
* **The results are per buffer**, three depths each — roughly 50 / 70 / 90 % of each ladder.
  Only the deepest rung of each was measured, so the other two are out-of-sample predictions,
  and the slides say so. Numbers, native against track 1:

  | buffer | deepest | middle | mildest |
  |---|---|---|---|
  | ex2 | +70.7 / −1.8 % | +24.0 / −7.4 % | +1.3 / −6.6 % |
  | inv_chain | +87.2 / −3.6 % | +31.7 / +5.0 % | +7.4 / −0.7 % |
  | io_buf | −20.4 / +1.6 % | −10.2 / +7.0 % | −5.0 / +4.7 % |

  Worth saying out loud at the meeting: on ex2 native comes right by the mildest rung (+1.3 %)
  while track 1 sits at −6.6 %. Track 1 is flat across the ladder where native collapses, which
  is the trade, but it is not uniformly better at every depth.
* **`bullets()` now refuses an unpaired `*`.** Three literal asterisks reached rendered slides
  across these rounds because the emphasis markers are `**` and a single one renders as itself.

### The fifth pass: teach the law, and say what is invented

The method core is four slides now instead of one, and every factor of the stage law states on
its face whether it has a source.

* **Slide 14 teaches the device.** The three regimes of one MOSFET, drawn as an I-V family with
  the `V_DS = V_GS - V_th` boundary, beside the book's equation for each. Source: Leventhal &
  Green, *Semiconductor Modeling*, §3.8 printed p.89 (pdf 105) — SPICE Level 1
  (Shichman-Hodges), eq. 3-23 to 3-25. Note the naming trap the book itself flags on p.63: a
  MOSFET's *saturation* region is its constant-current one, the opposite sense to a BJT's.
* **Slide 15 puts our version on top of the book's, region by region**, and labels each one:

  | regime | the book | ours | verdict |
  |---|---|---|---|
  | below threshold | `I_D = 0` | `h = 0` | **same** |
  | saturated | `∝ (V_GS − V_th)²` | `∝ (u − vt)^p`, p = 1 | **same form, our exponent** |
  | triode | `V_DS(2(V_GS−V_th) − V_DS)`, a parabola | a straight line | **ours, no source** |

  With the numbers attached: half way into the triode region the book passes 0.75 of full
  current and we pass 0.50. We give the current up faster than the device does. And `p = 1` is
  not a claim about the device — it is an admission that the file cannot see `p` (every value
  from 1 to 2 fits the full-swing Ku(t) to rms 0.002–0.007); the book's own value is 2.
* **Slide 16 is the assembled law, colour-badged**: green has a source, amber is the source's
  form with one thing changed, red has none. K identical stages in series is called out
  separately as the other thing with no source behind it.
* `docs/track1_recipe.md` carries the same factor-by-factor table, so the written recipe and
  the deck say the same thing about provenance.

### The sixth pass: the missing link

Reading 13 to 16 as a cold viewer, the chain broke in one place. Slide 13 introduces **u** and
**v**. Slide 15 talks entirely in **V_GS** and **V_DS**. Slide 16 then plots "share of full
current" against u and against v — and nothing had ever said those were the same two
quantities. A new slide 14 makes the bridge: for the device that is conducting, measured down
from its own rail, **u = |V_GS| / swing** and **1 − v = |V_DS| / swing**.

It also closes a trap the deck had been walking past. The drawing is an inverter, so its input
*falls* to turn the pull-up on — but the law has v rise as u rises. Normalising each stage in
the direction that turns it on is what makes a chain of inverters read as non-inverting, and
that was never stated.

Writing it turned up a fourth deviation from the book, now declared on slide 16 and in the
recipe: the book puts the saturation/triode boundary at `|V_DS| = |V_GS| − |V_th|`, which in
our variables is `1 − v = u − vt` and therefore **moves as the input moves**. Ours is the
constant `x_lin`. On a full transition the input sits at its rail for most of the travel and
the two agree; on a truncated pulse, which is the case the method exists for, it never gets
there.

## Bench and sources

Main bench, 50 Ω ‖ 2 pF, at each buffer's cascade-folder C_comp (ex2 1.7 pF, inv_chain
0.6 pF). Five stress levels per buffer, 50–90 % of the settled swing. Probed gates from
`predriver_stages_2026-09-09`; replays and the shipped model from
`gate_cascade_prototype_2026-09-09`; candidate builds from `stage_count_from_file_2026-09-21`;
native HSPICE IBIS and the transistor from the 08-20 stress matrix.

**inv_chain caveat, carried from the 09-18 deck.** Its IBIS file declares Vinh 2.0 V on a 1.8 V
part, so our input comparator fires late and trims ~29 ps off every pulse. That flatters the
gate-state model on slide 5. It is a defect, not a result; the backup slide says so.

## Known gaps, stated on the slides

The coverage slide gives them to the audience rather than leaving them to be asked: short HIGH
pulses only, 50–90 % of the travel, single pulses rather than trains, and a shape grid chosen
by looking at results on these same twelve buffers. `docs/track1_recipe.md` carries the full
procedure and numbers; `docs/track1_explainer.template.html` is the same argument as a web page,
kept in step by `scripts/check_recipe_agreement.py`.

**Still to reconcile:** the doc and the web page keep the older method-first ordering, while
this deck is evidence-first. They should be restructured to match.
