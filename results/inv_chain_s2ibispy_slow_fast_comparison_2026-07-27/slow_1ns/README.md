# inv_chain slow IBIS (1 ns source edges)

## Setup

- Source IBIS: `results\inv_chain_s2ibispy_slow_fast_2026-07-27\slow_1ns\inv_chain_slow_1ns.ibs`
- Source edge setting: `tr=tf=1 ns`
- Component/model: `invchain` / `driver2`
- Supply: `1.8 V`
- Load: `50 ohm || 2 pF`
- Applied input edge: `1 ps`
- Temperature: `27 C`
- No channel or transmission line.

## Offline Gate-State Reconstruction

- Worst directional-residual RMSE: `0.019446`
- Worst directional-residual max error: `0.066355`
- Reconstruction gate: **PASS**

## Comparison Phases

- `plots/01_hspice_ibis_vs_transistor/`: HSPICE native IBIS pad vs HSPICE transistor pad.
- `plots/02_hspice_ibis_vs_legacy/`: HSPICE native IBIS vs ngspice legacy pybis, pad/Ku/Kd.
- `plots/03_hspice_ibis_vs_gate_state/`: HSPICE native IBIS vs ngspice directional-residual, pad/Ku/Kd.
- `plots/04_hspice_ibis_gate_state_transistor/`: pad-only three-way overlay.
- `waveform_data/`: aligned numeric traces behind every plot.

## Pad RMSE versus Native HSPICE IBIS

| Case | HSPICE transistor (mV) | legacy pybis (mV) | gate-state pybis (mV) |
|---|---:|---:|---:|
| edge_1ps_base_50r_2pf | 383.230 | 11.364 | 18.082 |
| short_pulse_50ps_high | 41.239 | 564.806 | 17.373 |
| short_pulse_100ps_high | 142.679 | 538.271 | 22.404 |
| short_pulse_200ps_high | 316.355 | 494.879 | 26.142 |
| short_pulse_1ns_high | 602.499 | 17.298 | 24.829 |
| short_pulse_50ps_low | 322.480 | 414.360 | 39.625 |
| short_pulse_100ps_low | 344.027 | 392.520 | 29.694 |
| short_pulse_200ps_low | 412.654 | 365.503 | 24.918 |
| short_pulse_1ns_low | 521.885 | 14.339 | 22.949 |

## HSPICE Reference Sources

| Case | Reference | Source |
|---|---|---|
| edge_1ps_base_50r_2pf | hspice_native_ibis | prior_sanity |
| edge_1ps_base_50r_2pf | hspice_transistor | cache |
| short_pulse_50ps_high | hspice_native_ibis | run |
| short_pulse_50ps_high | hspice_transistor | cache |
| short_pulse_100ps_high | hspice_native_ibis | run |
| short_pulse_100ps_high | hspice_transistor | cache |
| short_pulse_200ps_high | hspice_native_ibis | run |
| short_pulse_200ps_high | hspice_transistor | cache |
| short_pulse_1ns_high | hspice_native_ibis | run |
| short_pulse_1ns_high | hspice_transistor | cache |
| short_pulse_50ps_low | hspice_native_ibis | run |
| short_pulse_50ps_low | hspice_transistor | cache |
| short_pulse_100ps_low | hspice_native_ibis | run |
| short_pulse_100ps_low | hspice_transistor | cache |
| short_pulse_200ps_low | hspice_native_ibis | run |
| short_pulse_200ps_low | hspice_transistor | cache |
| short_pulse_1ns_low | hspice_native_ibis | run |
| short_pulse_1ns_low | hspice_transistor | cache |
