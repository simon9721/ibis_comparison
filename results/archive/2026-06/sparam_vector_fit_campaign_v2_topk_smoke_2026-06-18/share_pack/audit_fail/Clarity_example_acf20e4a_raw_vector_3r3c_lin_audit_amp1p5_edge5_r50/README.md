# Clarity_example_acf20e4a - audit_amp1p5_edge5_r50

- Candidate: `raw_vector_3r3c_lin`
- Independent class: `PASS`
- HSPICE audit: `FAIL`
- RX audit: `FAIL`
- TX/reflection audit: `PASS`
- Edge: `5.0 ps`

## Key Figures

- `figures/rx_overlay.png`
- `figures/tx_overlay.png`
- `figures/hspice_ngspice_two_panel.png`
- `figures/frequency_fit.png`
- `figures/passivity.png`

## Metrics

| Metric | Value |
| --- | --- |
| `hspice_audit_class` | `FAIL` |
| `hspice_audit_reason` | `rx_active_rmse;rx_active_maxabs` |
| `rx_hspice_audit_class` | `FAIL` |
| `rx_hspice_audit_reason` | `rx_active_rmse;rx_active_maxabs` |
| `reflection_hspice_audit_class` | `PASS` |
| `reflection_hspice_audit_reason` | `reflection/TX thresholds passed` |
| `rx_shape_hspice_audit_class` | `FAIL` |
| `rx_timing_hspice_audit_class` | `WARN` |
| `tx_active_rmse_v` | `0.00817599378505233` |
| `tx_active_maxabs_v` | `0.0412880031643318` |
| `rx_active_rmse_v` | `0.04715127710963358` |
| `rx_active_maxabs_v` | `0.19666711928883485` |
| `rx_minus_tx_rise50_ps_delta_ps` | `-2.1501319666864447` |
| `rx_minus_tx_fall50_ps_delta_ps` | `-47.329643394227006` |
| `hspice_threshold_delay_confidence` | `low` |
| `hspice_threshold_delay_confidence_reasons` | `hspice_rx_fall_threshold_ambiguous;ngspice_rx_fall_threshold_ambiguous` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
