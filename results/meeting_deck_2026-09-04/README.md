# Meeting deck — 4 September 2026

`ibis_pybis_status_2026-09-04.pptx`, built by
`scripts/build_0902_meeting_deck.py` from the deliverables in `0902_plan.md`.
13 slides.

## The cmd_clean section

Slides 5-8 stay on one case: **io_buf, short high, 1792 ps**, one stimulus (a
50 ps edge rising at 5.000 ns, falling at 6.790).

Slides 6 and 7 are **last week's two pages redrawn**, from
`scripts/build_cmd_clean_slides.py`:

| last week | this week |
|---|---|
| `settled_offset_diagnosis_2026-08-27/12_gup_ku_fix_comparison.png` | `cmd_clean_gate_and_ku.png` |
| `settled_offset_diagnosis_2026-08-27/11_pad_voltage_fix_comparison.png` | `cmd_clean_pad.png` |

Same case, same panel titles, same axis labels, same colours -- **`fix_old` is
the purple that was labelled `fix` last week**, so a curve keeps the colour the
audience already associates with it. `cmd_clean` takes `#2E8B57`, the one colour
in that palette not already spoken for. Two changes: cmd_clean is drawn as a
third curve, and the pad figure is the full view only (last week's carried a tail
zoom underneath).

**The build is called `cmd_clean` on the slides. The code still calls it
`delay_cmd`** -- `InputDrivenTwoStateGateDelayCommandFull`. Anyone reading the
repo after the talk needs that mapping.

What the third curve settles, on the tail 1.0-1.7 ns after the reversal:

```
GUPCMD    original +0.036    fix_old +0.024    cmd_clean +0.000
pad       original  76.3 mV  fix_old  51.9 mV  cmd_clean   4.0 mV
          transistor 5.9 mV  native    6.2 mV
```

fix_old takes a third off the pedestal. On the GUP panel it holds +0.024 flat
until 8.7 ns and only then clears: the restore gate does not open until the
reversal + 3.0 ns, and the pad has been holding the offset since 7.5. It reached a
clean 0 late, not never -- which is the answer to "why did last week's approach
fail when it also drove the command back to 0/1".

Sources are the existing bench: the comprehensive CSVs in
`settled_offset_diagnosis_2026-08-27/` for original, fix_old and the two
references, the stress matrix for cmd_clean's pad, and one ngspice run for
cmd_clean's internal nodes. That run is checked against the matrix result it
stands in for (5.4 mV max, 1.3 mV rms) every time the script runs.

Retired figures, deleted rather than left to be reused: `command_node.png` (drawn
from a 1 ps-edge probe run, titled 2354 ps when the probe had run 1792, annotated
-0.144 where its own trace sat at -0.079) and the four `cmd_clean_[0-3]_*.png`
from a wordier first draft.

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

**One question is answered differently from the plan.** It lists "does cmd_clean
fix the timing too?" as the highest-value open item. It has since been measured:
0 of 19 stress cases improved, so the slide reports two mechanisms rather than an
open question.

## Not yet in the deck

The nine-variant stress run has finished but is not yet read. Slide 12 shows one
completed case; the finished result — the shift growing under truncation on 9 of 9, and native's
two-waveform failure on ex2 — belongs there once it lands.
