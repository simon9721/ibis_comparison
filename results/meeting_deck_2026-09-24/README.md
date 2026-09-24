# Meeting deck — 24 September 2026

`0924_track1_story.pptx`, 23 slides. Built by `scripts/build_0924_deck.py`; figures by
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
| 10 | what the file gives, and the specific way it is blind: Ku(t) fixes the composition, not the split |
| 11 | one stressed pulse reaches the gate – the five widths stop it at 0.76 / 0.80 / 0.84 / 0.88 / 0.94, so the stress sweep is a sampling grid |
| 12 | what shape the gate may be: every stage under-reaches a linear filter, and the gap compounds to 0.50 against 1.00 at the pad |
| 13 | the physics, and the four numbers it forces – drawn, not listed |
| 14 | **the model we build** |
| 15 | step 1: C_comp, rejected by the file's own Ku ≤ 1 test |
| 16 | step 2: the four numbers, fitted to the file's Ku(t), costing no measurement |
| 17 | step 3: what the file cannot choose — the fit plateaus, the stressed pulse does not |
| 18 | step 4: the stressed run's first job — bisect vt until the peak matches |
| 19 | step 5: its second job — all nine now share the peak, so the waveform picks |
| 20 | the recipe on one slide |
| 21 | where it stands: 12 of 12 within ±10 %, and what it costs |
| 22 | what it does not cover yet |
| 23 | backup: inv_chain's input threshold |

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

Seven slides, one idea each, every one with something on screen. The first version compressed
all of it into two text slides, which is not something a viewer can follow in sequence.

Four figures are new and all are drawn from candidate builds already on disk in
`stage_count_from_file_2026-09-21` — ex2's nine candidates (3 stage counts × 3 map shapes),
each with a full-swing run and five stressed ones.

`model_blocks` separates what we build from what comes out of the file untouched. `k_choice` is
the crux: on the left the fit error against the file's Ku(t) at every K, flat past K = 3 — what
the file sees; on the right the three candidates inside that band on one 810 ps pulse, three
completely different buffers. `calib_select` then shows all nine after calibration, sharing the
measured peak by construction and separating in the tail, with the picked one on the transistor.
Its rms numbers are computed when the figure builds: 59 mV for the pick against 84, 140 and
worse — on this buffer the rule picks the best of the nine outright.

Two numbers on slide 18 come from the build log rather than a figure: the file-fitted threshold
vt = 0.700 leaves ex2's 810 ps pad **97 % low**, and the bisection moves it to 0.632.

### A figure that had to be rebuilt

`k_choice` first drew the nine built models' full-swing Ku(t) captioned "indistinguishable".
They are not — they are post-calibration, and the calibration moves vt, which moves the
timing. What the file actually sees is the fit residual before any stressed run touches the
model, so the panel now shows that instead.

## Known gaps, stated on the slides

Slide 17 gives them to the audience rather than leaving them to be asked: short HIGH pulses
only, 50–90 % of the travel, single pulses rather than trains, and a shape grid that was
chosen by looking at results on these same twelve buffers. `docs/track1_recipe.md` carries the
full procedure and the numbers; `docs/track1_explainer.template.html` is the same argument as a
web page, kept in step by `scripts/check_recipe_agreement.py`.
