# s2ibispy_parameter_selection_ex2_od_slowpre_2026-09-02

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 28M, 900 files, written 2026-09-08 to 2026-09-08
- location before archiving: `results/s2ibispy_parameter_selection_ex2_od_slowpre_2026-09-02`

## Contents (top level)

```
decision.json                                      4.0K
probe/                                             4.7M  114 files
selection.csv                                      4.0K
tr100ps/                                           3.4M  114 files
tr10ps/                                            3.4M  114 files
tr1ps/                                             2.9M  107 files
tr200ps/                                           2.9M  107 files
tr20ps/                                            3.4M  114 files
tr50ps/                                            3.4M  114 files
tr5ps/                                             3.4M  114 files
```

## Produced by

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

