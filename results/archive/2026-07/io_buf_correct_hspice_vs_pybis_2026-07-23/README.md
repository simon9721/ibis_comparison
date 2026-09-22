# Corrected HSPICE References versus pybis

## Setup

- Both pybis models were regenerated from `results\io_buf_fast_edge_retest_2026-06-05\source\io_buf.ibs`.
- Legacy baseline: `InputDriven`.
- Current best structural method: `InputDrivenTwoStateGateDirectionalResidualFull`.
- HSPICE native-IBIS and original-transistor references are reused from `results\io_buf_correct_hspice_reference_waveforms_2026-07-23`.
- No HSPICE simulations are rerun by this comparison script.
- Common runtime setup: 3.3 V, 1 ps command edges, ideal 3.3 V supply, 50 ohm || 2 pF.

## Headline Finding

- The directional-residual model fails the corrected-file offline reconstruction gate: worst RMSE `0.46428`, worst max error `0.69980`, verdict `FAIL`.
- Its inferred endpoint states are not settled logic states: `Ku off/on = 0.3116/0.3024` and `Kd off/on = 0.3827/0.7871`.
- Legacy pybis still reproduces the normal pad well: `38.4 mV` RMSE versus native IBIS and `37.0 mV` versus the transistor.
- Legacy pybis fails the 1 ns short-high pulse: it peaks at `0.901 V`, while corrected native IBIS and transistor references peak at `0.048 V` and `0.096 V`.
- In the 1 ns short-low case, legacy pybis follows the transistor pad much better than native IBIS does: `51.5 mV` RMSE and recovery only `+63.3 ps` from the transistor. Its Ku/Kd still disagree with native-IBIS playback, so this is transistor-pad agreement, not coefficient agreement.
- For 1 ns short-high, native-IBIS Ku/Kd RMSE is legacy `0.30011/0.31837` versus directional-residual `0.29005/0.34232`. These algorithm values are diagnostic only because the reconstruction gate failed.
- Directional-residual transient failures: `short_pulse_2ns_high (cached ngspice numeric failure: C:\Users\sh3qm\code\ibis_comparison\results\io_buf_correct_hspice_vs_pybis_2026-07-23\cases\short_pulse_2ns_high\ngspice_directional_residual)`.
- The transistor-reference pad score is reported independently. A pybis model can agree with native IBIS coefficients while still missing transistor history, or move toward transistor behavior while disagreeing with native table playback.

## Metrics

| Case | Flow | Pad RMSE vs native (mV) | Pad RMSE vs transistor (mV) | Ku RMSE vs native | Kd RMSE vs native |
|---|---|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | legacy | 38.433 | 37.042 | 0.28052 | 0.14874 |
| edge_1ps_base_50r_2pf | directional_residual | 838.292 | 841.758 | 0.48836 | 0.13562 |
| short_pulse_1ns_high | legacy | 248.174 | 244.478 | 0.30011 | 0.31837 |
| short_pulse_1ns_high | directional_residual | 384.874 | 385.687 | 0.29005 | 0.34232 |
| short_pulse_2ns_high | legacy | 128.638 | 109.334 | 0.18630 | 0.09651 |
| short_pulse_2ns_high | directional_residual | NUMERIC FAIL | NUMERIC FAIL | NUMERIC FAIL | NUMERIC FAIL |
| short_pulse_1ns_low | legacy | 366.059 | 51.522 | 0.45845 | 0.35703 |
| short_pulse_1ns_low | directional_residual | 922.672 | 842.429 | 0.56872 | 0.28487 |
| short_pulse_2ns_low | legacy | 240.784 | 46.127 | 0.32327 | 0.34355 |
| short_pulse_2ns_low | directional_residual | 881.757 | 818.744 | 0.52510 | 0.32612 |

## Figures

- `figures/algorithm_vs_correct_references_contact_sheet.png`
- `figures/fast_ibis_reconstruction_gate.png`
- `figures/<case>/01_all_flows_pad_overlay.png`
- `figures/<case>/02_algorithm_vs_hspice_native_ibis.png`
- `figures/<case>/03_algorithm_vs_hspice_transistor.png`
- `figures/<case>/04_legacy_vs_hspice_native_ibis.png`

## Numeric Data

- `comparison_metrics.csv`
- `fast_ibis_reconstruction_metrics.csv`
- `fast_ibis_reconstruction_summary.csv`
- `ngspice_run_manifest.csv`
- `model_manifest.csv`
- `cases/<case>/aligned_correct_references_vs_pybis.csv`

Each ngspice run retains its exact generated model, deck, raw output, and log.
