# Xyce Edge50 122 ns Fix Sweep

Targeted sweep using the same PRBS62 / 2 ns UI / coarse 30 cm RLGC / loss x5 deck
that stalls with `edge50_flat4p2` at about 122.26 ns.

| Variant | Completed | End ns | Return | Timeout | Wall s | Last NX ns | Last Ku | Last Kd | Note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| gear2_nl50 | True | 124.000 | 0 | False | 15.01 | 1.910 | 0.169335 | 0.0929138 | solver only: Gear order 2 and more nonlinear iterations |
| trap_nl50_no_reverse | False | 122.260 | timeout | True | 90.01 | 0.170 | 0.000578282 | 1.00184 | solver only: keep trap, allow more nonlinear iterations, disable timestep reversal |
| no_uic | False | nan | 1 | False | 0.04 | nan | nan | nan | setup only: let Xyce calculate the operating point before transient |
| edge_delay20p | True | 124.000 | 0 | False | 9.11 | 1.900 | 0.166779 | 0.103412 | model parameter only: increase internal edge-detect T-line delay from 10 ps to 20 ps |
| edge15_model | False | 86.550 | timeout | True | 90.01 | 0.420 | 0.96449 | -0.019681 | model comparison: existing edge15_flat4p2 smoothing |
| tanh15_model | False | 100.250 | timeout | True | 90.01 | 0.150 | 0.0480183 | 0.954545 | model comparison: existing broad tanh15 smoothing |

A variant that still ends near 122.26 ns is reproducing the same stall.
A variant that reaches 124 ns completed the focused PRBS62 case.
