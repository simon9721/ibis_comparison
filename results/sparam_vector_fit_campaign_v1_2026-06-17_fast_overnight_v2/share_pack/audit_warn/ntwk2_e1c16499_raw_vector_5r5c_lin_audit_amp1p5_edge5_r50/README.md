# ntwk2_e1c16499 - audit_amp1p5_edge5_r50

- Candidate: `raw_vector_5r5c_lin`
- Independent class: `WARN`
- HSPICE audit: `WARN`
- RX audit: `WARN`
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
| `hspice_audit_class` | `WARN` |
| `hspice_audit_reason` | `voltage_pass_threshold_delay_confidence_low` |
| `rx_hspice_audit_class` | `WARN` |
| `rx_hspice_audit_reason` | `rx_timing_threshold_confidence_low` |
| `reflection_hspice_audit_class` | `PASS` |
| `reflection_hspice_audit_reason` | `reflection/TX thresholds passed` |
| `rx_shape_hspice_audit_class` | `PASS` |
| `rx_timing_hspice_audit_class` | `WARN` |
| `tx_active_rmse_v` | `0.0063788118755886865` |
| `tx_active_maxabs_v` | `0.10722162515381473` |
| `rx_active_rmse_v` | `0.0026082522052489863` |
| `rx_active_maxabs_v` | `0.041676983636416254` |
| `rx_minus_tx_rise50_ps_delta_ps` | `1.7680960624712876` |
| `rx_minus_tx_fall50_ps_delta_ps` | `1.6796108850824876` |
| `hspice_threshold_delay_confidence` | `low` |
| `hspice_threshold_delay_confidence_reasons` | `ngspice_tx_fall_threshold_ambiguous;ngspice_tx_rise_threshold_ambiguous` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
