# Today's models on a stressed pulse train - findings

*2026-09-23* · script `scripts/train_check_today.py`

## Why

All of the 09-21/22 track-1 work is single-pulse: one stressed pad run calibrates the model
and five stressed widths score it. The train results on record predate the converter's input
threshold clamp, so their inverter-chain numbers carry the defect that masks inv_chain's error
threefold. This reruns the train on today's builds - no refitting, no HSPICE (the transistor
train references at 50 ps edges are cached from 09-13).

Three models per buffer: the converter's own **shipped** model, the **track-1** build (measured
C_comp, family shape, netlist K) and the **file-only** build (knee C_comp, universal shape, K
from the timing selector). 8 pulses at 50 % duty, the width each buffer's train study used.

## Result: the train is where our model loses to the shipped one

Peak error against the transistor, per pulse and settled (pulses 4-7):

| buffer | model | pulse 1 | settled |
|---|---|---:|---:|
| ex2 | shipped | -1.0 % | **-3.8 %** |
| ex2 | track-1 | -9.2 % | -9.5 % |
| ex2 | file-only | -17.5 % | -19.1 % |
| inv_chain | shipped | +17.5 % | -8.3 % |
| inv_chain | track-1 | +19.7 % | **-4.8 %** |
| inv_chain | file-only | +41.2 % | +9.6 % |
| io_buf | shipped | -1.9 % | **-2.0 %** |
| io_buf | track-1 | +5.2 % | +4.7 % |
| io_buf | file-only | +6.6 % | +6.6 % |

* **On ex2 and io_buf the shipped model wins.** Our chain is built and calibrated for the
  single-pulse regime, and on a settled train it is 6-15 points worse than the model it is
  meant to improve on.
* **Only inv_chain's track-1 build beats shipped** (-4.8 against -8.3 %), and even there the
  file-only build does not (+9.6 %).
* **The first pulse is the single-pulse regime** and reads like it: inv_chain +17...+41 %,
  ex2 -1...-18 %. The chain's error on pulse 1 and its error when settled are different
  quantities, and a calibration that fixes one does not fix the other.
* The file-only build is consistently the worst of the three on the train. Its C_comp comes
  from the knee (ex2 2.64 pF against the measured 1.7), which the single-pulse peak is
  insensitive to - the train is not.

## Caveat, and a defect in the earlier metric

The 8th pulse scores nonsense for **every** model, shipped included (+100 % on ex2, +214 % on
io_buf): the scoring window runs past the end of the train, so the "peak" it finds is the
settle to the rail. The settled numbers above average pulses 4-7 only.
`gate_chain_train_calib.settled_error` averages pulses 4-8, so any settled figure taken from it
- including those in the 09-10 and 09-13 write-ups - is contaminated by that window. It is a
ratio of means, so the damage varies: on these nine runs it moved the answer by 0.1-0.5 points,
not enough to change any conclusion, but the metric should be fixed before it is trusted again.

## What follows

The recipe has one characterisation point and it is a single pulse. The train needs either a
second point (the 09-10 round tried exactly this and found `x_lin` could not meet both) or the
extra degree of freedom the single-pulse work also landed on - a final stage that is not
identical to the others (`results/inv_chain_last_stage_2026-09-22/`). Whether that one change
serves both regimes is the test worth running next.
