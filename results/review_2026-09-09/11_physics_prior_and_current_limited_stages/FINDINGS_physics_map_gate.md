# From the IBIS tables to the gate: a physics prior on the map

*2026-09-10*  ·  tool: `scripts/physics_map_gate_from_ibis.py`  ·  figure `physics_map_gate.png`, numbers `results.csv`

## Why this test

`../predriver_stages_2026-09-09/` proved the output stage is a static Ku(g)
map of one gate node, and that the IBIS tables only pin the *product* Ku(t) at
full swing. Any monotone re-pairing of (map, gate) reproduces full swing; only
the right pair reproduces stress. Silicon data settled the pair for our three
buffers, but a converter does not have silicon. The question here: **can a
physics-shaped map break the tie by itself?**

The prior: `Ku(g) = ((g − vt) / (1 − vt))^alpha` for g > vt, else 0 — a
threshold and a power law, two numbers.

## 1. The three silicon maps share the shape

Fitted on the working range (Ku ≥ 0.1), with the real gate at five Ku levels
against the prior's inverse:

| buffer | vt | alpha | rms | gate at Ku = 0.2 / 0.4 / 0.6 / 0.8 / 0.9, real | prior |
|---|---:|---:|---:|---|---|
| ex2 | 0.57 | 0.64 | 0.068 | 0.62 0.70 0.75 0.84 0.88 | 0.60 0.67 0.76 0.87 0.93 |
| inv_chain | 0.49 | 0.60 | 0.070 | 0.53 0.62 0.71 0.79 0.82 | 0.52 0.60 0.71 0.84 0.92 |
| io_buf | 0.50 | 0.78 | 0.014 | 0.58 0.65 0.76 0.87 0.93 | 0.56 0.65 0.76 0.88 0.94 |

Three different processes and topologies, one family: threshold at half the
gate swing, a slightly concave power. Up to Ku = 0.6 the prior places the gate
within 0.03 on all three; above 0.8 the real maps saturate earlier than a
power law (the real gate is at 0.82–0.88 where the prior says 0.92–0.93). A
third parameter for the top end would close that; a universal (vt 0.5,
alpha 0.7) is already a usable default.

## 2. The gate the tables imply, through the prior

Invert the prior on the shipped model's full-swing gate-part Ku(t) (rest-
referenced, residual excluded). Below threshold the gate is invisible to the
tables; each edge is continued with the slope it has just above threshold.

| buffer | real gate rise t50 / 10–90 (ps) | derived | real fall t50 / 10–90 | derived | rms 5–8 ns |
|---|---|---|---|---|---:|
| ex2 | 1096 / 662 | 1058 / 986 | 1170 / 798 | 1204 / 904 | 0.094 |
| inv_chain | 302 / 50 | 312 / 38 | 308 / 72 | 290 / 68 | 0.028 |
| io_buf | 1198 / 2566 | 1278 / 2826 | 260 / 448 | 348 / 854 | 0.159 |

inv_chain's gate is recovered to 10 ps from the IBIS tables and the prior. ex2's
is recovered at the 50 % point (38 ps early) but its top end is stretched
(10–90 986 vs 662) — the prior's late saturation, inverted. io_buf's ramp is
recovered above threshold and mis-drawn below it (the extrapolation is a poor
stand-in for a ramp that starts at 0). Where the map is right, the gate the
tables imply is the real gate — so the "IBIS-implied map is late" failure of
the replay round was a failure of pairing Ku(t) with the *model's* RC gate, not
a defect of the tables.

## 3. Superposition of the derived step responses under stress

| buffer | W (ps) | real gate max | superposition | shipped GUP | real Ku max ¹ | Ku from superposition | shipped Ku |
|---|---:|---:|---:|---:|---:|---:|---:|
| ex2 | 810 | 0.758 | 0.989 | 0.913 | 0.640 | 0.984 | 0.963 |
| ex2 | 975 | 0.936 | 0.996 | 0.963 | 0.963 | 0.994 | 0.991 |
| inv_chain | 104 | 0.879 | 0.986 | 0.934 | 0.862 | 0.984 | 0.975 |
| inv_chain | 135 | 1.003 | 0.997 | 0.985 | 1.010 | 0.997 | 1.005 |
| io_buf | 1505 | 0.672 | 0.640 | 0.405 | — | — | — |
| io_buf | 2354 | 0.876 | 0.841 | 0.720 | — | — | — |

¹ two-fixture Ku after +90 ps; io_buf's Ku peaks before the reversal and is
not comparable in this window.

* **io_buf**: superposition of the derived steps lands within 0.035 of the
  real gate on all five widths where the shipped model's RC gate is 0.15–0.27
  low. This is the io_buf pedestal fix derived from the tables alone.
* **inv_chain**: right to 0.01 at the three shallow widths; over-predicts by
  0.05–0.11 at the two deepest, exactly the sub-linearity measured on vout6/7.
  In Ku terms that is 0.98 predicted vs 0.86 real at 104 ps — the pad cares.
* **ex2**: superposition is wrong (0.99 vs 0.76): three sub-linear stages in a
  row. No linear structure derived from the tables can do ex2; the cascade
  N = 5 that "worked" was a fit.

## 4. What this fixes in the direction

The tie between map and gate is breakable without silicon: assume the MOSFET
shape, invert the tables, and the full-swing gate comes out right where the map
is right. What is still missing is the *predriver's non-linearity* — the
current-limited return that makes a partial pulse smaller than superposition
says. That is a property of the predriver stages, invisible at full swing to a
linear description, and it is what `../current_limited_stages_2026-09-10/`
tests: whether a current-limited stage fitted only at full swing predicts it.
