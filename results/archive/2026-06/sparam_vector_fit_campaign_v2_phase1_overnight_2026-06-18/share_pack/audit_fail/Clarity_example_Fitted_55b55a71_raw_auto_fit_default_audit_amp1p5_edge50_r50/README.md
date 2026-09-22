# Clarity_example_Fitted_55b55a71 - audit_amp1p5_edge50_r50

- Candidate: `raw_auto_fit_default`
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
| `tx_active_rmse_v` | `0.005336385581980265` |
| `tx_active_maxabs_v` | `0.02530901746738423` |
| `rx_active_rmse_v` | `0.04351635251838372` |
| `rx_active_maxabs_v` | `0.1562207123363185` |
| `rx_minus_tx_rise50_ps_delta_ps` | `6.63141798306458` |
| `rx_minus_tx_fall50_ps_delta_ps` | `13.750614256048493` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
