# full_swing_fixtures_2026-09-09

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 12M, 222 files, written 2026-06-04 to 2026-09-18
- location before archiving: `results/full_swing_fixtures_2026-09-09`

## Contents (top level)

```
ex2/                                               110K  18 files
ex2_base/                                          110K  18 files
ex2_nomiller/                                      110K  18 files
ex2_skewp/                                         110K  18 files
ex2_slowpre/                                       110K  18 files
ex2_weak/                                          110K  18 files
inv_base8/                                         2.3M  24 files
inv_chain/                                         2.3M  18 files
inv_skewp/                                         2.3M  24 files
inv_stage4/                                        2.3M  24 files
inv_weak/                                          2.3M  24 files
```

## Produced by

`scripts/silicon_map_replay.py`:

> Real gate in, and the Ku/Kd maps taken from the transistor instead of the IBIS tables.
> 
> `gate_replay_prototype.py` feeds the model the transistor's real gate and keeps
> the maps the shipped model implies: Ku(g) is "the IBIS Ku(t) at the moment the
> real full-swing gate passed g". On inv_chain that under-drives the stressed pad
> by up to 54 %, although Ku is a single-valued function of the gate within every
> stressed event (loop <= 0.1). So either the map's shape is wrong, or the output
> stage is not a static map. This decides it.
> 
> The map is now the transistor's own two-fixture Ku(t)/Kd(t) plotted against its
> own gate, either
> 
>     --source full     at full swing (two new fixture runs, rise 5 ns, fall 15 ns)
>     --source stress   inside the middle stressed event (the matrix fixture runs)
> 
> and the stressed widths are replayed as before. If the silicon map reproduces
> the stressed pad, the output stage IS a static map of the gate and the IBIS
> tables place Ku wrongly against the gate for a fast gate. The map values are
> printed side by side so the difference can be read directly.
> 
>     py -3.14 scripts/silicon_map_replay.py --variant inv_chain --ccomp 0.6 --source full
> 

`scripts/variant_silicon_maps.py`:

> Track 2 on the nine variants: measured Ku/Kd maps (two full-swing fixture runs of the
> variant's transistor plus its last-stage gate node), then the file chain + measured map +
> one pad point, scored on the variant's stressed matrix like `gate_chain_prototype.py`.
> 
> Per variant this script makes three HSPICE runs from the variant's own full-swing deck
> (results/variant_stress_cases_2026-09-04/<v>/full_swing/run.sp, 1 ps input edges like its
> stress cases):
> 
>     full_swing_fixtures_2026-09-09/<v>/vfix_0     pad through 50 Ohm to 0 V
>     full_swing_fixtures_2026-09-09/<v>/vfix_vcc   pad through 50 Ohm to VCC
>     predriver_stages_2026-09-09/<v>/full          50 Ohm || 2 pF, gate node probed
> 
> and then calls gate_chain_prototype.main() with --maps silicon --calib-pad 50, after
> registering the variant's gate node and fixture directory in the modules that need them.
> 
>     py -3.14 scripts/variant_silicon_maps.py [--only ex2_base inv_stage4 ...] [--maps-only]
> 

