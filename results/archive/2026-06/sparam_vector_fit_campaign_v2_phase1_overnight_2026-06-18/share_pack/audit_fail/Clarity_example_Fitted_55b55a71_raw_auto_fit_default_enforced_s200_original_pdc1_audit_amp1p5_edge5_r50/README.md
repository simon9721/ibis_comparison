# Clarity_example_Fitted_55b55a71 - audit_amp1p5_edge5_r50

- Candidate: `raw_auto_fit_default_enforced_s200_original_pdc1`
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
| `tx_active_rmse_v` | `0.005993640466458068` |
| `tx_active_maxabs_v` | `0.02659558469523582` |
| `rx_active_rmse_v` | `0.03644323717966242` |
| `rx_active_maxabs_v` | `0.18437255147055823` |
| `rx_minus_tx_rise50_ps_delta_ps` | `1.132150265481016` |
| `rx_minus_tx_fall50_ps_delta_ps` | `-47.374355184425376` |
| `hspice_threshold_delay_confidence` | `low` |
| `hspice_threshold_delay_confidence_reasons` | `hspice_rx_fall_threshold_ambiguous;ngspice_rx_fall_threshold_ambiguous` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
