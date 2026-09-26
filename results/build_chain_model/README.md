# build_chain_model

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 80M, 61 files, written 2026-09-10 to 2026-09-10
- location before archiving: `results/build_chain_model`

## Contents (top level)

```
ex2_chain.sub                                       88K
ex2_chain_v2.sub                                    88K
input/                                              79M  57 files
inv_chain_chain.sub                                 40K
inv_chain_pad_w104.csv                              12K
```

## Produced by

`scripts/build_chain_model.py`:

> The recipe as one command: IBIS file in, current-limited-chain driver.sub out.
> 
>     1. generate the converter's model (input threshold clamped to the supply)
>     2. run it once at full swing to read its gate-part Ku(t) / Kd(t)
>     3. fit K identical current-limited stages so that PRIOR(chain) reproduces
>        that Ku(t) (K = smallest on the rms plateau, or --K)
>     4. optional one stressed observation (--calib W_PS GATE_MAX) to place the
>        drive law under a partial input
>     5. write the model: chain -> GUP, GDN = 1 - GUP, prior maps on the last stage
> 
>     py -3.14 scripts/build_chain_model.py --ibis path.ibs --supply 3.3 --family ex2 --out driver_chain.sub
>     py -3.14 scripts/build_chain_model.py --ibis path.ibs --supply 1.8 --family inv --calib 104 0.879 --out driver_chain.sub
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

`tools/pybis2spice/pybis2spice/chain_command.py`:

> Current-limited-chain command layer for the gate-state model (converter-side, pure text).
> 
> The physics (results/current_limited_stages_2026-09-10, gate_chain_prototype_2026-09-10):
> the predriver is K identical current-limited stages
> 
>     dv/dt = s_up * h(u) * r(1 - v) - s_dn * h(1 - u) * r(v)
>     h(x)  = clip((x - vt) / (1 - vt), 0, 1) ** p
>     r(x)  = min(1, x / x_lin)
> 
> driven by a mid-supply comparator on the input pin; the output gate GUP is the
> last stage, GDN = 1 - GUP (one inverter drives both halves); Ku/Kd are static
> maps of the gate with a MOSFET-shaped prior
> 
>     Ku(g) = ((g - vt_m) / (gs - vt_m)) ** alpha,   clipped to [0, 1]
> 
> This module only rewrites a generated `InputDrivenTwoStateGateDelayCommandFull`
> subcircuit text; fitting the stage numbers (from the tables' full-swing Ku(t))
> and the one-point calibration live in scripts/build_chain_model.py.
> 

