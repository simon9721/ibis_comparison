# ntwk3_8f8a2430 - audit_amp1p5_edge50_r50

- Candidate: `raw_vector_5r5c_log`
- Independent class: `FAIL`
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
| `tx_active_rmse_v` | `0.00018432148774199597` |
| `tx_active_maxabs_v` | `0.0016938135230757656` |
| `rx_active_rmse_v` | `0.000795654531238877` |
| `rx_active_maxabs_v` | `0.0077662930839682565` |
| `rx_minus_tx_rise50_ps_delta_ps` | `0.25136153828414187` |
| `rx_minus_tx_fall50_ps_delta_ps` | `0.3463168324401078` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
