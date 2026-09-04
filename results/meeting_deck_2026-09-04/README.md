# Meeting deck — 4 September 2026

`ibis_pybis_status_2026-09-04.pptx`, built by
`scripts/build_0902_meeting_deck.py` from the deliverables in `0902_plan.md`.

16 slides, 6 figures. Every figure is **real measured data**, redrawn at slide
size by `scripts/build_deck_figures.py` — no schematics, nothing invented.

## Readability

The print figures in `results/` are 11–13 in wide and up to 13 in tall with ~10 pt
labels. Dropped into a slide box they shrink with the box: measured on the first
draft, every figure's axis text landed at **3.9–5.6 pt**. Present, unreadable.

Enlarging the box cannot fix a figure taller than the slide, so the deck figures
are redrawn at 12.2 x 5.2 in with 15–19 pt fonts. Placed at a 12.2 in box the
scale is 1.0 and the text is the size it says. The five-panel offset chain is cut
to the two panels that carry the argument rather than shrunk into illegibility.

Audited after building: nothing below 13 pt except the template's own section
eyebrow, no shape off the canvas, no content in the takeaway band.

Rebuild figures first if results change, then the deck:

```
py -3.14 scripts/build_deck_figures.py
py -3.14 scripts/build_0902_meeting_deck.py
```

Figure sources:

| slide | figure |
|---|---|
| clean edge | `defect_b_full_swing_2026-09-03/` |
| the offset | `settled_offset_diagnosis_2026-08-27/03_offset_chain.png` |
| delay_cmd | `settled_offset_diagnosis_2026-08-27/04_offset_fix.png` |
| shift vs depth | `timing_shift_decomposition_2026-09-03/` |
| golden waveforms | `golden_waveform_test_2026-09-03/` |
| C_comp | `pybis_ccomp_converged_2026-09-03/` |
| new buffers | `variant_stress_cases_2026-09-04/inv_base8/depth50_w102ps/kukd.png` |

## Two deliberate choices

**The wrong turns are on the slides, not omitted.** The C_comp double-counting
claim that the golden-waveform test overturned, and the Miller-feedthrough
hypothesis that `nomiller` disproved, both appear with the correction. A reviewer
who finds a reversal afterwards trusts everything else less.

**One question is answered differently from the plan.** `0902_plan.md` lists
"does delay_cmd fix the timing too?" as the highest-value open item. It has since
been measured: delay_cmd improved timing on **0 of 19** stress cases, so the
offset and the timing shift are two mechanisms, not one. The slide reports that
rather than the question.

## Not yet in the deck

The nine-variant stress run is still in progress. Its finished result — the
timing shift growing under truncation on 9 of 9 variants, and the native
two-waveform failure on ex2 — belongs on slides 8 and 14 once complete.
