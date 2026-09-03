# Edge Family Diagnostics

This folder checks whether the accepted PRBS/RLGC transient data contains
multiple visibly different rising and falling receiver edge families.

Method:

- detect each `v(in_dig)` 50% crossing after the first 10 UIs
- extract `v(n10b)` from -1 ns to +5 ns around that input crossing
- do not align traces to the output crossing
- measure output 50% delay spread, 20-80% slew spread, and residual
  spread relative to the median edge shape

Main result:

The accepted 5 ns UI / 50 ohm RLGC data has very little edge-family
variation. The eye tool is not collapsing a wide family of edges into
one template; the transient waveforms themselves are already close to
template-like for each edge polarity.

## Summary

| Case | Direction | Edges | 50% delay p2p | 20-80 slew p2p | Residual p95 | Residual max |
|---|---|---:|---:|---:|---:|---:|
| ngspice + io_buf.sp | rise | 46 | 0.57 ps | 0.94 ps | 2.69 mV | 5.21 mV |
| ngspice + io_buf.sp | fall | 46 | 2.17 ps | 0.54 ps | 32.76 mV | 77.67 mV |
| Xyce + io_buf.sp | rise | 46 | 4.68 ps | 9.93 ps | 3.62 mV | 7.05 mV |
| Xyce + io_buf.sp | fall | 46 | 3.76 ps | 2.40 ps | 31.11 mV | 74.48 mV |
| ngspice + pybis | rise | 46 | 0.00 ps | 0.00 ps | 0.83 mV | 5.38 mV |
| ngspice + pybis | fall | 46 | 0.36 ps | 0.09 ps | 85.51 mV | 200.49 mV |
| Xyce + pybis edge15_flat4p2 | rise | 46 | 7.19 ps | 0.58 ps | 8.95 mV | 17.11 mV |
| Xyce + pybis edge15_flat4p2 | fall | 46 | 7.17 ps | 0.68 ps | 31.67 mV | 147.23 mV |

## Files

- `edge_family_summary.csv`: aggregate variation metrics
- `edge_family_events.csv`: one row per detected edge
- `*_edge_families.png`: per-case rising/falling overlays and residuals
- `edge_family_variation_summary.png`: compact bar-chart summary
