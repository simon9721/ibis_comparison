# pu_off_conflict_2026-09-07

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 109M, 161 files, written 2026-09-07 to 2026-09-09
- location before archiving: `results/pu_off_conflict_2026-09-07`

## Contents (top level)

```
pu_off_conflict.png                                128K
s0.10/                                              11M  16 files
s0.20/                                              11M  16 files
s0.25/                                              11M  16 files
s0.29/                                              11M  16 files
s0.40/                                              11M  16 files
s0.50/                                              11M  16 files
s0.60/                                              11M  16 files
s0.70/                                              11M  16 files
s0.85/                                              11M  16 files
s1.00/                                              11M  16 files
```

## Produced by

`scripts/build_0917_deck.py`:

> Build the 2026-09-17 deck: inside the buffer, what it taught us, and the open question.
> 
> This deck deliberately stops before the solution. It shows the internal-stage study on
> three buffers, what was learned, the verification that driving Ku/Kd from the transistor's
> own gate node works, why the shipped model's gate is not that node, the question that
> leaves, and the experiments that did not answer it. Track 1, track 2 and the four-number fit
> are not on these slides.
> 
> Style follows the 0904 and 0911 decks:
> 
> * Simulation figures only; a number is listed, not charted. One relaxation, agreed for this
>   deck: one slide of schematic, drawn as native shapes, for the stage structure.
> * Two or three lines state the point; the rest of the slide is the waveform.
> * The wrong turns stay on the slides with their corrections.
> 
> One layout rule learned on this deck's first render: the 0904 script placed every figure at
> a fixed y under a fixed 0.75 in per bullet, and any bullet that wrapped put the figure
> straight through the text. Here `points()` returns the y it actually used and figures are
> placed from that.
> 
>     py -3.14 scripts/build_0917_deck_figures.py     # first
>     py -3.14 scripts/build_0917_deck.py
>     powershell -ExecutionPolicy Bypass -File scripts/render_deck_slides.ps1 `
>         -Deck results/meeting_deck_2026-09-17/inside_the_buffer_2026-09-17.pptx
> 

`scripts/build_review_package.py`:

> Assemble the 2026-09-08/09 findings into one reviewable package.
> 
> One folder per claim under results/review_2026-09-09/, each with the figure,
> the CSV it was computed from, the FINDINGS.md and the script that produced it.
> Two figures that did not exist yet are built here: the three-open-drain Kd law,
> and the ex2 C_comp correction (the negative result).
> 
>     py -3.14 scripts/build_review_package.py
> 

`scripts/full_swing_silicon_kukd.py`:

> Solve the transistor's Ku/Kd at full swing -- the reference that never existed.
> 
> Two open items in `pu_off_scale_2026-09-07` both close on this one run:
> 
> * every full-swing comparison there leans on native, because the stress matrix
>   carries `silicon_ku`/`silicon_kd` for stressed cases only;
> * the reversal overshoot is an objective the sweep trades against, and nobody has
>   checked whether the **transistor's own coefficient** overshoots at the start of
>   a fall. If it does not, "preserve the overshoot" is the wrong objective and the
>   `pu_off` conflict may dissolve rather than needing an architectural fix.
> 
> Two HSPICE runs of the transistor into the IBIS fixtures (50 ohm to 0 V and to
> VCC) on the canonical `long_control` case -- rise at 5 ns, fall at 15 ns, the same
> stimulus as `defect_b_full_swing_2026-09-03`.
> 
> Solved at five grids, because `silicon_kukd_conditioning_2026-09-07` showed the
> excursion near a reversal is set by the `C_comp dV/dt` finite difference and does
> not converge. Any claim made here has to survive that check or be dropped.
> 
>     py -3.14 scripts/full_swing_silicon_kukd.py
> 

`scripts/pu_off_conflict_sweep.py`:

> Is `pu_off` genuinely undecidable, or was three points just too few?
> 
> `pu_off_scale_2026-09-07` claimed the parameter cannot be derived because it sets
> two things at once -- when the gate decays, and the phase between the gate and the
> residual spike -- and they want opposite values. That was argued from three
> points (0.70 / 0.29 / 0.25) plus a mechanism read off the netlist. Three points
> cannot rule out an interior optimum that satisfies both.
> 
> This sweeps it properly. Two objectives, each measured against its own reference:
> 
> * **coefficient**  Ku rms against the transistor over +90..+400 ps from the
>   reversal, three widths. That window is grid-converged (spread 0.0012 against
>   0.0304 nearer the reversal, `silicon_kukd_conditioning_2026-09-07`), so the
>   reference is sound there.
> * **amplitude**    the full-swing reversal overshoot above the trace's own
>   settled plateau. The transistor's is +64.9 mV, native's +83.8.
> 
> If both objectives are monotone in `pu_off` and pull in opposite directions,
> there is no value that satisfies both and the claim stands. If either turns over,
> it falls.
> 
>     py -3.14 scripts/pu_off_conflict_sweep.py
> 

