# io_buf Switching Coefficient Sweep

This study runs matched HSPICE native-IBIS and ngspice pybis testbenches while changing the input edge, input pattern, and pad load.

Both flows use the same canonical `hspice/sparam/io_buf.ibs`, the same PWL stimulus, the same 3.3 V rails, and the same pad load for each case.

## Flows

- HSPICE: native IBIS `B` element with `xv_pu=ku` and `xv_pd=kd`.
- ngspice: pybis-generated `driver_OutputInput_Typical.sub`, measured at `V(xdrv.ku)` and `V(xdrv.kd)`.

## Summary

- GOOD: 7
- WARN: 2
- CHECK: 3
- FAIL: 0

`GOOD` means pad active-window RMSE <= 10 mV and both Ku/Kd RMSE <= 0.01.
`WARN` means pad active-window RMSE <= 25 mV and both Ku/Kd RMSE <= 0.03.

## Main Findings

- Sharp, complete toggles match very well. The 1 ps baseline and the double-toggle case are both `GOOD`.
- Load variation alone is not the weak point. 25 ohm, 50 ohm, 100 ohm, 0 pF, 2 pF, and 10 pF cases all stay `GOOD` for 1 ps input edges.
- Slow input ramps expose a real difference in switching-state handling. 5 ps and 50 ps edges are still close enough to be `WARN`, but 500 ps and 2 ns edges become `CHECK`.
- Interrupted output transitions expose the largest difference. The 2 ns-high short pulse reverses before the pad has settled, and HSPICE native IBIS and pybis choose visibly different Ku/Kd trajectories.
- The 1.8 V input-high case is an exploratory threshold case. It remains numerically close here, but it should not be treated as a normal guaranteed-logic operation because it is below the model's nominal `Vinh=2 V`.

## Outputs

- `metrics_by_case.csv`
- `plots/summary_rmse_by_case.png`
- `plots/cases/*_waveform_coeff_overlay.png`
- `plots/cases/*_transition_*_zoom.png`
- `cases/<case>/hspice_native_ibis/`
- `cases/<case>/ngspice_pybis/`

## Case Metrics

| Case | Status | Pad RMSE (mV) | Pad max (mV) | Ku RMSE | Kd RMSE |
|---|---:|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | GOOD | 5.289 | 16.780 | 0.00434 | 0.00561 |
| edge_5ps_50r_2pf | WARN | 7.934 | 31.992 | 0.01531 | 0.02094 |
| edge_50ps_50r_2pf | WARN | 11.375 | 37.289 | 0.01032 | 0.01477 |
| edge_500ps_50r_2pf | CHECK | 134.834 | 480.983 | 0.10275 | 0.13166 |
| edge_2ns_50r_2pf | CHECK | 393.169 | 1366.543 | 0.28076 | 0.33645 |
| load_50r_0pf | GOOD | 5.770 | 18.854 | 0.00467 | 0.00577 |
| load_50r_10pf | GOOD | 4.543 | 9.644 | 0.00425 | 0.00495 |
| load_25r_2pf | GOOD | 3.223 | 8.991 | 0.00441 | 0.00531 |
| load_100r_2pf | GOOD | 8.922 | 20.231 | 0.00424 | 0.00517 |
| short_pulse_2ns_high | CHECK | 361.362 | 946.897 | 0.28330 | 0.23142 |
| double_toggle_1ps | GOOD | 5.713 | 15.836 | 0.00436 | 0.00558 |
| marginal_input_1p8_high | GOOD | 6.519 | 17.347 | 0.00489 | 0.00952 |

## Notes

The marginal 1.8 V input case is intentionally below the model's nominal `Vinh=2 V`, so it probes threshold handling rather than normal switching.
Small coefficient differences are expected because HSPICE owns the native IBIS state machine, while pybis expands the behavior into explicit free-SPICE sources.
The slow-edge and short-pulse `CHECK` cases should be treated as evidence that input-stimulus/state-machine behavior needs separate validation from normal fast-edge output loading.
