# opendrain_ccomp_2026-09-17

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 1.7M, 254 files, written 2026-07-28 to 2026-09-17
- location before archiving: `results/opendrain_ccomp_2026-09-17`

## Contents (top level)

```
cv_in0.csv                                          12K
cv_in3p3.csv                                        12K
driven/                                            1.4M  216 files
in0_dc/                                             66K  9 files
in0_ramp/                                           51K  9 files
in3p3_dc/                                           66K  9 files
in3p3_ramp/                                         51K  9 files
```

## Produced by

`scripts/opendrain_driven_capacitance.py`:

> The open-drain part's pad capacitance in its DRIVEN state, by ramp-rate convergence.
> 
> The released state measured cleanly at 0.234 pF (opendrain_released_capacitance.py). The driven
> state did not, and the reason is numerical: with the pull-down on, conduction at mid-rail is
> 44 mA while the displacement current at a 2 ns ramp is only C dV/dt ~ 0.8 mA, so C is a small
> difference of large numbers.
> 
> A faster ramp raises the displacement term proportionally without changing conduction. This
> sweeps the ramp duration and looks for a value that stops moving. The RELEASED state is measured
> at every ramp rate as a control: it is known to be 0.234 pF, so any rate where the control drifts
> is a rate where the method has broken down.
> 
>     py -3.14 scripts/opendrain_driven_capacitance.py
> 

`scripts/opendrain_released_capacitance.py`:

> The open-drain part's own pad capacitance versus bias, released and driven.
> 
> The open-drain file declares C_comp 5.0 pF. Two solves of the same die disagree: the
> single-fixture loop value is 3.0 pF and the two-fixture push-pull solve gives 1.75 pF. The
> "released state is 0.25 pF" figure that has been quoted for this part is io_buf's number, from
> a routine explicitly limited to io_buf; no released-state measurement of THIS part exists.
> 
> Method, identical to the io_buf measurement so the numbers are comparable:
> 
>     I_total(V) = I_conduction(V) + C(V) dV/dt
>     a DC sweep is the conduction term with dV/dt exactly zero
>     C(V) = [I_ramp(V) - I_dc(V)] / slope
> 
> No output-enable pin is needed. This output stage is NMOS-only to ground, so holding the input
> at the level that leaves the pull-down off IS the released state. Both input levels are swept
> rather than assumed, and the released one is identified by its conduction current.
> 
>     py -3.14 scripts/opendrain_released_capacitance.py
> 

