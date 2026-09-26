# gate_chain_train_calib_2026-09-10

*Generated 2026-09-21 from this folder's contents, the scripts that name it and its logs,
so the folder is identifiable after it leaves the working tree. Not a study write-up.*

- size: 2.4G, 1729 files, written 2026-09-10 to 2026-09-14
- location before archiving: `results/gate_chain_train_calib_2026-09-10`

## Contents (top level)

```
ex2_c1.7/                                          742M  447 files
inv_chain_c0.6/                                    698M  529 files
inv_chain_c0.6_edge50/                             986M  753 files
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

`scripts/gate_chain_train_calib.py`:

> Two characterisation points: the single stressed pulse and a stressed train.
> 
> The one-point (pad-peak) calibration fixes the stage threshold and reproduces
> the single-pulse regime, but the file-only chains were 9 % (ex2) / 23 %
> (inv_chain) low on the settled pulses of a 50 % duty stressed train
> (`NEXT_STEPS_FINDINGS.md` §12): a pulse that arrives before the stages have
> returned to rest exercises the resistive fraction x_lin, which full swing does
> not pin either. So: for each x_lin in a small set, refit the chain at full
> swing, calibrate the threshold on the single pulse, run the train, and pick
> the x_lin whose settled train peak matches. Then score all matrix widths.
> 
>     py -3.14 scripts/gate_chain_train_calib.py --variant ex2 --ccomp 1.7 --prior 0.57 0.64 --K 3
>     py -3.14 scripts/gate_chain_train_calib.py --variant inv_chain --ccomp 0.6 --prior3 0.42 1.15 0.87 --K 7
> 

