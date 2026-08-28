# Transistor-derived Ku/Kd — representative set

Gathered by `scripts/gather_silicon_kukd_figures.py`. Every figure below is
the current version: io_buf runs use the stock `models/hspice.mod` card, and
the two-fixture solve runs on a uniform 5 ps grid.

Superseded and kept only for history:

- `results/silicon_kukd_recovery_2026-08-19/` — union grid, and io_buf on the
  RDSW-zeroed card that makes the device 8-16% too strong
- `results/silicon_vs_pybis_kukd_figures_2026-08-19/` — same caveats

| # | figure | what it shows | source |
|---|---|---|---|
| 1 | `01_validation_io_buf_full_swing.png` | Validation. io_buf clean full transition, silicon vs HSPICE native IBIS vs pybis. Three independent routes to the same coefficients. | `results\full_swing_kukd_comparison_2026-08-27\01_io_buf_full_swing_kukd.png` |
| 2 | `02_validation_inv_chain_full_swing.png` | Validation, second buffer. Same comparison on inv_chain. | `results\full_swing_kukd_comparison_2026-08-27\02_inv_chain_full_swing_kukd.png` |
| 3 | `03_grid_artifact_io_buf_full_swing.png` | Why the earlier figures spiked. Union of the two fixture grids on the left, one uniform 5 ps grid on the right. Not a conditioning failure -- cond never exceeds 5.5. | `results\silicon_kukd_conditioning_2026-08-27\01_io_buf_full_transition.png` |
| 4 | `04_grid_artifact_io_buf_short_high_70.png` | The same artifact and the same fix on a reversal case. | `results\silicon_kukd_conditioning_2026-08-27\03_io_buf_short_high_70pct.png` |
| 5 | `05_reversal_io_buf_short_high_70.png` | Mid-reversal. io_buf short high 70%, silicon vs native IBIS vs gate-state. | `results\silicon_kukd_recovery_uniform_2026-08-27\plots\io_buf_short_high_70.png` |
| 6 | `06_reversal_io_buf_short_low_70.png` | Mid-reversal, opposite direction. The case where native IBIS departs from silicon most sharply. | `results\silicon_kukd_recovery_uniform_2026-08-27\plots\io_buf_short_low_70.png` |
| 7 | `07_reversal_inv_chain_short_high_50.png` | Mid-reversal. inv_chain short high 50%, where silicon produces no pulse at all. | `results\silicon_kukd_recovery_uniform_2026-08-27\plots\inv_chain_short_high_50.png` |
| 8 | `08_reversal_ex2_short_low_70.png` | Mid-reversal. ex2 short low 70%, the third buffer. | `results\silicon_kukd_recovery_uniform_2026-08-27\plots\ex2_short_low_70.png` |

## Model and native IBIS against silicon, post-reversal Ku

Time-weighted RMSE. From `recovery_vs_silicon.csv` in this folder.

| buffer | direction | target | gate-state | native IBIS |
|---|---|---:|---:|---:|
| io_buf | short high | 90% | 0.0279 | 0.0100 |
| io_buf | short high | 70% | 0.0617 | 0.0113 |
| io_buf | short high | 50% | 0.0269 | 0.0137 |
| io_buf | short low | 90% | 0.0347 | 0.3051 |
| io_buf | short low | 70% | 0.0565 | 0.3375 |
| io_buf | short low | 50% | 0.0999 | 0.2978 |
| inv_chain | short high | 90% | 0.0420 | 0.0691 |
| inv_chain | short high | 70% | 0.0071 | 0.0540 |
| inv_chain | short high | 50% | 0.0005 | 0.0506 |
| inv_chain | short low | 90% | 0.0731 | 0.0533 |
| inv_chain | short low | 70% | 0.1020 | 0.0707 |
| inv_chain | short low | 50% | 0.0972 | 0.0609 |
| ex2 | short high | 70% | 0.1187 | 0.1327 |
| ex2 | short high | 50% | 0.0958 | 0.0978 |
| ex2 | short low | 90% | 0.2593 | 0.2191 |
| ex2 | short low | 70% | 0.2619 | 0.1941 |
| ex2 | short low | 50% | 0.2514 | 0.1585 |
