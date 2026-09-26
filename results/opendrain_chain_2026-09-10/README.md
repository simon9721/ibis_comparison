# opendrain_chain_2026-09-10

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 1.2G, 1456 files, written 2026-09-10 to 2026-09-10
- location before archiving: `results/opendrain_chain_2026-09-10`

## Contents (top level)

```
base_K3_calib680.log                               4.0K
base_c1.75_calib680/                                90M  101 files
base_c1.75_calib680.log                            4.0K
base_c3_calib680/                                   89M  101 files
base_c3_calib680.log                               4.0K
base_c3_calib680_K3/                                33M  35 files
base_c3_calib680_K3v/                               85M  96 files
base_c3_calib680_odprior/                           84M  96 files
base_c3_calib680_odprior_K3/                        84M  96 files
base_c3_kd_K3_calib680.log                            0
base_c3_kd_K3v_calib680.log                        4.0K
base_c3_kd_calib680.log                            4.0K
base_c3_odprior_K3_calib680.log                    4.0K
base_c3_odprior_calib680.log                       4.0K
base_calib680/                                      82M  100 files
base_calib680.log                                  4.0K
base_calib680_K3/                                   68M  100 files
base_calib680_K3v/                                  64M  95 files
base_kd_K3_calib680.log                            4.0K
base_kd_K3v_calib680.log                           4.0K
base_kd_calib680.log                               4.0K
fullswing_maps_pp_vs_od.png                        120K
od_slowpre_c3_calib800_odprior_K3/                  83M  96 files
od_slowpre_c3_odprior_K3_calib800.log              4.0K
od_slowpre_calib800/                                87M  100 files
od_slowpre_calib800.log                            4.0K
od_slowpre_calib800_K3/                             27M  25 files
od_slowpre_calib800_K3v/                            83M  95 files
od_slowpre_kd_K3_calib800.log                         0
od_slowpre_kd_K3v_calib800.log                     4.0K
od_slowpre_kd_calib800.log                         4.0K
od_weak_c3_calib680_odprior_K3/                     73M  96 files
od_weak_c3_odprior_K3_calib680.log                 4.0K
od_weak_calib680/                                   77M  100 files
od_weak_calib680.log                               4.0K
od_weak_calib680_K3/                                11M  6 files
od_weak_calib680_K3v/                               74M  95 files
od_weak_kd_K3_calib680.log                            0
od_weak_kd_K3v_calib680.log                        4.0K
od_weak_kd_calib680.log                            4.0K
```

## Produced by

`scripts/build_od_slide_figures.py`:

> Open-drain slides: full swing and stressed cases, transistor vs native vs our builds,
> pad and Kd on the same axes. Drawn from existing runs:
> 
>     transistor, native   results/opendrain_gatestate_2026-09-10/base/w*/{transistor,native}
>     ours, legacy build   results/opendrain_stress_2026-09-08/w*/ours          (before 2026-09-10)
>     ours, gate-state     results/opendrain_gatestate_2026-09-10/base/w*/ours  (converter now)
>     ours, chain          results/opendrain_chain_2026-09-10/base_c3_calib680_odprior/w*  (recipe)
> 
>     py -3.14 scripts/build_od_slide_figures.py
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

`scripts/opendrain_summary_figure.py`:

> Open-drain, three buffers, four builds: the low-excursion error against depth.
> 
>     py -3.14 scripts/opendrain_summary_figure.py
> 

First lines of `base_c1.75_calib680.log`:

```
  base: prior3 vt=0.52 alpha=1.1 gs=0.91; chain fit in the (mirrored) Ku domain:
      K=2: Ku-domain rms 0.0102  s_up 2.36 s_dn 1.37 vt 0.70 x_lin 0.45
      K=3: Ku-domain rms 0.0111  s_up 2.69 s_dn 1.67 vt 0.23 x_lin 0.45
      K=4: Ku-domain rms 0.0142  s_up 3.30 s_dn 2.34 vt 0.00 x_lin 0.45
  -> K = 2: s_up 2.356 s_dn 1.365 vt 0.700 x_lin 0.450 (full-swing rms 0.0102)
    calibration at W = 680 ps: excursion error -94.1 % with vt 0.700; vt 0 -> -94.4 %, vt 0.7 -> -94.0 %
    -> drive scale 1.994

```

First lines of `base_c3_calib680.log`:

```
  base: prior3 vt=0.52 alpha=1.1 gs=0.91; chain fit in the (mirrored) Ku domain:
      K=2: Ku-domain rms 0.0102  s_up 2.45 s_dn 1.46 vt 0.70 x_lin 0.45
      K=3: Ku-domain rms 0.0100  s_up 2.80 s_dn 1.79 vt 0.23 x_lin 0.45
      K=4: Ku-domain rms 0.0105  s_up 3.43 s_dn 2.48 vt 0.00 x_lin 0.45
  -> K = 2: s_up 2.447 s_dn 1.458 vt 0.700 x_lin 0.450 (full-swing rms 0.0102)
    calibration at W = 680 ps: excursion error -91.7 % with vt 0.700; vt 0 -> -92.1 %, vt 0.7 -> -91.7 %
    -> drive scale 1.936

```

