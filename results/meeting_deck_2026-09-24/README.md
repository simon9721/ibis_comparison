# Meeting deck — 24 September 2026

`0924_track1_story.pptx`, 18 slides. Built by `scripts/build_0924_deck.py`; figures by
`scripts/build_0924_deck_figures.py`. Rendered to `slides/` with
`scripts/render_deck_slides.ps1`. Style and layout are taken from Simon's 09-18 deck; none of
his slides are carried over.

## Why this deck exists

Every earlier telling of track 1 started from the method and worked back to the evidence. This
one runs in the order the work actually went, which is the order Simon asked for:

| slides | step |
|---|---|
| 2 | we can probe our own test chips — the node that matters is the output stage's gate |
| 3 | **measure the map**: pair Ku(t) from the file with the probed gate at each instant |
| 4–6 | **show it works**: that map, driven by the real gate, tracks the transistor at every stress level, where native IBIS and our gate-state model do not |
| 7–8 | **show why ours fails**: the real gate changes shape as the pulse shortens, GUP keeps one shape, and that difference is the whole error |
| 9 | **only now the motivation**: reproduce the gate's shape from what is in the file |
| 10 | what the file gives, and the specific way it is blind: a full transition visits only the two ends of the gate's travel |
| 11 | one stressed pulse reaches the interior – the five widths stop the gate at 0.76 / 0.80 / 0.84 / 0.88 / 0.94, so the stress sweep is a sampling grid |
| 12 | what shape the gate may be: every stage under-reaches a linear filter, and the gap compounds to 0.50 against 1.00 at the pad |
| 13 | the physics, and the four numbers it forces – drawn, not listed |
| 14 | what we build, with the stage law written out |
| 15 | where every number comes from, and why the peak cannot be used to choose |
| 16 | where the recipe stands: 12 of 12 within ±10 %, and what it costs |
| 17 | what it does not cover yet |
| 18 | backup: inv_chain's input threshold |

## The correction that changed slides 4–6

The first build of those slides used `gate_replay` — the real gate through the **IBIS-implied**
map. On ex2 that is fine (−3 … −6 %). On inv_chain it collapses: **−14 % at 135 ps to −69 % at
104 ps**, which would have contradicted the slide's own title.

The build that works is `gate_replay_silicon_full`: the real gate through the **map measured at
full swing**. ex2 +1.2 / +1.1 / +1.0 / −1.3 / −4.7 %, inv_chain +2.0 / +2.8 / +4.6 / +7.0 /
+9.4 %, deepest stress last. So **both ingredients matter** — the gate's shape and the map — and
on inv_chain the IBIS-implied map is not good enough on its own. Slides 4–6 use the measured-map
build and the speaker notes record the difference.

## Bench and sources

Main bench, 50 Ω ∥ 2 pF, at each buffer's cascade-folder C_comp (ex2 1.7 pF, inv_chain 0.6 pF).
Five stress levels per buffer, 50–90 % of the settled swing. Nothing is re-simulated: probed
gates from `predriver_stages_2026-09-09`, replays and the shipped model from
`gate_cascade_prototype_2026-09-09`, native HSPICE IBIS and the transistor from the 08-20 stress
matrix (`delay_cmd/waveforms`).

**inv_chain caveat, carried from the 09-18 deck.** Its IBIS file declares Vinh 2.0 V on a 1.8 V
part, so our input comparator fires late and trims ~29 ps off every pulse. That flatters the
gate-state model on slide 5 (−2 % at 70 % stress against native's +32 %). It is a defect, not a
result; slide 18 says so.

## The method half

Written to the same rule as the first half: one question per slide, and nothing before the thing
that motivates it. Three figures are new.

`sampling_grid` puts the five probed gates on one axis with the full transition behind them, so
"each width stops the clock at a different point of the same path" is something you can see
rather than a claim. `stage_nonlinear` is the evidence for the stage law: every probed stage
against what a linear filter would give at the deepest pulse, with the gap compounding down the
chain — 1.03 against 1.04 at the first stage, 0.50 against 1.00 at the pad. The superposition
itself comes from `predriver_stage_probe`, which owns it. `stage_law` draws the four numbers as
geometry rather than listing them, because a threshold, a slope and a taper are easier seen.

## Known gaps, stated on the slides

Slide 17 gives them to the audience rather than leaving them to be asked: short HIGH pulses
only, 50–90 % of the travel, single pulses rather than trains, and a shape grid that was
chosen by looking at results on these same twelve buffers. `docs/track1_recipe.md` carries the
full procedure and the numbers; `docs/track1_explainer.template.html` is the same argument as a
web page, kept in step by `scripts/check_recipe_agreement.py`.
