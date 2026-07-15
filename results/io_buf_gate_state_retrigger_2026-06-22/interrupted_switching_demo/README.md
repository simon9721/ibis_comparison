# io_buf Gate-State pybis Retrigger Study

This study tests an opt-in transistor-like `InputDrivenGateStateHybrid` mode against HSPICE native IBIS, legacy pybis, and the current short-pulse hybrid.

## Headline

- Long-pulse control pad RMSE delta versus legacy: `3.904 mV`.
- Long-pulse control max Ku/Kd RMSE delta versus legacy: `0.00462`.
- GateStateHybrid coefficient-first improvements versus legacy: `2` / `3` short-pulse cases.
- GateStateHybrid coefficient-first improvements versus ShortPulseHybrid: `0` / `3` short-pulse cases.
- `InputDrivenGateStateFull` is diagnostic only and is not considered for default behavior.

## short_pulse_1ns_high Specific Numbers

- HSPICE Ku peak: `0.0746`
- legacy Ku peak: `1.0125`
- ShortPulseHybrid Ku peak: `0.3606`
- GateStateHybrid Ku peak: `0.0586`
- GateStateFull Ku peak: `0.0586`
- HSPICE pad peak: `0.0616 V`
- legacy pad peak: `1.5155 V`
- ShortPulseHybrid pad peak: `0.2185 V`
- GateStateHybrid pad peak: `0.0802 V`

## Short-Pulse Metric Table

| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum | Overlap ns |
|---|---|---:|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | legacy pybis | 678.863 | 0.5024 | 0.5785 | 1.0125 | -0.0717 | 0.0116 |
| short_pulse_500ps_high | ShortPulseHybrid | 47.575 | 0.0783 | 0.4926 | 0.2025 | 0.1233 | 0.1194 |
| short_pulse_500ps_high | GateStateHybrid | 11.746 | 0.0138 | 0.6267 | 0.0195 | 0.0036 | 0.0032 |
| short_pulse_500ps_high | GateStateFull | 24.477 | 0.0142 | 0.6277 | 0.0515 | 0.0022 | 0.0063 |
| short_pulse_1ns_high | legacy pybis | 653.256 | 0.4704 | 0.5038 | 1.0125 | -0.0718 | 0.0113 |
| short_pulse_1ns_high | ShortPulseHybrid | 87.890 | 0.1279 | 0.3699 | 0.3606 | 0.0168 | 0.1871 |
| short_pulse_1ns_high | GateStateHybrid | 29.648 | 0.0312 | 0.4887 | 0.0586 | 0.0025 | 0.0067 |
| short_pulse_1ns_high | GateStateFull | 28.905 | 0.0272 | 0.4899 | 0.0586 | 0.0013 | 0.0088 |
| short_pulse_2ns_high | legacy pybis | 361.362 | 0.2833 | 0.2314 | 1.0125 | -0.0724 | 0.0463 |
| short_pulse_2ns_high | ShortPulseHybrid | 116.976 | 0.0874 | 0.1608 | 0.5906 | 0.0013 | 0.0528 |
| short_pulse_2ns_high | GateStateHybrid | 62.113 | 0.0549 | 0.2261 | 0.5660 | 0.0011 | 0.0417 |
| short_pulse_2ns_high | GateStateFull | 63.717 | 0.0604 | 0.2277 | 0.5650 | 0.0012 | 0.0206 |

## Figures

- `figures/*_01_input_pad_overlay.png`: input plus pad overlay.
- `figures/*_02_ku_only.png`: Ku-only comparison.
- `figures/*_02_kd_only.png`: Kd-only comparison.
- `figures/*_03_gate_state_diagnostics.png`: GUP/GDN, KUGATE/KDGATE, and targets.
- `figures/*_04_pad_consequence.png`: mismatch area for ShortPulseHybrid versus GateStateHybrid.
- `figures/control_vs_interrupted.png`: long-pulse preservation check.
- `figures/short_pulse_summary_bars.png`: metrics and overlap energy.

## Interpretation

A real improvement requires better coefficient agreement, not just lower pad RMSE.
The gate-state model remains experimental unless it preserves the long-pulse control and beats the current ShortPulseHybrid on Ku, Kd, and pad metrics.
