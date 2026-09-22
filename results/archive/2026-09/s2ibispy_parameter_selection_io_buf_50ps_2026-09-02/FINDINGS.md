# Parameter selection across all three buffers

Item 3 of `0902_plan.md`. Produced by `scripts/select_s2ibispy_parameters.py`,
one run per recipe, no per-buffer wiring — the component, driver model, netlist
directory, supply and fixture resistance are all read out of the recipe.

Each candidate passes or fails on five gates: conversion exit code (which
includes ibischk), `max abs Ku`/`max abs Kd` <= 1.25, at least 5 V-T samples
across the output edge, HSPICE native IBIS simulating the model, and the pybis
subcircuit converging in ngspice.

Scored against the transistor on a **normal full-swing edge**. Stress cases are
deliberately out of scope: matching a clean transition is the precondition for
anything else meaning much.

## inv_chain — a clear win

Settles in 0.498 ns while capturing for 6 ns, so 92% of its V-T resolution was
being spent on flat waveform.

| | window | sampling | edge samples | pad RMSE | timing shift |
|---|---:|---:|---:|---:|---:|
| shipped | 6.000 ns | 6.00 ps | 3.0 | 11.04 mV | +5.5 ps |
| **selected** | **0.623 ns** | **0.62 ps** | **29.0** | **4.12 mV** * | **−0.1 ps** * |

\* measured at the 2.0 margin (0.997 ns window); the 1.25 margin used here gives
finer sampling still and was not re-benched.

All seven edge rates passed every gate, so the selection is the fastest offered:
`tr = 1 ps`.

## io_buf — the selector reproduces a decision that took a week

| tr | edge samples | max abs Ku | verdict |
|---:|---:|---:|---|
| 200 ps | 30.0 | 1.043 | accept |
| 100 ps | 30.0 | 1.090 | accept |
| **50 ps** | **30.0** | **1.180** | **accept — selected** |
| 20 ps | 30.0 | 1.714 | reject |
| 10 ps | 37.0 | 2.334 | reject |
| 5 ps | 36.0 | 2.091 | reject |
| 1 ps | 36.0 | 2.863 | reject |

**It chose 50 ps — the same answer the August work reached**, and for the same
underlying reason, but by a static check taking seconds rather than by watching
ngspice stall for 240 s.

The numbers corroborate closely. `io_buf_fast_edge_regen_2026-08-19` recorded
`max abs Ku` of 1.178 at 50 ps and 1.655 at 20 ps; this run measured 1.180 and
1.714 under a slightly different window. Same cliff, same location.

Note io_buf keeps a long window — it settles in 5.18 ns, so 6.479 ns is chosen
against 6.000 ns inherited. There is no resolution to win here, and the
selector correctly does not try. **A 2.0 margin would have handed it 10.4 ns,
coarser than what it already had.**

Expect about 35 ps of built-in lateness at 50 ps, from the 0.70 x tr law.

## ex2 — no candidate passed, and that is a calibration problem, not a discovery

| tr | edge samples | max abs Ku | verdict |
|---:|---:|---:|---|
| 200 ps … 1 ps | 76–77 | 1.283 – 1.343 | reject, all seven |

Before reading anything into that, the shipped models:

| model | max abs Ku | vs the 1.25 gate |
|---|---:|---|
| inv_chain shipped | 1.012 | pass |
| io_buf shipped 50 ps | 1.178 | pass |
| io_buf 20 ps (rejected in August) | 1.655 | fail |
| **ex2 shipped fast_5ps** | **1.244** | **pass by 0.006** |
| **ex2 shipped slow_1ns** | **1.250** | **exactly at the limit** |

ex2 has always sat on the threshold. The gate slices straight through where this
buffer lives, so its rejection says more about where 1.25 was drawn than about
the candidates.

**And the procedure made ex2 slightly worse.** Same edge rate, only the window
changed:

| window | max abs Ku |
|---|---:|
| 8.000 ns (shipped) | 1.244 |
| 2.673 ns (selected by the probe) | 1.299 |

Shortening the window degraded the extraction by 0.055. That is the risk in the
settling margin, showing up for real: ex2 settles at 2.138 ns by the 0.5%-of-
excursion criterion, but a 1.25x window on that number evidently truncates
something the extraction depends on.

So for ex2 the honest result is: **inconclusive, do not adopt.** Two things need
resolving first — whether 1.25 is the right coefficient limit given a healthy
buffer sits at 1.244, and why ex2's Ku exceeds 1 at all, which nothing here
explains.

## What this closes, and what it does not

Closed:

- the conversion is deterministic for runs that complete
- the instability was the 60 s per-job timeout, fixed upstream (`a7b0ead`)
- accuracy improves monotonically with faster `tr`, no plateau over four decades
- the error is mostly a timing shift of about **0.70 x tr**
- `sim_time` controls V-T sampling and was never chosen for any buffer
- a general, measurement-driven selector exists and needs no per-buffer wiring
- it reproduces the io_buf decision independently

Open:

- **the coefficient limit is not calibrated.** 1.25 passes io_buf's shipped
  model at 1.178 and fails ex2's candidates at 1.28, while ex2's own shipped
  model sits at 1.244. It separates io_buf's known-bad 20 ps model correctly and
  is ambiguous everywhere else.
- **the settling margin is still a judgement.** 2.0 was too loose and would have
  hurt io_buf; 1.25 is too tight for ex2. It probably should not be a single
  constant.
- **why ex2's Ku exceeds 1** at every edge rate and every window. Unexplained.
- **nothing has been adopted.** The study still points at the shipped models.
  inv_chain has a clear case for switching; io_buf would land where it already
  is; ex2 should not move.

## Files

- `selection.csv`, `decision.json` in each
  `results/s2ibispy_parameter_selection_<recipe>_2026-09-02/`
- `probe/` — the observation pass
- `tr<N>ps/` — one directory per candidate with its recipe, model and gate runs
