# Measuring the buffer to set its conversion parameters

Item 3 of `0902_plan.md`, the part that matters: stop inheriting `sim_time` and
`tr/tf`, and derive them from one probe simulation of the buffer being
converted.

Produced by `scripts/select_s2ibispy_parameters.py`.

## Why two parameters and not one

The V-T table is 1000 uniformly spaced points across `sim_time` — 1000 being the
IBIS >= 4.0 ceiling — so:

```
V-T sampling = sim_time / 1000
```

`sim_time` has to be long enough to capture the buffer settling and short enough
that 1000 points resolve the edge. Tuning `tr` alone leaves the resolution
wherever the inherited window happened to put it.

Nobody had chosen these numbers. inv_chain and io_buf were both at 6 ns, ex2 at
8 ns, and the values appear to have been carried forward from the first recipe
written.

## What the probe measured

One conversion at a safe 200 ps edge with the inherited window, read back from
its own generated V-T tables:

| | |
|---|---|
| settles by | **0.498 ns** |
| output edge, 20–80% | **18.0 ps** |
| inherited window | 6.000 ns — **8% used**, 6.00 ps sampling |
| chosen `sim_time` | **0.997 ns** — 1.00 ps sampling |

92% of inv_chain's V-T resolution was being spent on flat, settled waveform.

## The sweep, under the chosen window

| tr | edge samples | max abs Ku | max abs Kd | verdict |
|---:|---:|---:|---:|---|
| 200 ps | 19.0 | 1.030 | 1.034 | accept |
| 100 ps | 18.1 | 1.021 | 1.034 | accept |
| 50 ps | 19.0 | 1.027 | 1.033 | accept |
| 20 ps | 19.1 | 1.027 | 1.034 | accept |
| 10 ps | 18.1 | 1.024 | 1.034 | accept |
| 5 ps | 19.1 | 1.027 | 1.034 | accept |
| **1 ps** | **19.1** | **1.026** | **1.033** | **accept — selected** |

Every candidate passed. Note the edge-sample count barely moves with `tr`: it
sits near 19 throughout, because inv_chain's *output* edge stays ~18 ps however
fast you drive it. That is the buffer's own rise time, and it is why `sim_time`,
not `tr`, was the binding constraint.

## Does the selection actually help?

Scored on the July sanity bench — HSPICE native IBIS, 1 ps input edges, direct
50 ohm || 2 pF load, against the cached transistor run.

| model | edge samples | pad RMSE | rise 50% shift |
|---|---:|---:|---:|
| shipped, 6 ns / 5 ps | 3.0 | 11.04 mV | +5.5 ps |
| edge-rate tuning only, 6 ns / 1 ps | 4.0 | 6.98 mV | +2.2 ps |
| **selected, 0.997 ns / 1 ps** | **19.1** | **4.12 mV** | **−0.1 ps** |

**2.7x better pad RMSE than the shipped model, and the timing shift goes to
essentially zero.**

The middle row is the important control. Tuning only the edge rate — which is
what the earlier sweep did — reaches 6.98 mV. Adding the measured `sim_time`
takes it to 4.12 mV. So roughly 40% of the remaining error was the capture
window, and no amount of edge-rate tuning would have found it.

## The gates

| gate | threshold | catches |
|---|---|---|
| exit code | must be 0 | the conversion lost a SPICE job |
| ibischk | no critical errors | invalid IBIS |
| max abs Ku, max abs Kd | <= 1.25 | corrupted coefficient extraction |
| edge samples | >= 5 | the V-T grid cannot resolve the transition |

The edge-samples gate is the one that catches io_buf's known failure by its
cause rather than its symptoms. At 6 ps sampling a 5 ps edge lands inside a
single sample, `C_comp * dV/dt` reads ~660 mA against a 23 mA fixture current,
and the endpoints, onset delays and gate-state maps are all corrupted
downstream. The gate rejects that before any of it happens.

Worth stating: **the currently shipped inv_chain model has 3.0 edge samples and
would fail this gate.**

## Limits, and what has not been done

- **Only inv_chain is wired up.** `BUFFERS` in the selector needs io_buf and ex2
  adding before items 1 and 2 can use it. Mechanical, but real work.
- **The settling margin is a judgement, not a measurement.** `sim_time` is set
  to 2x the observed settling. 2x is conservative rather than derived; a shorter
  margin would buy more resolution and risks truncating the tail.
- **No ngspice convergence gate.** io_buf's 20 ps model passed every static
  check and then stalled ngspice for 240 s on a study stimulus. That gate needs
  a downstream simulation and is not implemented here.
- **This has not been adopted.** The study still points at the shipped 6 ns /
  5 ps model. Regenerating for real means re-running everything that consumes
  inv_chain's IBIS, and that is a separate decision.

## Files

- `decision.json` — the observation, the chosen parameters, the gates, rejects
- `selection.csv` — every candidate with its measurements
- `probe/` — the observation pass
- `tr<N>ps/` — one directory per candidate, each with its recipe and model

HSPICE intermediates are left on disk and kept out of the repo; only the models,
recipes and results are tracked.
