# Cross-Flow Edge-Family Stress Comparison

This ports the two clean ngspice-refspice stress points to pybis and Xyce.
The goal is to see whether the more realistic eye/edge-family behavior is
preserved across the comparison flows.

Flows:

- ngspice + transistor-level `io_buf.sp`
- ngspice + pybis
- Xyce + transistor-level `io_buf.sp`
- Xyce + pybis `edge15_flat4p2`

## Run Status

| Case | Flow | Return | Timed out | Wall s | Output |
|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss1 | ngspice_refspice | 0 | False | 2.20 | True |
| ui2_len30cm_loss1 | ngspice_pybis | timeout | True | 240.02 | True |
| ui2_len30cm_loss1 | xyce_refspice | 0 | False | 2.50 | True |
| ui2_len30cm_loss1 | xyce_pybis | timeout | True | 240.02 | True |
| ui2_len30cm_loss5 | ngspice_refspice | 0 | False | 2.20 | True |
| ui2_len30cm_loss5 | ngspice_pybis | timeout | True | 240.01 | True |
| ui2_len30cm_loss5 | xyce_refspice | 0 | False | 2.36 | True |
| ui2_len30cm_loss5 | xyce_pybis | timeout | True | 240.01 | True |

## Edge-Family Metrics

| Case | Flow | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |
|---|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss1 | ngspice_refspice | rise | 71.4 ps | 0.0357 UI | 60.1 ps | 1239.1 mV |
| ui2_len30cm_loss1 | ngspice_refspice | fall | 84.9 ps | 0.0424 UI | 6.9 ps | 1324.9 mV |
| ui2_len30cm_loss1 | xyce_refspice | rise | 84.5 ps | 0.0422 UI | 73.9 ps | 1231.8 mV |
| ui2_len30cm_loss1 | xyce_refspice | fall | 89.1 ps | 0.0446 UI | 10.9 ps | 1320.8 mV |
| ui2_len30cm_loss5 | ngspice_refspice | rise | 83.0 ps | 0.0415 UI | 54.5 ps | 1171.5 mV |
| ui2_len30cm_loss5 | ngspice_refspice | fall | 101.3 ps | 0.0507 UI | 5.5 ps | 1258.5 mV |
| ui2_len30cm_loss5 | xyce_refspice | rise | 97.8 ps | 0.0489 UI | 57.6 ps | 1163.2 mV |
| ui2_len30cm_loss5 | xyce_refspice | fall | 106.5 ps | 0.0532 UI | 8.0 ps | 1254.4 mV |

## Files

- `run_summary.csv`: command status
- `stress_summary.csv`: aggregate edge-family metrics
- `stress_events.csv`: per-edge measurements
- `plots/*_eye_overlay.png`: 2-UI eye views
- `plots/*_edge_families.png`: input-referenced edge-family overlays
- `plots/*_transient_overlay.png`: transient overlays per stress case
- `plots/*_metrics_summary.png`: compact metric comparison per stress case
