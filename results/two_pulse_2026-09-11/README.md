# two_pulse_2026-09-11

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 7.9M, 80 files, written 2026-06-04 to 2026-09-11
- location before archiving: `results/two_pulse_2026-09-11`

## Contents (top level)

```
ex2/                                               3.3M  40 files
io_buf/                                            4.6M  40 files
```

## Produced by

`scripts/two_pulse_probe.py`:

> Two identical stressed pulses: does the second one carry the first one's error?
> 
> Same benches as the pulse train (`pulse_train_accumulation.py`), same three builds
> (transistor, native HSPICE IBIS, ours = cmd_clean), two pulses of the same width W with
> a gap G between the first falling edge and the second rising edge:
> 
>     settled    G = 6 ns, the pad and every internal node have returned to rest
>     unsettled  G = W, 50 % duty, the second pulse lands on the tail of the first
> 
> Per pulse: model pad-peak time minus the transistor's, and the best-fit lag.
> 
>     py -3.14 scripts/two_pulse_probe.py
> 

