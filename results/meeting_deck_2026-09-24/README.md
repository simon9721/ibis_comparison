# Meeting deck — 24 September 2026

`0924_track1_story.pptx`, 25 slides. Built by `scripts/build_0924_deck.py`; figures by
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
| 10 | 6 · Where Ku(t) comes from, and what it is |
| 11 | 7 · What Ku(t) fixes, and what it leaves open |
| 12 | 8 · One stressed pulse is the measurement that reaches the gate |
| 13 | 9 · What shape may the gate be?  Measure a stage |
| 14 | 10 · The physics behind it — a stage is a current source with a threshold |
| 15 | 11 · What each of the four numbers does |
| 16 | 12 · What we build |
| 17 | 13 · Step 1 — C_comp, rejected by the file's own arithmetic |
| 18 | 14 · Step 2 — the four numbers, fitted to the file |
| 19 | 15 · Step 3 — what the file cannot choose |
| 20 | 16 · Step 4 — the stressed run, first job: set the amplitude |
| 21 | 17 · Step 5 — the stressed run, second job: pick one |
| 22 | 18 · The recipe, end to end |
| 23 | Where the file-only recipe stands |
| 24 | What this does not cover yet |
| 25 | Backup · inv_chain's input threshold |

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
