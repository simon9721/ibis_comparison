# opendrain_risefall_2026-09-11

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 22M, 72 files, written 2026-07-28 to 2026-09-17
- location before archiving: `results/opendrain_risefall_2026-09-11`

## Contents (top level)

```
chain/                                             3.0M  4 files
clamp_check/                                        88K  1 files
gatestate/                                         3.0M  4 files
gatestate_clamped_ccomp0p2/                        2.9M  4 files
gatestate_clamped_ccomp0p25/                       2.9M  4 files
gatestate_clamped_converter/                       2.9M  4 files
gatestate_clamped_diag/                            2.9M  4 files
kd_solve_diag.png                                  116K
legacy/                                            2.8M  4 files
native/                                            326K  7 files
native_ccomp0p2/                                   318K  7 files
native_ccomp0p25/                                  318K  7 files
od_risefall.png                                    192K
od_risefall_ccomp.png                              168K
od_risefall_ccomp0p25.png                          192K
transistor/                                         55K  9 files
transistor_padcap/                                  55K  9 files
```

## Produced by

`scripts/build_od_risefall_figure.py`:

> Open-drain rise-then-fall figure (neutral: no annotations), drawn from the runs in
> results/opendrain_risefall_2026-09-11 (input rests LOW, HIGH at 5 ns, LOW at 17 ns,
> 1 kOhm pull-up to VCC, 2 pF):
> 
>     transistor              HSPICE transistor bench
>     native                  HSPICE native IBIS (ramp_rwf=2)
>     gatestate_clamped_diag  our gate-state build with the I-V pwl() arguments clamped to
>                             the table range (diagnostic; the converter's own build diverges
>                             on this load, see the session notes of 2026-09-11)
> 
> The transistor Kd is solved from this bench (1 kOhm fixture, C_comp 3 pF) with the same
> two-fixture identity used everywhere else, here with one fixture only. Where the
> pull-down current at the pad voltage is small the quotient is ill-conditioned; the
> figure masks |I_pd| below a threshold instead of drawing the blow-up.
> 
>     py -3.14 scripts/build_od_risefall_figure.py [--diag]
> 

`scripts/opendrain_clamp_check.py`:

> Item 6 verification: regenerate the open-drain gate-state model with the converter (I-V
> pwl arguments now clamped to the table range) and run the 1 kOhm rise-then-fall bench that
> diverged on 2026-09-11. Also regenerates the push-pull ex2 model and diffs it against the
> shipped build to show the only change is the clamp.
> 
>     py -3.14 scripts/opendrain_clamp_check.py
> 

