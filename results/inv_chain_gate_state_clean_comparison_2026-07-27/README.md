# inv_chain Clean IBIS / pybis / Transistor Comparison

This study applies the same clean comparison format used for `io_buf` to the established `inv_chain` buffer.

## Headline Findings

- `inv_chain` is much faster than `io_buf`: its complete-edge coefficient activity is concentrated near `0.2-0.4 ns`, so `1 ns` pulses are settled controls, not interrupted-pulse tests.
- On the complete-edge control, legacy pybis remains better than gate-state: pad RMSE is `59.1 mV` vs `110.2 mV`.
- On 50/100/200 ps short-high pulses, gate-state reduces pad RMSE from `1006/831/695 mV` to `110/108/114 mV` versus native HSPICE IBIS.
- On 50/100/200 ps short-low pulses, gate-state reduces pad RMSE from `704/459/412 mV` to `151/97/103 mV` versus native HSPICE IBIS.
- This is improved native-IBIS playback, not transistor-level validation. The transistor chain suppresses the 50 ps high pulse and the 100 ps low pulse. Native IBIS and gate-state still produce approximately `0.46 V` and `0.50 V` for the 50 ps high case.
- The directional-residual offline reconstruction gate still fails on `Ku` rise, and the gate-state model leaves visible coefficient/tail errors. It is not a default replacement.

## Setup

- IBIS: `inv_chain\t2b_0615_v5.ibs`
- IBIS component/model: `invchain` / `driver2`
- Transistor wrapper: `inv_chain\clean_ibis_vs_pybis_matched_pkg\invchain_ref_ngspice.sub`
- Transistor library: `inv_chain\clean_ibis_vs_pybis_matched_pkg\HL18G-S3.7S.lib`
- Supply: `1.8 V`
- Load in every flow: `50 ohm || 2 pF`
- Loaded steady high is approximately `1.42 V`, or `28.4 mA` into 50 ohm; this corresponds to about `13.3 ohm` effective pullup resistance at that operating point.
- Input edge: `1 ps`
- Temperature: `27 C`
- No channel or transmission line is present.

## Model Provenance

`t2b_0615_v5.ibs` is the established direct T2B `driver2` model used by the prior matched inv_chain study. `t2b_0616_v3.ibs` is a coarser export of the same model, not a separate fast-edge model, so it is not presented as a slow/fast pair.

## Offline Reconstruction Gate

- Directional-residual worst table RMSE: `0.025820`
- Directional-residual worst table max error: `0.078882`
- Gate result: **FAIL**

The gate-state transient figures are diagnostic when this gate is `FAIL`; they are not a validated replacement for legacy pybis.

## Clean Figure Sets

- `plots/01_legacy_vs_hspice_ibis/`: original pybis vs native HSPICE IBIS, pad/Ku/Kd.
- `plots/02_gate_state_vs_hspice_ibis/`: directional-residual gate-state vs native HSPICE IBIS, pad/Ku/Kd.
- `plots/03_ibis_gate_state_transistor_pad/`: pad-only native IBIS, gate-state, and transistor overlays.
- `plots/*_contact_sheet.png`: one-page overviews.
- `waveform_data/*.csv`: aligned numeric data behind every figure.
- `metrics.csv`: pad/Ku/Kd error and extrema values.
- `source_provenance.csv`: source and generated-model hashes.

## Metrics

| Case | Flow | Pad RMSE (mV) | Ku RMSE | Kd RMSE |
|---|---|---:|---:|---:|
| edge_1ps_base_50r_2pf | legacy | 59.102 | 0.10324 | 0.07183 |
| edge_1ps_base_50r_2pf | gate_state | 110.162 | 0.15523 | 0.12608 |
| edge_1ps_base_50r_2pf | hspice_transistor | 62.479 | n/a | n/a |
| short_pulse_50ps_high | legacy | 1005.992 | 0.51757 | 0.35612 |
| short_pulse_50ps_high | gate_state | 109.716 | 0.18538 | 0.21981 |
| short_pulse_50ps_high | hspice_transistor | 205.078 | n/a | n/a |
| short_pulse_100ps_high | legacy | 830.954 | 0.46112 | 0.31474 |
| short_pulse_100ps_high | gate_state | 107.552 | 0.14804 | 0.12898 |
| short_pulse_100ps_high | hspice_transistor | 461.988 | n/a | n/a |
| short_pulse_200ps_high | legacy | 695.357 | 0.46143 | 0.27411 |
| short_pulse_200ps_high | gate_state | 114.070 | 0.14894 | 0.13903 |
| short_pulse_200ps_high | hspice_transistor | 74.747 | n/a | n/a |
| short_pulse_1ns_high | legacy | 61.976 | 0.09680 | 0.07446 |
| short_pulse_1ns_high | gate_state | 112.835 | 0.14169 | 0.12443 |
| short_pulse_1ns_high | hspice_transistor | 64.677 | n/a | n/a |
| short_pulse_50ps_low | legacy | 703.756 | 0.42026 | 0.42506 |
| short_pulse_50ps_low | gate_state | 151.280 | 0.34569 | 0.10322 |
| short_pulse_50ps_low | hspice_transistor | 156.224 | n/a | n/a |
| short_pulse_100ps_low | legacy | 458.825 | 0.24594 | 0.34432 |
| short_pulse_100ps_low | gate_state | 96.916 | 0.16237 | 0.11162 |
| short_pulse_100ps_low | hspice_transistor | 678.455 | n/a | n/a |
| short_pulse_200ps_low | legacy | 411.620 | 0.22279 | 0.31731 |
| short_pulse_200ps_low | gate_state | 103.126 | 0.16777 | 0.11913 |
| short_pulse_200ps_low | hspice_transistor | 59.281 | n/a | n/a |
| short_pulse_1ns_low | legacy | 56.394 | 0.10491 | 0.07825 |
| short_pulse_1ns_low | gate_state | 103.384 | 0.15902 | 0.12855 |
| short_pulse_1ns_low | hspice_transistor | 56.429 | n/a | n/a |

## HSPICE Cache

| Case | Reference | Source |
|---|---|---|
| edge_1ps_base_50r_2pf | hspice_native_ibis | cache |
| edge_1ps_base_50r_2pf | hspice_transistor | cache |
| short_pulse_50ps_high | hspice_native_ibis | cache |
| short_pulse_50ps_high | hspice_transistor | cache |
| short_pulse_100ps_high | hspice_native_ibis | cache |
| short_pulse_100ps_high | hspice_transistor | cache |
| short_pulse_200ps_high | hspice_native_ibis | cache |
| short_pulse_200ps_high | hspice_transistor | cache |
| short_pulse_1ns_high | hspice_native_ibis | cache |
| short_pulse_1ns_high | hspice_transistor | cache |
| short_pulse_50ps_low | hspice_native_ibis | cache |
| short_pulse_50ps_low | hspice_transistor | cache |
| short_pulse_100ps_low | hspice_native_ibis | cache |
| short_pulse_100ps_low | hspice_transistor | cache |
| short_pulse_200ps_low | hspice_native_ibis | cache |
| short_pulse_200ps_low | hspice_transistor | cache |
| short_pulse_1ns_low | hspice_native_ibis | cache |
| short_pulse_1ns_low | hspice_transistor | cache |
