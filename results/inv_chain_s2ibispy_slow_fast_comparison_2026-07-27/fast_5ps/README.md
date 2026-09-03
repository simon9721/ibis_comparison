# inv_chain fast IBIS (5 ps source edges)

## Setup

- Source IBIS: `results\inv_chain_s2ibispy_slow_fast_2026-07-27\fast_5ps\inv_chain_fast_5ps.ibs`
- Source edge setting: `tr=tf=5 ps`
- Component/model: `invchain` / `driver2`
- Supply: `1.8 V`
- Load: `50 ohm || 2 pF`
- Applied input edge: `1 ps`
- Temperature: `27 C`
- No channel or transmission line.

## Offline Gate-State Reconstruction

- Worst directional-residual RMSE: `0.019901`
- Worst directional-residual max error: `0.069460`
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
| edge_1ps_base_50r_2pf | 13.822 | 11.408 | 17.383 |
| short_pulse_50ps_high | 39.612 | 294.312 | 16.600 |
| short_pulse_100ps_high | 115.861 | 244.556 | 23.452 |
| short_pulse_200ps_high | 24.525 | 144.357 | 27.367 |
| short_pulse_1ns_high | 20.969 | 17.427 | 25.194 |
| short_pulse_50ps_low | 15.532 | 232.084 | 45.086 |
| short_pulse_100ps_low | 129.156 | 185.059 | 22.467 |
| short_pulse_200ps_low | 18.716 | 121.055 | 25.355 |
| short_pulse_1ns_low | 17.068 | 14.365 | 24.027 |

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
