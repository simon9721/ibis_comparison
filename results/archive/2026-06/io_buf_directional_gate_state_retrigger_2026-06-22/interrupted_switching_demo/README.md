# io_buf Directional Gate-State pybis Retrigger Study

This study tests `InputDrivenDirectionalGateStateHybrid`, which splits interrupted switching into Ku turn-on, Ku turn-off, Kd turn-off, and Kd turn-on states.

## Headline

- Long-pulse control pad RMSE delta versus legacy: `3.962 mV`.
- Long-pulse control max Ku/Kd RMSE delta versus legacy: `0.00477`.
- Directional coefficient-first improvements versus legacy: `2` / `6` interrupted cases.
- Directional Kd RMSE improvements versus GateStateHybrid: `2` / `6` interrupted cases.
- Directional all-metric improvements versus GateStateHybrid: `2` / `6` interrupted cases.
- `InputDrivenDirectionalGateStateFull` is diagnostic only and is not considered for default behavior.

## short_pulse_1ns_high Specific Numbers

- HSPICE Ku peak: `0.0746`
- legacy Ku peak: `1.0125`
- ShortPulseHybrid Ku peak: `0.3606`
- GateStateHybrid Ku peak: `0.0586`
- DirectionalGateStateHybrid Ku peak: `0.0440`

## Interrupted-Pulse Metric Table

| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum | Kd rec. delta ns | Overlap ns |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | legacy pybis | 678.863 | 0.5024 | 0.5785 | 1.0125 | -0.0717 | 2.9287 | 0.0116 |
| short_pulse_500ps_high | ShortPulseHybrid | 47.575 | 0.0783 | 0.4926 | 0.2025 | 0.1233 | 0.0000 | 0.1194 |
| short_pulse_500ps_high | GateStateHybrid | 11.746 | 0.0138 | 0.6267 | 0.0195 | 0.0036 | 0.0000 | 0.0032 |
| short_pulse_500ps_high | DirectionalGateStateHybrid | 375.059 | 0.3923 | 0.6271 | 0.0151 | -0.0052 | 0.0000 | 0.0010 |
| short_pulse_500ps_high | DirectionalGateStateFull | 374.298 | 0.3881 | 0.6305 | 0.0019 | -0.0159 | 0.0000 | 0.0018 |
| short_pulse_1ns_high | legacy pybis | 653.256 | 0.4704 | 0.5038 | 1.0125 | -0.0718 | 2.9119 | 0.0113 |
| short_pulse_1ns_high | ShortPulseHybrid | 87.890 | 0.1279 | 0.3699 | 0.3606 | 0.0168 | 0.0000 | 0.1871 |
| short_pulse_1ns_high | GateStateHybrid | 29.648 | 0.0312 | 0.4887 | 0.0586 | 0.0025 | 0.0000 | 0.0067 |
| short_pulse_1ns_high | DirectionalGateStateHybrid | 289.346 | 0.2288 | 0.5026 | 0.0440 | -0.0448 | 0.0000 | 0.0116 |
| short_pulse_1ns_high | DirectionalGateStateFull | 279.978 | 0.2178 | 0.5063 | 0.0465 | -0.0580 | 0.0000 | 0.0198 |
| short_pulse_2ns_high | legacy pybis | 361.362 | 0.2833 | 0.2314 | 1.0125 | -0.0724 | 0.3502 | 0.0463 |
| short_pulse_2ns_high | ShortPulseHybrid | 116.976 | 0.0874 | 0.1608 | 0.5906 | 0.0013 | 2.2329 | 0.0528 |
| short_pulse_2ns_high | GateStateHybrid | 62.113 | 0.0549 | 0.2261 | 0.5660 | 0.0011 | 0.3835 | 0.0417 |
| short_pulse_2ns_high | DirectionalGateStateHybrid | 115.571 | 0.0828 | 0.2546 | 0.5249 | -0.0515 | 0.6168 | 0.0525 |
| short_pulse_2ns_high | DirectionalGateStateFull | 111.428 | 0.0792 | 0.2625 | 0.5396 | -0.0732 | 0.6502 | 0.0592 |
| short_pulse_500ps_low | legacy pybis | 680.819 | 0.5231 | 0.7421 | 1.0102 | -0.0285 | 1.9365 | 0.0458 |
| short_pulse_500ps_low | ShortPulseHybrid | 680.645 | 0.4982 | 0.7198 | 1.0103 | -0.0285 | 1.9365 | 0.0463 |
| short_pulse_500ps_low | GateStateHybrid | 678.167 | 0.4861 | 0.7089 | 1.0095 | -0.0281 | 0.0000 | 0.0482 |
| short_pulse_500ps_low | DirectionalGateStateHybrid | 677.864 | 0.4861 | 0.7089 | 1.0095 | -0.0281 | 0.0000 | 0.0482 |
| short_pulse_500ps_low | DirectionalGateStateFull | 290.570 | 0.3670 | 0.2751 | 1.0209 | -0.9615 | 0.0000 | 0.0022 |
| short_pulse_1ns_low | legacy pybis | 508.684 | 0.4054 | 0.6550 | 1.0102 | -0.0718 | 1.9430 | 0.0455 |
| short_pulse_1ns_low | ShortPulseHybrid | 507.889 | 0.4048 | 0.6308 | 1.0103 | -0.0718 | 1.9430 | 0.0461 |
| short_pulse_1ns_low | GateStateHybrid | 509.035 | 0.4055 | 0.6177 | 1.0095 | -0.0719 | 0.0000 | 0.0462 |
| short_pulse_1ns_low | DirectionalGateStateHybrid | 509.144 | 0.4055 | 0.6178 | 1.0095 | -0.0719 | 0.0000 | 0.0462 |
| short_pulse_1ns_low | DirectionalGateStateFull | 403.744 | 0.3679 | 0.0600 | 1.0209 | -0.2352 | 0.0000 | 0.0000 |
| short_pulse_2ns_low | legacy pybis | 18.888 | 0.0210 | 0.3617 | 1.0102 | -0.0718 | 1.9225 | 0.0461 |
| short_pulse_2ns_low | ShortPulseHybrid | 18.965 | 0.0210 | 0.3348 | 1.0103 | -0.0718 | 1.9225 | 0.0460 |
| short_pulse_2ns_low | GateStateHybrid | 20.469 | 0.0216 | 0.3211 | 1.0095 | -0.0719 | 0.0000 | 0.0461 |
| short_pulse_2ns_low | DirectionalGateStateHybrid | 20.417 | 0.0216 | 0.3211 | 1.0095 | -0.0719 | 0.0000 | 0.0461 |
| short_pulse_2ns_low | DirectionalGateStateFull | 87.776 | 0.0553 | 0.0483 | 1.0209 | -0.0786 | 0.0000 | 0.0945 |

## Figures

- `figures/*_01_input_pad_overlay.png`: input plus pad overlay.
- `figures/*_02_ku_only.png`: Ku-only comparison.
- `figures/*_02_kd_only.png`: Kd-only comparison.
- `figures/*_03_directional_state_diagnostics.png`: KU_ON/KU_OFF/KD_OFF/KD_ON and composed KUDIR/KDDIR.
- `figures/*_04_alignment_diagnostics.png`: fall-after-rise / rise-after-fall detectors and HALIGN blend.
- `figures/high_vs_low_pulse_comparison.png`: mirrored interruption-direction comparison.
- `figures/short_pulse_summary_bars.png`: summary metrics and overlap energy.

## Interpretation

A real pass requires Ku, Kd, and pad agreement. Lower pad RMSE alone is not enough.
The directional model remains experimental unless it preserves the long-pulse control and improves Kd recovery versus the previous GateStateHybrid.
