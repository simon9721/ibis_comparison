# Xyce Edge50 122 ns Fix Sweep

Targeted sweep using the same PRBS62 / 2 ns UI / coarse 30 cm RLGC / loss x5 deck
that stalls with `edge50_flat4p2` at about 122.26 ns.

| Variant | Completed | End ns | Return | Timeout | Wall s | Last NX ns | Last Ku | Last Kd | Note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| trap_nl50 | False | 122.260 | timeout | True | 90.02 | 0.170 | 0.000578282 | 1.00184 | isolation: trap order 1, nlmax 50, timestep reversal kept enabled |
| gear2_nl8 | True | 124.000 | 0 | False | 15.03 | 1.910 | 0.169335 | 0.0929138 | isolation: Gear order 2 but original nlmax 8 |
| gear1_nl50 | True | 124.000 | 0 | False | 14.84 | 1.910 | 0.169335 | 0.0929138 | isolation: Gear order 1 and nlmax 50 |
| gear1_nl8 | True | 124.000 | 0 | False | 15.07 | 1.910 | 0.169335 | 0.0929138 | isolation: Gear order 1 with original nlmax 8 |

A variant that still ends near 122.26 ns is reproducing the same stall.
A variant that reaches 124 ns completed the focused PRBS62 case.
