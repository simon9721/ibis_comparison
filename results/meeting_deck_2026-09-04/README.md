# Meeting deck — 4 September 2026

`ibis_pybis_status_2026-09-04.pptx`, built by
`scripts/build_0902_meeting_deck.py` from the deliverables in `0902_plan.md`.

15 slides, 7 figures. **Every figure is a real result file** copied straight from
its results directory — nothing redrawn or schematised for the slide:

| slide | figure |
|---|---|
| clean edge | `defect_b_full_swing_2026-09-03/` |
| the offset | `settled_offset_diagnosis_2026-08-27/03_offset_chain.png` |
| delay_cmd | `settled_offset_diagnosis_2026-08-27/04_offset_fix.png` |
| shift vs depth | `timing_shift_decomposition_2026-09-03/` |
| golden waveforms | `golden_waveform_test_2026-09-03/` |
| C_comp | `pybis_ccomp_converged_2026-09-03/` |
| new buffers | `variant_stress_cases_2026-09-04/inv_base8/depth50_w102ps/kukd.png` |

Rebuild after new results with `py -3.14 scripts/build_0902_meeting_deck.py`.

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
