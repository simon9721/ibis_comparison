# ntwk2_24638a5f - audit_amp1p5_edge500_r50

- Candidate: `raw_vector_12r12c_lin_enforced_s200_original_pdc1`
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
| `tx_active_rmse_v` | `0.0018300212671318367` |
| `tx_active_maxabs_v` | `0.0020728309627805475` |
| `rx_active_rmse_v` | `0.0006290716667706645` |
| `rx_active_maxabs_v` | `0.0008871362599679466` |
| `rx_minus_tx_rise50_ps_delta_ps` | `0.21332332218051953` |
| `rx_minus_tx_fall50_ps_delta_ps` | `-0.5468788315371995` |
| `hspice_threshold_delay_confidence` | `high` |

## Included Files

- `models/ngspice_vector_fit_model.sp`
- `inputs/`: original Touchstone
- `hspice/`: native S-element deck plus `.tr0`/`.lis`
- `ngspice/`: vector-fit testbench plus `.raw`/`.log`
