# Final PRBS7 + 50 Ohm RLGC Comparison

Date: 2026-05-11

This folder is the frozen accepted benchmark for the current open-source
IBIS comparison work. It intentionally excludes HSPICE because the matched
HSPICE `io_buf.sp` run is not ready yet.

## Accepted Benchmark

- PRBS7 stimulus
- 5 ns UI, 200 Mbps
- 200 ps input rise/fall
- 1000 ns transient
- new 50 ohm 10-section RLGC channel
- 50 ohm receiver termination
- physical clock/UI-grid eye folding only

Ideal T-line PRBS results are stress tests and are not part of this
accepted result folder.

## Cases

| Case | Model | Completed | Eye height | Eye width | Rise/Fall 50 split |
|---|---|---:|---:|---:|---:|
| ngspice + io_buf.sp | io_buf.sp transistor-level | True | 296.4 mV | 2617.5 ps | 0.265 UI |
| Xyce + io_buf.sp | io_buf.sp transistor-level | True | 305.4 mV | 2622.5 ps | 0.265 UI |
| ngspice + pybis | pybis2spice direct | True | 1064.2 mV | 5000.0 ps | 0.274 UI |
| Xyce + pybis edge15_flat4p2 | pybis2spice Xyce continuation | True | 998.2 mV | 1370.0 ps | 0.277 UI |

## Key Files

- `final_metrics_summary.csv`: combined per-case metrics
- `pairwise_error_summary.csv`: Xyce-vs-ngspice error summaries
- `plots/refspice_vs_pybis_ngspice.png`: ngspice refspice-vs-pybis overlay
- `plots/refspice_vs_pybis_xyce.png`: Xyce refspice-vs-pybis overlay
- `plots/refspice_vs_pybis_all.png`: four-trace refspice/pybis overlay
- `plots/refspice_vs_pybis_error_summary.csv`: refspice-vs-pybis error summaries
- `plots/rx_transient_overlay_0_120ns.png`: receiver overlay
- `plots/rx_transient_overlay_30_80ns.png`: early transition zoom
- `eyes/*/*_overlay.png`: physical clock-folded eye overlays

## Xyce pybis Status

The Xyce pybis case is a practical continuation setup, not a direct
unmodified pybis pass. It uses `edge15_flat4p2`: edge/latch `tanh15`
conditioning plus a flat rising KUR/KDR table tail after 4.2 ns.
This is the best full 1000 ns PRBS/RLGC path found so far, but the
direct/minimally modified Xyce pybis question remains open.
