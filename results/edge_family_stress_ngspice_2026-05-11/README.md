# ngspice Refspice Edge-Family Stress Study

Goal: find a transient setup where real pattern-dependent edge spread is
visible before changing the eye tool. This uses ngspice plus the
transistor-level `io_buf.sp` model as the raw reference.

Stress knobs:

- reduce UI from 5 ns to 2 ns and 1 ns
- increase channel length from 10 cm to 30 cm by adding RLGC sections
- optionally scale simple conductor/dielectric loss with `R` and `G`

The primary metric is 50% delay peak-to-peak in UI. Bigger values mean
the edge family should visibly thicken in an eye diagram, but very large
multi-UI values mean the eye is already severely closed and edge pairing
is no longer a clean jitter measurement.

## Recommended Clean Stress Points

These cases show real edge spread without pushing the response into
multi-UI ambiguity. They are the best next targets for pybis and Xyce.

| Case | Direction | Delay p2p | Delay p2p UI | Slew p2p | Residual p95 |
|---|---|---:|---:|---:|---:|
| ui2_len30cm_loss5 | fall | 101.3 ps | 0.0507 UI | 5.5 ps | 1258.5 mV |
| ui2_len30cm_loss1 | fall | 84.9 ps | 0.0424 UI | 6.9 ps | 1324.9 mV |
| ui2_len30cm_loss5 | rise | 83.0 ps | 0.0415 UI | 54.5 ps | 1171.5 mV |
| ui2_len10cm_loss5 | fall | 75.7 ps | 0.0379 UI | 2.1 ps | 1297.8 mV |
| ui2_len10cm_loss1 | fall | 72.7 ps | 0.0363 UI | 2.2 ps | 1312.9 mV |
| ui2_len30cm_loss1 | rise | 71.4 ps | 0.0357 UI | 60.1 ps | 1239.1 mV |
| ui2_len10cm_loss1 | rise | 22.6 ps | 0.0113 UI | 93.9 ps | 975.2 mV |
| ui2_len10cm_loss5 | rise | 15.7 ps | 0.0079 UI | 92.8 ps | 959.6 mV |

## Over-Stress Cases

These are useful for forcing eye closure, but not ideal for measuring
ordinary jitter because one output transition can be influenced by
multiple input bits.

| Case | Direction | Delay p2p | Delay p2p UI | Slew p2p |
|---|---|---:|---:|---:|
| ui1_len10cm_loss1 | fall | 4048.8 ps | 4.0488 UI | 4128.5 ps |
| ui1_len30cm_loss1 | rise | 3055.6 ps | 3.0556 UI | 6660.0 ps |
| ui1_len30cm_loss1 | fall | 2076.3 ps | 2.0763 UI | 27.9 ps |
| ui1_len10cm_loss1 | rise | 2017.8 ps | 2.0178 UI | 2333.9 ps |

## Files

- `stress_summary.csv`: aggregate metrics by case and edge direction
- `stress_events.csv`: per-edge measurements
- `run_summary.csv`: simulator return codes and runtimes
- `plots/stress_matrix_summary.png`: compact comparison plot
- `plots/*_edge_families.png`: per-case edge-family overlays
- `plots/*_eye_overlay.png`: actual 2-UI eye overlays for each stress case
