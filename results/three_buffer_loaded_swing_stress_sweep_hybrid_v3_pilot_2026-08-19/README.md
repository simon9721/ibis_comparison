# Three-Buffer Loaded-Swing Stress Sweep With Hybrid

This is a separate extension of the August 14 loaded-swing sweep. It reuses the exact cached HSPICE native-IBIS, HSPICE transistor, and full gate-state waveforms, then runs only the dual-residual hybrid in ngspice.

Baseline source: `results\three_buffer_loaded_swing_stress_sweep_2026-08-14`
Hybrid mode: `InputDrivenHybridV3AlignedReplay`

## Coverage

- Hybrid simulations completed: `6/6`.
- Hybrid detector activated: `6/6` cases.
- Hybrid path-switch discontinuity above 0.10: `0/6` cases.
- Hybrid improved versus full gate-state: pad `2/6`, Ku `2/6`, Kd `2/6`.
- Overall verdict: the present hybrid is diagnostic, not validated. It contains some full-model errors, but its hard path switch creates coefficient jumps and it regresses the strongest `ex2` short-high result.

## Aggregate Results

| Buffer | Direction | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Post-reverse SSE | Triggered |
|---|---|---|---:|---:|---:|---:|---:|
| ex2 | short high | gate_state | 31.36 mV | 0.0796 | 0.0546 | 99.2% | 0/1 |
| ex2 | short high | hybrid | 590.98 mV | 0.5051 | 0.7157 | 99.9% | 1/1 |
| ex2 | short low | gate_state | 261.78 mV | 0.2831 | 0.1776 | 100.0% | 0/1 |
| ex2 | short low | hybrid | 912.41 mV | 0.6544 | 0.2626 | 100.0% | 1/1 |
| inv_chain | short high | gate_state | 358.20 mV | 0.3569 | 0.3018 | 100.0% | 0/1 |
| inv_chain | short high | hybrid | 635.36 mV | 0.5760 | 0.7165 | 100.0% | 1/1 |
| inv_chain | short low | gate_state | 371.00 mV | 0.4825 | 0.3640 | 100.0% | 0/1 |
| inv_chain | short low | hybrid | 909.47 mV | 0.6060 | 0.3531 | 100.0% | 1/1 |
| io_buf | short high | gate_state | 647.31 mV | 0.4071 | 0.3327 | 78.8% | 0/1 |
| io_buf | short high | hybrid | 28.80 mV | 0.1292 | 0.3935 | 86.3% | 1/1 |
| io_buf | short low | gate_state | 534.37 mV | 0.7857 | 0.5612 | 38.0% | 0/1 |
| io_buf | short low | hybrid | 250.32 mV | 0.6815 | 0.3715 | 12.3% | 1/1 |

## Files

- `comparison_metrics.csv`: active-window pad/Ku/Kd errors for full gate-state and hybrid.
- `coefficient_diagnostics.csv`: before/after-reverse coefficient errors, extrema, reverse-edge values, and hybrid activation intervals.
- `summary_by_device_direction.csv`: aggregate trends and stress correlation.
- `KUKD_ANALYSIS.md`: detailed native-IBIS, gate-state, and hybrid interpretation.
- `analysis_plots/`: stress trends, pre/post-reversal split, and hybrid switch-jump evidence.
- `figures/<buffer>/<direction>/swing_<target>/`: two clean figures plus aligned numeric waveforms.
- `all_figures_flat/`: presentation-friendly copies of all figures.
- `ngspice_runs/`: hybrid decks, raw files, and logs.

No HSPICE simulation was launched by this runner.
