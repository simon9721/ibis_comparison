# Cross-Flow Edge-Family Stress Comparison

This ports the two clean ngspice-refspice stress points to pybis and Xyce.
The goal is to see whether the more realistic eye/edge-family behavior is
preserved across the comparison flows.
Stimulus: `PRBS7-80`, 80 bits, skip 10 UI for edge metrics.

Flows:

- ngspice + transistor-level `io_buf.sp`
- ngspice + pybis
- Xyce + transistor-level `io_buf.sp`
- Xyce + pybis `tanh10`

## Run Status

| Case | Flow | Return | Timed out | Wall s | Output |
|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | 0 | False | 0.73 | True |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | 0 | False | 12.29 | True |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | 0 | False | 0.78 | True |
| ui2_len30cm_loss5_coarse10 | xyce_pybis | timeout | True | 300.01 | True |

## Edge-Family Metrics

| Case | Flow | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |
|---|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | rise | 117.5 ps | 0.0588 UI | 142.2 ps | 1095.0 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | fall | 150.3 ps | 0.0751 UI | 33.7 ps | 1263.4 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | rise | 2004.3 ps | 1.0021 UI | 2053.7 ps | 1158.9 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | fall | 2039.0 ps | 1.0195 UI | 52.5 ps | 1156.1 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | rise | 111.8 ps | 0.0559 UI | 167.8 ps | 1093.9 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | fall | 153.8 ps | 0.0769 UI | 39.5 ps | 1266.4 mV |

## Files

- `run_summary.csv`: command status
- `stress_summary.csv`: aggregate edge-family metrics
- `stress_events.csv`: per-edge measurements
- `plots/*_eye_overlay.png`: 2-UI eye views
- `plots/*_edge_families.png`: input-referenced edge-family overlays
- `plots/*_transient_overlay.png`: transient overlays per stress case
- `plots/*_metrics_summary.png`: compact metric comparison per stress case
