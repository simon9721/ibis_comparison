# Meeting deck — 4 September 2026

`ibis_pybis_status_2026-09-04.pptx`, built by
`scripts/build_0902_meeting_deck.py` from the deliverables in `0902_plan.md`.
14 slides.

## Style

Follows the earlier `0825_Simon` deck, which reads better than this one's first
drafts:

* **Simulation figures only.** No bar charts, no scatter plots, no schematics.
  A number is explained by listing it on the slide, not by drawing it as a bar.
  An earlier draft turned the error budget, the C_comp sweep and the max|Ku| table
  into charts; they looked tidy and said less than the plain numbers.
* **Short bullets, then the picture.** Two or three lines state the point; the
  rest of the slide is the waveform.
* **Pad and coefficients side by side** for the same case, so the pad shape and
  the Ku/Kd behind it are read together.
* Bold pipe-separated figure titles (`device | pulse | quantity`), the transistor
  as a thick pale trace with native IBIS drawn over it, and the reversal marked.

## Rebuild

```
py -3.14 scripts/build_deck_figures.py
py -3.14 scripts/build_0902_meeting_deck.py
powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
    -Deck results/meeting_deck_2026-09-04/ibis_pybis_status_2026-09-04.pptx
```

The third step exports every slide to `slides/` as PNG. **Do not send the deck
without looking at it.** Geometry checks are not a substitute: python-pptx
reported no off-slide shapes and no overlaps on drafts that had a paragraph
running under a code box, centred monospace tables with broken column alignment, a
figure contradicting its own slide title, and a table rendered at 2.8 pt.

## Two deliberate choices

**The wrong turns are on the slides.** The C_comp double-counting claim the
golden-waveform test overturned, and the Miller-feedthrough hypothesis `nomiller`
disproved, both appear with their correction.

**One question is answered differently from the plan.** It lists "does delay_cmd
fix the timing too?" as the highest-value open item. It has since been measured:
0 of 19 stress cases improved, so the slide reports two mechanisms rather than an
open question.

## Not yet in the deck

The nine-variant stress run is still going. Slide 13 shows one completed case;
the finished result — the shift growing under truncation on 9 of 9, and native's
two-waveform failure on ex2 — belongs there once it lands.
