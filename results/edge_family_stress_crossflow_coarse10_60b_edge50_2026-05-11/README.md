# Cross-Flow Edge-Family Stress Comparison

This ports the two clean ngspice-refspice stress points to pybis and Xyce.
The goal is to see whether the more realistic eye/edge-family behavior is
preserved across the comparison flows.
Stimulus: `PRBS7-60`, 60 bits, skip 10 UI for edge metrics.

Flows:

- ngspice + transistor-level `io_buf.sp`
- ngspice + pybis
- Xyce + transistor-level `io_buf.sp`
- Xyce + pybis `edge50_flat4p2`

## Run Status

| Case | Flow | Return | Timed out | Wall s | Output |
|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | 0 | False | 0.55 | True |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | 0 | False | 9.22 | True |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | 0 | False | 0.58 | True |
| ui2_len30cm_loss5_coarse10 | xyce_pybis | 0 | False | 14.04 | True |

## Edge-Family Metrics

| Case | Flow | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |
|---|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | rise | 117.5 ps | 0.0588 UI | 109.3 ps | 1088.2 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | fall | 150.2 ps | 0.0751 UI | 27.8 ps | 1263.4 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | rise | 2003.6 ps | 1.0018 UI | 2054.0 ps | 1179.8 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | fall | 2039.0 ps | 1.0195 UI | 52.3 ps | 1192.5 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | rise | 109.2 ps | 0.0546 UI | 139.2 ps | 1090.4 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | fall | 153.0 ps | 0.0765 UI | 35.0 ps | 1265.8 mV |
| ui2_len30cm_loss5_coarse10 | xyce_pybis | rise | 4218.4 ps | 2.1092 UI | 4871.9 ps | 1237.4 mV |
| ui2_len30cm_loss5_coarse10 | xyce_pybis | fall | 40.9 ps | 0.0204 UI | 145.2 ps | 1260.7 mV |

## Files

- `run_summary.csv`: command status
- `stress_summary.csv`: aggregate edge-family metrics
- `stress_events.csv`: per-edge measurements
- `plots/*_eye_overlay.png`: 2-UI eye views
- `plots/*_edge_families.png`: input-referenced edge-family overlays
- `plots/*_transient_overlay.png`: transient overlays per stress case
- `plots/*_metrics_summary.png`: compact metric comparison per stress case
