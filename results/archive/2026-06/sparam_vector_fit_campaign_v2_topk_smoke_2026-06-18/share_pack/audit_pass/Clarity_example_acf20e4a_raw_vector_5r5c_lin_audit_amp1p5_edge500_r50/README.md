# Clarity_example_acf20e4a - audit_amp1p5_edge500_r50

- Candidate: `raw_vector_5r5c_lin`
- Independent class: `FAIL`
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
| `tx_active_rmse_v` | `0.002914323652228344` |
| `tx_active_maxabs_v` | `0.008175083234193511` |
| `rx_active_rmse_v` | `0.006302707238465843` |
| `rx_active_maxabs_v` | `0.020754405004519916` |
| `rx_minus_tx_rise50_ps_delta_ps` | `-16.390841981336166` |
| `rx_minus_tx_fall50_ps_delta_ps` | `-13.375842054395605` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
