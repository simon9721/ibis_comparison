# Xyce pybis Context38 Variant Sweep

Same compact stressed context stimulus as the coarse cross-flow test:

- 2 ns UI
- 30 cm total RLGC delay/loss represented as 10 coarse sections
- R/G loss x5
- context38 deterministic bit pattern covering all rise/fall contexts

| Variant | Return | Timed out | t end | Completed | Wall s | Note |
|---|---:|---:|---:|---:|---:|---|
| edge15_flat4p2 | timeout | True | 24.16 ns | False | 60.01 | current accepted PRBS/RLGC continuation setup |
| tanh10 | 0 | False | 76.00 ns | True | 9.84 | global tanh10 smoothing |
| tanh15 | 0 | False | 76.00 ns | True | 8.73 | global tanh15 smoothing |
| tanh30 | timeout | True | 58.14 ns | False | 60.01 | global tanh30 smoothing |
| tailflat4p2 | timeout | True | 15.28 ns | False | 60.01 | tail-table flattening only |
| edge20_flat4p2 | timeout | True | 62.06 ns | False | 60.02 | edge/latch tanh20 plus flat tail |
| edge30_flat4p2 | timeout | True | 56.27 ns | False | 60.03 | edge/latch tanh30 plus flat tail |
| edge50_flat4p2 | 0 | False | 76.00 ns | True | 9.29 | less-smoothed edge controls plus flat tail |
| edge55_flat4p2 | timeout | True | 32.30 ns | False | 60.02 | edge/latch tanh55 plus flat tail |
| edge60_flat4p2 | 0 | False | 76.00 ns | True | 9.24 | edge/latch tanh60 plus flat tail |
| edge75_flat4p2 | timeout | True | 42.48 ns | False | 60.01 | edge/latch tanh75 plus flat tail |

Passing variants also get `*_summary.csv`, `*_events.csv`, and plots under `plots/`.
