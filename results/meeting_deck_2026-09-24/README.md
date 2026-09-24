# Meeting deck — 24 September 2026

`0924_track1_story.pptx`, 12 slides. Built by `scripts/build_0924_deck.py`; figures by
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
| 10–11 | the method, and what it does not yet cover |
| 12 | backup: inv_chain's input threshold |

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
result; slide 12 says so.

## What still needs a pass

Slides 10–11 are deliberately thin. Simon's feedback on the earlier web version was that the
method needs a proper walkthrough — the stage law written out, where each parameter's value
comes from, and why that law rather than an RC — and that a circuit diagram plus a ramp figure
does not do it. That is the next piece of work. `docs/track1_recipe.md` carries the full
procedure and the numbers meanwhile, and `docs/track1_explainer.template.html` is the visual
version of the same argument.
