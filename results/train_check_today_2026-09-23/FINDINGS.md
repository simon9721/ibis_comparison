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

## Step 8's models on the train: inv_chain improves, io_buf will not simulate

Rerun with the builds that choose K **and the curve shape** from the pad run's timing
(step 8), which fixed inv_chain's single-pulse error (34 -> 5 %):

| buffer | model | pulse 1 | settled |
|---|---|---:|---:|
| inv_chain | shipped | +17.5 % | -8.3 % |
| inv_chain | file-only (universal shape) | +41.2 % | +9.6 % |
| inv_chain | **file + shape (K6, 0.4/0.9)** | **+6.9 %** | **-6.8 %** |
| ex2 | file + shape | -17.5 % | -19.1 % (the selector kept the universal shape, so this is the same build) |
| io_buf | file + shape (K1, 0.4/0.9) | - | **ngspice did not converge** |

* **inv_chain's shape fix carries to the train**: better than the shipped model on both the
  first pulse (+6.9 against +17.5 %) and settled (-6.8 against -8.3 %), where the universal
  shape was +41.2 / +9.6 %. One buffer, but it is the one the recipe used to fail.
* **io_buf's selected shape will not simulate a train.** The build scores 6.1 % on single
  pulses, and on the 40 ns train deck ngspice collapses its timestep ("Reference value ..."
  repeated) and writes a single point at t = 0. Scoring that empty trace reads as -100 %,
  which is not a model error - the script now detects a truncated run and says so instead.
  This is the io_buf stall the 09-10 round hit during pad calibration, and a shape the
  selector prefers can trigger it: a robustness problem in the recipe, not just in one run.

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

## On the train, C_comp matters - where on a single pulse it does not

The file-only build differs from the track-1 one in two ways, and steps 3, 4a and 4b already
built each alone, so the split needed only their trains (ex2, settled):

| build | C_comp | shape | settled train |
|---|---|---|---:|
| track-1 | 1.7 (measured) | family | **-9.5 %** |
| step 4b | 1.7 | universal | -14.5 % |
| file-only | 2.64 (knee) | universal | -19.1 % |
| step 4a | 5.0 (declared) | family | -23.6 % |
| step 3 | 5.0 | universal | -26.2 % |

At the universal shape the C_comp axis is monotone and steep: **1.7 -> -14.5 %, 2.64 -> -19.1 %,
5.0 -> -26.2 %**, about -5 % per pF. The single-pulse peak is nearly blind to C_comp once K is
right (ex2 scores *better* at the estimated 2.31 pF than at the measured 1.7); the settled
train is not. **So a stressed train is an observation that carries C_comp**, which is exactly
what track 1 lacks - and it is a measurement a user can make at the pad.

Two cautions before treating that as a recipe:

* the shape costs 5 points on the train too (track-1 against step 4b), so the train does not
  isolate C_comp any more than the single pulse isolates K;
* **no C_comp zeroes it.** Extrapolating -5 %/pF from -14.5 % at 1.7 pF reaches zero only at a
  negative C_comp. Under the settled train there is a deficit of roughly 6-9 % that C_comp
  cannot explain - the chain's recovery between pulses, which is what the 09-10 round could not
  fix with `x_lin` either.

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
