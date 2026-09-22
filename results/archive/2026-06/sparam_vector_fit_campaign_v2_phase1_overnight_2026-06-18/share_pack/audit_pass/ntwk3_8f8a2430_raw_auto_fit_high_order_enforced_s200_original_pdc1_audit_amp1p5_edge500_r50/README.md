# ntwk3_8f8a2430 - audit_amp1p5_edge500_r50

- Candidate: `raw_auto_fit_high_order_enforced_s200_original_pdc1`
- Independent class: `PASS`
- HSPICE audit: `PASS`
- RX audit: `PASS`
- TX/reflection audit: `PASS`
- Edge: `500.0 ps`

## Key Figures

- `figures/rx_overlay.png`
- `figures/tx_overlay.png`
- `figures/hspice_ngspice_two_panel.png`
- `figures/frequency_fit.png`
- `figures/passivity.png`

## Metrics

| Metric | Value |
| --- | --- |
| `hspice_audit_class` | `PASS` |
| `hspice_audit_reason` | `thresholds passed` |
| `rx_hspice_audit_class` | `PASS` |
| `rx_hspice_audit_reason` | `rx shape and timing thresholds passed` |
| `reflection_hspice_audit_class` | `PASS` |
| `reflection_hspice_audit_reason` | `reflection/TX thresholds passed` |
| `rx_shape_hspice_audit_class` | `PASS` |
| `rx_timing_hspice_audit_class` | `PASS` |
| `tx_active_rmse_v` | `3.379243517663624e-05` |
| `tx_active_maxabs_v` | `0.0002053206307986999` |
| `rx_active_rmse_v` | `0.00028418940792192276` |
| `rx_active_maxabs_v` | `0.0010072704439466618` |
| `rx_minus_tx_rise50_ps_delta_ps` | `-0.0526041690947352` |
| `rx_minus_tx_fall50_ps_delta_ps` | `0.17460942524768797` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
