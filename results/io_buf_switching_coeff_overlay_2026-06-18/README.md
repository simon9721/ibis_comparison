# io_buf Switching Coefficient Overlay

This run compares the same `io_buf.ibs` through two flows:

- HSPICE native IBIS B-element with `xv_pu=ku` and `xv_pd=kd`.
- ngspice pybis2spice generated subcircuit with internal `V(xdrv.ku)` and `V(xdrv.kd)` nodes.

Both use a 0/3.3 V PWL rise-then-fall input and a simple 50 ohm + 2 pF pad load.

## Key Outputs

- `plots/00_waveform_and_switching_coefficients_overlay.png`
- `plots/01_pad_waveform_overlay.png`
- `plots/02_switching_coefficients_overlay.png`
- `plots/03_rise_transition_zoom.png`
- `plots/03_fall_transition_zoom.png`
- `metrics_summary.csv`
- `aligned_waveforms.csv`

## Metrics

| Quantity | RMSE | Max abs |
|---|---:|---:|
| pad_voltage_active_window_v | 0.00525595 | 0.0167802 |
| ku_active_window | 0.00435967 | 0.0229404 |
| kd_active_window | 0.00536396 | 0.0228917 |
| ku_full | 0.00443118 | 0.0229404 |
| kd_full | 0.00481116 | 0.0228917 |

## Notes

HSPICE's coefficients are the simulator's internal IBIS switching functions exposed through `xv_pu/xv_pd`.
The pybis coefficients are the free-spice subcircuit's generated waveform coefficient nodes.
Small timing differences are expected because HSPICE owns the native IBIS state machine, while pybis approximates it with explicit behavioral sources.
