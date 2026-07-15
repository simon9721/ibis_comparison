# io_buf Coefficient-State pybis Retrigger Study

This study compares HSPICE native IBIS against two ngspice pybis models:

- Legacy `InputDriven`: edge restarts evaluate Ku/Kd from elapsed time since the latest input edge.
- Experimental `InputDrivenCoeffState`: Ku/Kd are independent continuous coefficient states driven by fitted delayed branch states derived from the IBIS coefficient tables.

## Headline

- Completed cases: `13` / `13`.
- Complete-edge regressions: `9`.
- Short-pulse coefficient-first passes: `3` / `3`.
- Pad-only false passes: `0`.
- Current conclusion: `InputDrivenCoeffState` is useful as an experimental short-pulse demo, but it is not default-ready because complete edges regress versus legacy pybis.

## Outputs

- `metrics_by_case.csv`
- `legacy_vs_coeff_state_summary.csv`
- `plots/summary_pad_rmse_legacy_vs_coeff_state.png`
- `plots/cases/*_legacy_vs_coeff_state.png`
- `common/legacy/driver_OutputInput_Typical.sub`
- `common/coeff_state/driver_OutputInput_Typical.sub`

## Case Summary

| Case | Kind | Legacy | Coeff | Legacy pad RMSE mV | Coeff pad RMSE mV | Legacy Ku/Kd RMSE | Coeff Ku/Kd RMSE | Pad reduction % | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| edge_1ps_base_50r_2pf | complete_edge | GOOD | CHECK | 5.289 | 150.744 | 0.006 | 0.186 | -2750.0 | REGRESSION |
| edge_5ps_50r_2pf | complete_edge | WARN | CHECK | 7.934 | 153.598 | 0.021 | 0.187 | -1835.9 | REGRESSION |
| edge_50ps_50r_2pf | complete_edge | WARN | CHECK | 11.375 | 144.285 | 0.015 | 0.183 | -1168.5 | REGRESSION |
| edge_500ps_50r_2pf | complete_edge | CHECK | CHECK | 134.834 | 181.185 | 0.132 | 0.203 | -34.4 | REGRESSION |
| edge_2ns_50r_2pf | complete_edge | CHECK | CHECK | 393.169 | 360.724 | 0.336 | 0.301 | 8.3 | PASS |
| load_25r_2pf | complete_edge | GOOD | CHECK | 3.223 | 99.044 | 0.005 | 0.166 | -2972.7 | REGRESSION |
| load_50r_0pf | complete_edge | GOOD | CHECK | 5.770 | 168.889 | 0.006 | 0.164 | -2827.0 | REGRESSION |
| load_50r_10pf | complete_edge | GOOD | CHECK | 4.543 | 121.042 | 0.005 | 0.155 | -2564.5 | REGRESSION |
| load_100r_2pf | complete_edge | GOOD | CHECK | 8.922 | 208.140 | 0.005 | 0.185 | -2233.0 | REGRESSION |
| double_toggle_1ps | complete_edge | GOOD | CHECK | 5.713 | 165.252 | 0.006 | 0.186 | -2792.5 | REGRESSION |
| short_pulse_2ns_high | short_pulse | CHECK | CHECK | 361.362 | 204.205 | 0.283 | 0.162 | 43.5 | PASS |
| short_pulse_1ns_high | short_pulse | CHECK | CHECK | 653.256 | 98.161 | 0.504 | 0.370 | 85.0 | PASS |
| short_pulse_500ps_high | short_pulse | CHECK | CHECK | 678.863 | 47.719 | 0.578 | 0.493 | 93.0 | PASS |

## Interpretation Guide

`PASS` for complete-edge cases means the coefficient-state model did not materially regress normal edges.
`PASS` for short-pulse cases requires pad improvement and both Ku and Kd RMSE improvement versus legacy pybis.
`FALSE_PASS_PAD_ONLY` means the pad waveform improved but at least one coefficient got worse, so the model is not physically accepted.
This is still experimental; it should not replace the default `InputDriven` mode unless it preserves normal-edge behavior and improves interrupted transitions for the right coefficient-state reason.
