# Three-Buffer Loaded-Swing Stress Sweep With Hybrid

This pilot reuses cached HSPICE/native-IBIS, transistor, and full gate-state references and runs only the corrected V3 aligned-replay candidate in ngspice.

Baseline source: `results\three_buffer_loaded_swing_stress_sweep_2026-08-14`
Hybrid mode: `InputDrivenHybridV3AlignedReplay`

## Coverage

- Hybrid simulations completed: `6/6`.
- Hybrid detector activated: `6/6` cases.
- Hybrid path-switch discontinuity above 0.10: `0/6` cases.
- Entry handoff within 0.02: `6/6` cases.
- Hybrid improved versus full gate-state: pad `2/6`, Ku `2/6`, Kd `2/6`.
- Overall verdict: V3 fixes the replay handoff structurally (6/6 entries within 0.02), but it improves pad/Ku/Kd versus full gate-state in only pad 2/6, Ku 2/6, and Kd 2/6 cases. The opposite full-transition tables do not predict interrupted recovery generally, so V3 is not promoted to the full stress sweep.

## Aggregate Results

| Buffer | Direction | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Post-reverse SSE | Triggered |
|---|---|---|---:|---:|---:|---:|---:|
| ex2 | short high | gate_state | 31.36 mV | 0.0796 | 0.0546 | 99.2% | 0/1 |
| ex2 | short high | hybrid | 590.17 mV | 0.5029 | 0.7059 | 99.9% | 1/1 |
| ex2 | short low | gate_state | 261.78 mV | 0.2831 | 0.1776 | 100.0% | 0/1 |
| ex2 | short low | hybrid | 914.95 mV | 0.6620 | 0.2597 | 100.0% | 1/1 |
| inv_chain | short high | gate_state | 358.20 mV | 0.3569 | 0.3018 | 100.0% | 0/1 |
| inv_chain | short high | hybrid | 635.35 mV | 0.5759 | 0.7165 | 100.0% | 1/1 |
| inv_chain | short low | gate_state | 371.00 mV | 0.4825 | 0.3640 | 100.0% | 0/1 |
| inv_chain | short low | hybrid | 909.36 mV | 0.6060 | 0.3530 | 100.0% | 1/1 |
| io_buf | short high | gate_state | 647.31 mV | 0.4071 | 0.3327 | 78.8% | 0/1 |
| io_buf | short high | hybrid | 27.16 mV | 0.1353 | 0.3820 | 85.7% | 1/1 |
| io_buf | short low | gate_state | 534.37 mV | 0.7857 | 0.5612 | 38.0% | 0/1 |
| io_buf | short low | hybrid | 259.63 mV | 0.6844 | 0.3716 | 12.8% | 1/1 |

## Files

- `comparison_metrics.csv`: active-window pad/Ku/Kd errors for full gate-state and hybrid.
- `coefficient_diagnostics.csv`: before/after-reverse coefficient errors, extrema, reverse-edge values, and hybrid activation intervals.
- `v3_structural_diagnostics.csv`: V3 anchors, independent table starts, timer monotonicity, handoff continuity, and active coefficient range.
- `summary_by_device_direction.csv`: aggregate trends and stress correlation.
- `KUKD_ANALYSIS.md`: detailed native-IBIS, gate-state, and hybrid interpretation.
- `analysis_plots/`: stress trends, pre/post-reversal split, and hybrid switch-jump evidence.
- `figures/<buffer>/<direction>/swing_<target>/`: two clean figures plus aligned numeric waveforms.
- `all_figures_flat/`: presentation-friendly copies of all figures.
- `ngspice_runs/`: hybrid decks, raw files, and logs.

No HSPICE simulation was launched by this runner.
