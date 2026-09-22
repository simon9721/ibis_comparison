# ex2_s2ibispy_slow_fast_2026-07-28

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 14M, 282 files, written 2026-07-28 to 2026-07-28
- location before archiving: `results/ex2_s2ibispy_slow_fast_2026-07-28`

## Contents (top level)

```
configs/                                           8.0K  2 files
fast_5ps/                                          6.9M  140 files
slow_1ns/                                          6.9M  140 files
```

## Produced by

`scripts/archive/run_ex2_slow_fast_gate_state_comparison.py`:

> * ex2 HSPICE native IBIS
> .title ex2 native IBIS {case.case_id}
> .option post=2 probe accurate ingold=2
> .temp 27
> 
> {clean.pwl(case)}
> 
> VPU pu_ref 0 DC {SUPPLY_V}
> VPD pd_ref 0 DC 0
> VPC pc_ref 0 DC {SUPPLY_V}
> VGC gc_ref 0 DC 0
> 
> BIBIS pu_ref pd_ref pad_ibis in_dig pc_ref gc_ref
> + file='ex2.ibs'
> + model='driver'
> + buffer=2 typ=typ power=off interpol=1 ramp_rwf=2 ramp_fwf=2
> + xv_pu=ku xv_pd=kd
> 
> Rload pad_ibis 0 {LOAD_OHM}
> Cload pad_ibis 0 {LOAD_PF}p
> .probe tran V(in_dig) V(pad_ibis) V(ku) V(kd)
> .tran 0.002n {clean.fmt(case.stop_ns)}n
> .end
> 

`scripts/make_ex2_opendrain_variant.py`:

> ex2 as an open-drain buffer: the output pullup removed.
> 
> Item 2 of `0902_plan.md`. ex2 is a real layout-extracted netlist, not a
> parameterized one, so it does not admit the clean width/stage sweeps inv_chain
> did. It admits one structurally interesting change: strip the output pullup and
> make it open-drain.
> 
> That is the change worth making. Every buffer in the study so far is push-pull,
> and the gate-state model, the command layer and the pybis subcircuit were all
> built around a pullup and a pulldown. An open-drain buffer has no pullup at all
> -- the pad can only be driven low, and reaches high through an external
> termination. If the machinery has quietly assumed push-pull, this is where it
> shows.
> 
> ex2's output stage is five pullup PMOS (mx24-28) and five pulldown NMOS
> (mx15-19), both gated by the predriver node n4. Removing the five PMOS leaves
> the predriver and the pulldown untouched, so the only thing that changes is that
> the pad has lost its path to VCC. The Miller caps from n4 to out (cx3, cx5, cx8)
> are kept -- they are physical and independent of the pullup.
> 
>     py -3.14 scripts/make_ex2_opendrain_variant.py
> 

`scripts/make_ex2_variants.py`:

> ex2 variants: the inv_chain axes, applied to a real extracted buffer.
> 
> I previously claimed ex2 did not admit parameterized variants because it is a
> flat layout-extracted netlist. That was wrong. `ex2/buffer.sp` carries an explicit
> `w=` on every device, so the same axes swept on inv_chain -- drive strength,
> pull-up/pull-down balance, predriver speed -- are a matter of scaling widths.
> 
> ex2's structure, from the netlist:
> 
>     predriver      mx20-23 (pfet)  mx11-14 (nfet)   in -> n2 -> n3 -> n4
>     output stage   mx24-28 (pfet)  mx15-19 (nfet)   gated by n4, drives out
> 
> Variants, each changing one thing so a downstream difference has one candidate
> explanation:
> 
>   base      unchanged, rebuilt through this generator -- the control on the
>             generator itself, exactly as base8 was for inv_chain.
>   weak      output stage widths halved, both devices. Weaker drive, slower edge
>             into the same load, timing structure untouched.
>   skewp     output PMOS halved only. Rise slows, fall does not -- the deliberate
>             asymmetry that on inv_chain inflated max|Ku| while leaving Kd alone.
>             Worth repeating on a device with a real extracted layout.
>   slowpre   predriver widths halved. ex2 cannot lose a stage the way inv_chain
>             could, but a weaker predriver takes longer to swing n4, which moves
>             the onset delay the command layer models.
> 
> The `[open-drain]` variant lives separately in `make_ex2_opendrain_variant.py`,
> since removing the pullup outright is a structural change rather than a scaling.
> 
>     py -3.14 scripts/make_ex2_variants.py

`scripts/run_three_buffer_realistic_pulse_campaign.py`:

> Windows creation flags that keep a child simulator off the desktop.
> 
>     A campaign launches hundreds of simulator processes. Without this each one
>     can flash or park a console window, which makes a long run impossible to sit
>     beside and can steal focus. Zero elsewhere, where the flag does not exist.
> 

