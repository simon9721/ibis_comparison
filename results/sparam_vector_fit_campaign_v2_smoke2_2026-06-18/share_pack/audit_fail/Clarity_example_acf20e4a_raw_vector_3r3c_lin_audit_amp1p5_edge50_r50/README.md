# Clarity_example_acf20e4a - audit_amp1p5_edge50_r50

- Candidate: `raw_vector_3r3c_lin`
- Independent class: `WARN`
- HSPICE audit: `FAIL`
- RX audit: `FAIL`
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
| `hspice_audit_class` | `FAIL` |
| `hspice_audit_reason` | `rx_active_rmse;rx_active_maxabs` |
| `rx_hspice_audit_class` | `FAIL` |
| `rx_hspice_audit_reason` | `rx_active_rmse;rx_active_maxabs` |
| `reflection_hspice_audit_class` | `PASS` |
| `reflection_hspice_audit_reason` | `reflection/TX thresholds passed` |
| `rx_shape_hspice_audit_class` | `FAIL` |
| `rx_timing_hspice_audit_class` | `PASS` |
| `tx_active_rmse_v` | `0.006649356387560488` |
| `tx_active_maxabs_v` | `0.02053560172787031` |
| `rx_active_rmse_v` | `0.023348112314136974` |
| `rx_active_maxabs_v` | `0.09833911188892541` |
| `rx_minus_tx_rise50_ps_delta_ps` | `5.995394239490622` |
| `rx_minus_tx_fall50_ps_delta_ps` | `16.75815892775796` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
