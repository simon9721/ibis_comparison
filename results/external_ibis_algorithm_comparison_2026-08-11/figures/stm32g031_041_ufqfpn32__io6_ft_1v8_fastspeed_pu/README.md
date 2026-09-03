# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pu

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
| short_high | legacy | COMPLETED | CHECK | 175.99158765312004 | 0.2987280389651927 | 0.04002922898271068 |
| short_high | value_match_v2 | COMPLETED | CHECK | 6.3543400141837285 | 0.011099032201435365 | 0.30068766220433163 |
| short_high | gate_state_full | COMPLETED | GOOD | 3.1209355552126605 | 0.006675178347252336 | 0.040850397902138375 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 2.839186215770343 | 0.006193395316509751 | 0.0407758745270577 |
| short_low | legacy | COMPLETED | CHECK | 8.23966462114829 | 0.01410776376496068 | 0.288136151851493 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
