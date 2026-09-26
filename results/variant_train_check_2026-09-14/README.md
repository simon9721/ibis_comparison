# variant_train_check_2026-09-14

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 76M, 360 files, written 2026-06-04 to 2026-09-17
- location before archiving: `results/variant_train_check_2026-09-14`

## Contents (top level)

```
ex2_base/                                          9.1M  34 files
ex2_nomiller/                                      8.6M  34 files
ex2_skewp/                                          11M  44 files
ex2_slowpre/                                       9.7M  34 files
ex2_weak/                                           11M  44 files
inv_base8/                                         6.7M  42 files
inv_skewp/                                         6.8M  42 files
inv_stage4/                                        6.7M  42 files
inv_weak/                                          5.9M  42 files
summary.csv                                        4.0K
variant_trains.png                                 792K
```

`summary.csv` columns: `variant,width_ns,build,pulse1_pct,settled_pct,(repeated per build)` (4 rows)

## Produced by

`scripts/variant_train_check.py`:

> Validation: the nine variants on a stressed pulse train (8 pulses, 50 % duty, at each
> variant's 50 %-depth width, 1 ps input edges like their stress cases).
> 
> Transistor: the variant's depth50 transistor deck with the train PWL substituted.
> Models: track 1 (file chain + prior map + pad point) and track 2 (+ measured map), the
> builds already made by gate_chain_prototype.py / variant_silicon_maps.py.
> Scoring as in track2_train_check.py (windows shifted by the transistor's own delay).
> 
>     py -3.14 scripts/variant_train_check.py [--only ex2_base ...]
> 

