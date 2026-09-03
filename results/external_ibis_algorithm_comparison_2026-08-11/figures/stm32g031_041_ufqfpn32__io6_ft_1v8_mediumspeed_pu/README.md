# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed_pu

- Component: `stm32g031_041_ufqfpn32`
- Model type: `I/O`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 59.58527111459651 | 0.10399531097696373 | 0.023097319139654526 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.1914203002536072 | 0.00342583454855694 | 0.19075402906795402 |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | CHECK | 26.875333438514527 | 0.04474277562445164 | 0.12788752184785224 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
