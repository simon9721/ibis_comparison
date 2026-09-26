# variant_gate_probe_2026-09-10

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 9.7M, 192 files, written 2026-06-04 to 2026-09-10
- location before archiving: `results/variant_gate_probe_2026-09-10`

## Contents (top level)

```
ccomp_loop.json                                    4.0K
ex2_base/                                          114K  18 files
ex2_nomiller/                                      114K  18 files
ex2_skewp/                                         114K  18 files
ex2_slowpre/                                       114K  18 files
ex2_weak/                                          114K  18 files
gate_max.json                                      4.0K
inv_base8/                                         2.4M  26 files
inv_skewp/                                         2.3M  24 files
inv_stage4/                                        2.4M  26 files
inv_weak/                                          2.3M  24 files
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

`scripts/variant_ccomp_loop.py`:

> C_comp per variant by the Ku-vs-gate loop method, now that every variant has a probed gate.
> 
> Same measurement as `ku_gate_hysteresis_ccomp.py` on the base buffers: the
> two-fixture Ku plotted against the real gate opens a loop when the C_comp used
> in the solve is wrong; the loop-minimising value is the device's C_comp. Uses
> the variant's deepest stressed case (fixture_0 / fixture_vcc from the stress
> cases, the gate from `variant_gate_probe.py`).
> 
>     py -3.14 scripts/variant_ccomp_loop.py
> 

`scripts/variant_gate_probe.py`:

> The one-point calibration run for every variant: probe the output gate.
> 
> Re-runs each variant's full-swing transistor deck and its deepest stressed deck
> with the last predriver node probed (ex2 family: n4; inv family: the highest
> internal VOUTn), normalises the gate to 0 = rest / 1 = full-swing high, and
> records the gate maximum at that width. That number is the `--calib W GMAX`
> input of the chain prototype. Writes results/variant_gate_probe_2026-09-10/gate_max.json.
> 
>     py -3.14 scripts/variant_gate_probe.py --variants ex2_base ex2_weak ...
> 

`scripts/variant_silicon_map.py`:

> A variant's own Ku-vs-gate map from its stressed fixture runs and the probed gate.
> 
> The variant stress cases carry two-fixture transistor runs per depth
> (fixture_0 / fixture_vcc); `variant_gate_probe.py` added the gate node at the
> deepest depth. Solve Ku/Kd there, plot against the normalised gate, fit the
> three-parameter prior. Answers "is inv_stage4's map the family map?".
> 
>     py -3.14 scripts/variant_silicon_map.py --variant inv_stage4 --ccomp 0.6
> 

