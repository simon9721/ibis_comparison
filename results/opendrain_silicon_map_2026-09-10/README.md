# opendrain_silicon_map_2026-09-10

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 2.0M, 12 files, written 2026-09-10 to 2026-09-10
- location before archiving: `results/opendrain_silicon_map_2026-09-10`

## Contents (top level)

```
base_c3.ibs                                        288K
base_c3_prior3.txt                                 1.0K
base_c3_silicon_kd_map.png                         196K
base_c5.ibs                                        288K
base_c5_prior3.txt                                 1.0K
base_c5_silicon_kd_map.png                         232K
od_slowpre_c3.ibs                                  288K
od_slowpre_c3_prior3.txt                           1.0K
od_slowpre_c3_silicon_kd_map.png                   188K
od_weak_c3.ibs                                     288K
od_weak_c3_prior3.txt                              1.0K
od_weak_c3_silicon_kd_map.png                      220K
```

## Produced by

`scripts/opendrain_silicon_map.py`:

> Open-drain: the transistor's own Kd against its own gate, and the prior that fits it.
> 
> The chain recipe on the open-drain ex2 (`opendrain_chain_build.py`) reproduced
> the calibration point but not the depth law: the pad's cliff between 620 and
> 750 ps is much sharper on the transistor than on any chain. The gate-state
> bench already recorded n4 and Kd at the pad minimum for every width, and those
> pairs say the NMOS turns on far below the ex2 pull-up prior's threshold of
> 0.52. This measures the map properly: single-fixture Kd(t) solved from the
> bench run (C_comp as given) against the normalised n4, full swing and every
> stressed width on one axis, and a three-parameter prior fitted to it.
> 
>     py -3.14 scripts/opendrain_silicon_map.py --variant base --ccomp 3.0
> 

