# Would a short-LOW characterisation point fix io_buf's pull-down? - findings

*2026-09-23* · script `scripts/io_buf_pulldown_calib.py` and the probes below · follows
`results/io_buf_pulldown_depth_2026-09-22/`

## Why

io_buf's pull-down direction is 16-21 points shallow under stress while its full swing is
right to 0.4 %. The recipe calibrates the pull-up chain on one short-HIGH pad run and gives
the pull-down nothing. The obvious question was whether a short-LOW point would fix it - and
the obvious knob, the pull-down chain's own rate, turned out to be the wrong one.

## 1. The pull-down chain is inert on these pulses

Scaling the pull-down chain's discharge rate by 1.5, 2, 3, 4 changes the pad by **0.1 points**.
Lowering its threshold from the fitted 0.699999 to 0.5, 0.35 or 0.2 changes it by no more than
0.3. Probing the chain's nodes on the 163 ps pulse says why:

| node | rate x1 | rate x4 |
|---|---|---|
| CHIN | 1.000 -> 0.000 | 1.000 -> 0.000 |
| STGD1 | falls to 0.738 | falls to 0.260 |
| STGD2 | **1.000, never moves** | 0.987 |
| STGD3 | 1.000 | 1.000 |
| GDN | **0** | **0** |

Each stage has to drag the next past a threshold of 0.7 of the swing before that one starts, so
a 163-322 ps pulse dies in the first or second stage. **GDN never rises: our pull-down device
never turns on at all.** The dip the model does produce is the pull-up releasing into the 50 Ω
load, nothing more. That also explains 09-22's result that Kd = 2...5 are indistinguishable -
the chain's depth cannot matter when the pulse never reaches the end of it.

The fitted threshold sitting exactly at the optimiser's upper bound (0.699999 of a 0.7 limit)
is a sign the full-swing fit wanted something it was not allowed to have.

## 2. What actually sets the depth is the PULL-UP turning off

Scaling the **pull-up** chain's discharge rate - how fast Ku goes away - moves the depth at
once. Error in points against the transistor, at the seven widths:

| pull-up discharge | 163 | 191 | 220 | 223 | 256 | 307 | 322 | worst |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| x1 (as built) | -16.4 | -19.9 | -21.3 | -21.2 | -18.1 | -5.4 | -2.8 | 21.3 |
| **x1.2** | -8.1 | -8.9 | -5.4 | -4.6 | +3.9 | +7.1 | +6.6 | **8.9** |
| x1.35 | -1.3 | +1.5 | +9.1 | +10.0 | +14.2 | +9.8 | +7.9 | 14.2 |
| x1.5 | +6.7 | +14.1 | +20.3 | +20.6 | +18.9 | +10.2 | +8.1 | 20.6 |
| x2 | +38.8 | +38.4 | +31.1 | +30.1 | +20.9 | +10.3 | +8.2 | 38.8 |

**One number takes the worst error from 21.3 to 8.9 points.** So a short-LOW characterisation
point would fix most of this direction - and the parameter it should move is the pull-up
chain's discharge rate, not anything in the pull-down path.

The residual at x1.2 is not flat (-9 at the short widths, +7 at the long ones), so one scale
does not match the whole profile; the direction needs the knob, and something else still
shapes it.

## The common thread

inv_chain's gate stays up 10-20 ps too long and its pad runs 26 % high; io_buf's pull-up lets
go too slowly and its short-low pad is 21 points shallow. Both are the **discharge direction of
the command chain**, and both come from the same place: `s_dn` is fitted at full swing, on a
transition that is slow and unstressed, and then used on pulses where the chain's return is
most of the event. A faster final stage helped inv_chain
(`results/inv_chain_last_stage_2026-09-22/`); a faster whole-chain discharge helps io_buf here.
Whether one mechanism covers both is the question worth taking to the fit.
