# native_st_vs_solved_2026-09-07

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 228K, 1 files, written 2026-09-07 to 2026-09-07
- location before archiving: `results/native_st_vs_solved_2026-09-07`

## Contents (top level)

```
native_st_vs_solved.png                            228K
```

## Produced by

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

`scripts/native_reversal_entry.py`:

> What does native do with its falling trajectory when the pulse is truncated?
> 
> `native_st_vs_solved_2026-09-07` settled that native's stored Ku(t)/Kd(t) is the
> offline two-fixture solve, same shape to 0.4% of span. So native holds exactly one
> falling trajectory, recorded from a **fully on** pull-up, indexed by time since
> the edge -- the same thing we hold.
> 
> And the documented state mechanism (bracket V(out) between waveforms with
> different initial voltages) is dormant here: io_buf's .ibs carries exactly one
> pair per edge.
> 
> So native ought to have our defect. It does not -- its Ku sits +15 ps from the
> transistor under stress where ours sits +80. This asks what it actually does with
> the curve, by overlaying native's stressed Ku against its own full-swing falling
> Ku, aligned at the reversal:
> 
> * **replays from the start** -> stressed Ku jumps to the full curve's 1.0 and
>   follows it, and native has no state mechanism at all;
> * **enters partway** -> stressed Ku picks the full curve up at the value it had
>   reached, which is the entry condition working through some other route;
> * **scales** -> stressed Ku is the full curve multiplied down.
> 
>     py -3.14 scripts/native_reversal_entry.py
> 

`scripts/native_st_vs_solved_k.py`:

> Is native's St_pu(t) the same curve as the offline two-fixture solve?
> 
> This is the question `native_vs_solved_ku.py` posed and never answered. It
> separates the two remaining explanations for why native's Ku sits +15 ps from the
> transistor under stress while ours sits +80:
> 
> * if native's St_pu(t) **equals** the offline solve on a clean full swing, then
>   the stored trajectory is identical and every difference under stress is in how
>   each model is *entered and driven*;
> * if they **differ even at full swing**, the difference is in the solve or in the
>   replay itself, and the stress case is a red herring.
> 
> `solve_k_params_output` returns [time, k_u, k_d] with **time in seconds** while
> every waveform in this study is in ns -- the unit trap that produced a saturated
> square wave the first time this solve was used.
> 
> The B-element run already exists (results/archive/2026-09/native_vs_solved_ku_2026-09-04), driven
> at full swing into the same 50 ohm + 2 pF bench with `xv_pu=ku` / `xv_pd=kd`
> exposing St_pu and St_pd as nodes.
> 
>     py -3.14 scripts/native_st_vs_solved_k.py
> 

