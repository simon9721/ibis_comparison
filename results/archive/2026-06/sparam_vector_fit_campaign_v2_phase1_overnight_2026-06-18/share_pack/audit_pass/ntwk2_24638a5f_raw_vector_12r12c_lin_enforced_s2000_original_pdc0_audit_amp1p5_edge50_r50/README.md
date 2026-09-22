# ntwk2_24638a5f - audit_amp1p5_edge50_r50

- Candidate: `raw_vector_12r12c_lin_enforced_s2000_original_pdc0`
- Independent class: `PASS`
- HSPICE audit: `PASS`
- RX audit: `PASS`
- TX/reflection audit: `PASS`
- Edge: `50.0 ps`

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
| `tx_active_rmse_v` | `0.001995559690269802` |
| `tx_active_maxabs_v` | `0.010903646477603217` |
| `rx_active_rmse_v` | `0.0007341900024847365` |
| `rx_active_maxabs_v` | `0.0072292772939278604` |
| `rx_minus_tx_rise50_ps_delta_ps` | `0.03995507414313337` |
| `rx_minus_tx_fall50_ps_delta_ps` | `-0.03847712066636788` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
