# Three-Buffer Loaded-Swing Stress Sweep With Hybrid

This is a separate extension of the August 14 loaded-swing sweep. It reuses the exact cached HSPICE native-IBIS, HSPICE transistor, and full gate-state waveforms, then runs only the selected hybrid in ngspice.

Baseline source: `results\three_buffer_loaded_swing_stress_sweep_2026-08-14`
Hybrid mode: `InputDrivenTwoStateGateDirectionalDualResidualHybrid`

## Coverage

- Hybrid simulations completed: `30/30`.
- Hybrid detector activated: `30/30` cases.
- Hybrid path-switch discontinuity above 0.10: `17/30` cases.
- Entry handoff within 0.02: `10/30` cases.
- Hybrid improved versus full gate-state: pad `15/30`, Ku `20/30`, Kd `18/30`.
- Overall verdict: The present hybrid is diagnostic, not validated. It contains some full-model errors and regresses the strongest `ex2` short-high result.

## Aggregate Results

| Buffer | Direction | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Post-reverse SSE | Triggered |
|---|---|---|---:|---:|---:|---:|---:|
| ex2 | short high | gate_state | 35.15 mV | 0.0868 | 0.0567 | 97.2% | 0/5 |
| ex2 | short high | hybrid | 57.26 mV | 0.1090 | 0.0821 | 95.6% | 5/5 |
| ex2 | short low | gate_state | 185.33 mV | 0.2185 | 0.1474 | 99.9% | 0/5 |
| ex2 | short low | hybrid | 185.54 mV | 0.2110 | 0.1580 | 99.7% | 5/5 |
| inv_chain | short high | gate_state | 342.94 mV | 0.3584 | 0.2985 | 100.0% | 0/5 |
| inv_chain | short high | hybrid | 342.93 mV | 0.3167 | 0.2891 | 100.0% | 5/5 |
| inv_chain | short low | gate_state | 370.82 mV | 0.4567 | 0.3722 | 100.0% | 0/5 |
| inv_chain | short low | hybrid | 363.65 mV | 0.4167 | 0.3264 | 100.0% | 5/5 |
| io_buf | short high | gate_state | 446.48 mV | 0.3945 | 0.2619 | 72.1% | 0/5 |
| io_buf | short high | hybrid | 193.16 mV | 0.3563 | 0.1600 | 84.3% | 5/5 |
| io_buf | short low | gate_state | 547.23 mV | 0.7925 | 0.5574 | 37.8% | 0/5 |
| io_buf | short low | hybrid | 561.86 mV | 0.7825 | 0.5524 | 41.4% | 5/5 |

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
