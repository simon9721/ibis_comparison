# Cross-Flow Edge-Family Stress Comparison

This ports the two clean ngspice-refspice stress points to pybis and Xyce.
The goal is to see whether the more realistic eye/edge-family behavior is
preserved across the comparison flows.
Stimulus: `context38`, 38 bits, skip 2 UI for edge metrics.

Flows:

- ngspice + transistor-level `io_buf.sp`
- ngspice + pybis
- Xyce + transistor-level `io_buf.sp`
- Xyce + pybis `edge15_flat4p2`

## Run Status

| Case | Flow | Return | Timed out | Wall s | Output |
|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | 0 | False | 0.58 | True |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | 0 | False | 232.41 | True |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | 0 | False | 0.41 | True |
| ui2_len30cm_loss5_coarse10 | xyce_pybis | timeout | True | 500.01 | True |

## Edge-Family Metrics

| Case | Flow | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |
|---|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | rise | 113.5 ps | 0.0567 UI | 9.5 ps | 789.9 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_refspice | fall | 145.1 ps | 0.0726 UI | 32.1 ps | 869.5 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | rise | 4238.3 ps | 2.1191 UI | 4849.2 ps | 899.5 mV |
| ui2_len30cm_loss5_coarse10 | ngspice_pybis | fall | 42.8 ps | 0.0214 UI | 168.1 ps | 1146.8 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | rise | 107.3 ps | 0.0536 UI | 84.8 ps | 797.4 mV |
| ui2_len30cm_loss5_coarse10 | xyce_refspice | fall | 144.8 ps | 0.0724 UI | 20.6 ps | 892.3 mV |

## Files

- `run_summary.csv`: command status
- `stress_summary.csv`: aggregate edge-family metrics
- `stress_events.csv`: per-edge measurements
- `plots/*_eye_overlay.png`: 2-UI eye views
- `plots/*_edge_families.png`: input-referenced edge-family overlays
- `plots/*_transient_overlay.png`: transient overlays per stress case
- `plots/*_metrics_summary.png`: compact metric comparison per stress case
