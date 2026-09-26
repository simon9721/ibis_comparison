# edge_rate_check_2026-09-17

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 219M, 249 files, written 2026-06-04 to 2026-09-17
- location before archiving: `results/edge_rate_check_2026-09-17`

## Contents (top level)

```
ex2_base/                                           90M  95 files
inv_base8/                                         129M  154 files
```

## Produced by

`scripts/edge_rate_check.py`:

> Does model accuracy depend on the input edge rate?
> 
> The three matrix buffers run at 50 ps input edges, the nine variants at 1 ps. Every comparison
> is internally consistent (both sides use that buffer's edge) and stress levels are matched by
> measured pad reach, so the pooled numbers are legitimate. What was never tested is whether the
> ACCURACY itself depends on the edge rate, because no buffer had been run at both.
> 
> This takes one existing model per family, unchanged, and runs it and its transistor at 1 ps and
> at 50 ps over the same widths. If peak error against achieved stress is the same at both edges,
> the 1 ps choice costs nothing.
> 
>     py -3.14 scripts/edge_rate_check.py
> 

