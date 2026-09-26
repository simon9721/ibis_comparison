# opendrain_stress_od_slowpre_2026-09-08

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 47M, 282 files, written 2026-07-28 to 2026-09-08
- location before archiving: `results/opendrain_stress_od_slowpre_2026-09-08`

## Contents (top level)

```
cases.csv                                          4.0K
opendrain_stress.png                               516K
w10000ps/                                          2.6M  20 files
w1000ps/                                           3.4M  20 files
w620ps/                                            3.4M  20 files
w640ps/                                            3.4M  20 files
w660ps/                                            3.4M  20 files
w680ps/                                            3.4M  20 files
w700ps/                                            3.4M  20 files
w720ps/                                            3.4M  20 files
w750ps/                                            3.4M  20 files
w770ps/                                            3.4M  20 files
w800ps/                                            3.4M  20 files
w840ps/                                            3.4M  20 files
w880ps/                                            3.4M  20 files
w940ps/                                            3.4M  20 files
```

`cases.csv` columns: `width_ns,depth_pct,si_low_V,t_min_after_rev_ps,nat_low_err_mV,our_low_err_mV,nat_lag_ps,nat_res,our_lag_ps,our_res,si_kd_at_min,nat_kd_at_min,our_kd_at_min,n4_at_min,n4_excursion` (8 rows)

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

`scripts/opendrain_chain_build.py`:

> Open-drain: the current-limited-chain recipe on the pull-down gate.
> 
> The converter now builds the gate-state model for `Model_type Open_drain`
> (`subcircuit.open_drain_tables_as_push_pull`): one predriver, one device, the
> pull-down gate GDN with its Kd map. That build rests in the right state and
> tracks depth partly, but like every gate-state build it drives the gate from a
> delay plus an RC, so under a short LOW pulse the pull-down is still far more
> "on" than the transistor's (`opendrain_gatestate_2026-09-10`).
> 
> This applies the push-pull recipe of `build_chain_model.py` to the open-drain:
> 
>     1. the converter's open-drain gate-state model
>     2. its full-swing gate-part Kd(t)
>     3. K identical current-limited stages fitted so that Kd = PRIOR(1 - chain)
>        reproduces it (Kd domain: a Ku-domain fit through the mirrored placeholder
>        leaves the pull-down onset unconstrained and lands 250 ps early). The
>        prior is the NMOS map measured in `opendrain_silicon_map.py` (threshold
>        ~0.2 of the gate swing, not the pull-up's 0.52); K on the 5 % plateau or
>        --K; x_lin 0.45; C_comp from the loop (3.0 pF), not the declared 5.0
>     4. one stressed transistor PAD run on the open-drain bench (50 ohm to VCC,
>        2 pF, short LOW pulse): bisect the stage threshold until the model's low
>        excursion matches, else scale the drive
>     5. score every width of the open-drain matrix against the transistor and
>        native, next to the legacy build and the plain gate-state build
> 
>     py -3.14 scripts/opendrain_chain_build.py --variant base --ccomp 3.0 --prior3 0.20 1.30 0.88 --calib-width 0.68 --tag _odprior
>     py -3.14 scripts/opendrain_chain_build.py --variant od_weak --ccomp 3.0 --prior3 0.23 1.15 0.92 --K 3 --calib-width 0.68 --tag _odprior_K3
> 

