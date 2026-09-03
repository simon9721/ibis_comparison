# io_buf Short-Pulse Hybrid Retrigger Study

This study keeps legacy `InputDriven` as the default and tests an opt-in `InputDrivenShortPulseHybrid` mode only on interrupted high pulses.

## Headline

- Selected hybrid candidate: `hybrid_branch`.
- Long-pulse control pad RMSE delta versus legacy: `0.671 mV`.
- Long-pulse control max Ku/Kd RMSE delta versus legacy: `0.00131`.
- Short-pulse coefficient-first improvements versus legacy: `3` / `3`.
- Legacy pybis generation remains unchanged; hybrid circuitry is only present when `--subcircuit-type InputDrivenShortPulseHybrid*` is requested.

## short_pulse_1ns_high Specific Numbers

- HSPICE Ku peak: `0.0746`
- legacy Ku peak: `1.0125`
- CoeffState Ku peak: `0.3606`
- ShortPulseHybrid Ku peak: `0.3606`
- HSPICE pad peak: `0.0616 V`
- legacy pad peak: `1.5155 V`
- CoeffState pad peak: `0.2189 V`
- ShortPulseHybrid pad peak: `0.2185 V`

## Short-Pulse Metric Table

| Case | Flow | Pad RMSE mV | Ku RMSE | Kd RMSE | Ku peak | Kd minimum |
|---|---|---:|---:|---:|---:|---:|
| short_pulse_500ps_high | legacy pybis | 678.863 | 0.5024 | 0.5785 | 1.0125 | -0.0717 |
| short_pulse_500ps_high | CoeffState | 47.719 | 0.0787 | 0.4925 | 0.2027 | 0.1236 |
| short_pulse_500ps_high | ShortPulseHybrid | 47.575 | 0.0783 | 0.4926 | 0.2025 | 0.1233 |
| short_pulse_1ns_high | legacy pybis | 653.256 | 0.4704 | 0.5038 | 1.0125 | -0.0718 |
| short_pulse_1ns_high | CoeffState | 98.161 | 0.1439 | 0.3699 | 0.3606 | 0.0168 |
| short_pulse_1ns_high | ShortPulseHybrid | 87.890 | 0.1279 | 0.3699 | 0.3606 | 0.0168 |
| short_pulse_2ns_high | legacy pybis | 361.362 | 0.2833 | 0.2314 | 1.0125 | -0.0724 |
| short_pulse_2ns_high | CoeffState | 204.205 | 0.1624 | 0.1622 | 0.5906 | 0.0013 |
| short_pulse_2ns_high | ShortPulseHybrid | 116.976 | 0.0874 | 0.1608 | 0.5906 | 0.0013 |

## Candidate Selection

| Candidate | Mean short pad RMSE mV | Mean short Ku RMSE | Mean short Kd RMSE | Control pad delta mV | Control coeff delta | Selected |
|---|---:|---:|---:|---:|---:|---|
| hybrid_branch | 84.147 | 0.0979 | 0.3411 | 0.671 | 0.00131 | True |
| hybrid_main_slope | 198.973 | 0.1459 | 0.3534 | 0.668 | 0.00131 | False |
| hybrid_constrained | 177.753 | 0.1202 | 0.3411 | 0.671 | 0.00131 | False |

## Figures

- `figures/*_input_pad_overlay.png`: input plus pad overlay for each short pulse.
- `figures/*_ku_only.png`: Ku plotted separately, with distinct colors for HSPICE, legacy, CoeffState, and hybrid.
- `figures/*_kd_only.png`: Kd plotted separately.
- `figures/*_pad_consequence.png`: pad mismatch area for legacy and hybrid.
- `figures/control_vs_interrupted.png`: long-pulse control versus interrupted 1 ns pulse.
- `figures/short_pulse_summary_bars.png`: pad RMSE, Ku RMSE, Kd RMSE, Ku peak, and Kd minimum.

## Interpretation

This is still experimental. A useful result requires coefficient correctness, not just a nicer pad waveform.
The hybrid is only a candidate for broader validation if it preserves the long-pulse control and improves pad, Ku, and Kd on the short-pulse cases.
