# gate_step_prototype_2026-09-10

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 1.7G, 667 files, written 2026-09-10 to 2026-09-17
- location before archiving: `results/gate_step_prototype_2026-09-10`

## Contents (top level)

```
io_buf/                                            1.7G  667 files
```

## Produced by

`scripts/build_iobuf_hump_figure.py`:

> io_buf's pull-down release hump: the transistor's walks earlier under stress, the model's does not.
> 
> Left panel the transistor, right panel the step-replay model with a 3-stage current-limited
> pull-down chain, five pulse widths each, plotted from the input reversal so the two panels are
> directly comparable. Reads existing runs only; nothing is simulated.
> 
>     py -3.14 scripts/build_iobuf_hump_figure.py
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

`scripts/gate_step_prototype.py`:

> The command as the measured step response itself — for a linear predriver (io_buf).
> 
> io_buf's predriver is linear from input to pad (`predriver_stages_2026-09-09`):
> under any pulse its gate is the superposition of its own two full-swing step
> responses, P(t) = S_rise(t − t_on) + S_fall(t − t_off) − 1, to within 0.035.
> A fitted stage cannot draw its decelerating ramp; the step response can.
> 
> Built into the model: a 3 ps delayed copy of the digital input marks each
> edge; a latch samples the edge time; the elapsed time since the last rising
> and the last falling edge index two pwl tables (the step responses); GUP is
> their sum minus one, clipped. The same for GDN from the NMOS-gate path.
> Exact for one pulse; on a train it keeps only the last edge of each direction
> (right when each response settles within one period).
> 
>     --source real   step responses from the probed transistor gates (n2, n3)
>     --source ibis   from the tables' Ku(t)/Kd(t) inverted through the prior
> 
>     py -3.14 scripts/gate_step_prototype.py --source real --maps prior --depth-residual
> 

`scripts/track2_train_check.py`:

> Track 1 vs track 2 on a stressed pulse train: do the builds that are right on one
> pulse stay right when pulses arrive before the buffer has recovered?
> 
> Bench: 8 pulses at 50 % duty at the matrix's deepest width, 50 Ohm || 2 pF, and the
> SAME 50 ps input edges the single-pulse matrix and the calibration used (the 2026-09-08
> train reference used 1 ps edges, which on inv_chain's 1.4 V threshold changes the
> effective width by 28 ps; the transistor is re-run here with 50 ps edges).
> 
> Scoring: per pulse, the transistor's peak and the model's peak inside a window that is
> shifted by the buffer's own input-to-pad delay (measured on the transistor's first
> pulse), so a pad response that lands after the input period (inv_chain: ~250 ps delay
> on a 222 ps period) is still scored against its own pulse.
> 
>     py -3.14 scripts/track2_train_check.py
> 

