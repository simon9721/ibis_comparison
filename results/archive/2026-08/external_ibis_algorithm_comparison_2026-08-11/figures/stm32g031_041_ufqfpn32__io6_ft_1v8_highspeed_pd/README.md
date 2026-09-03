# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_highspeed_pd

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
| short_high | legacy | COMPLETED | CHECK | 138.4826815965387 | 0.24460850711974025 | 0.07266554024821466 |
| short_high | value_match_v2 | COMPLETED | CHECK | 21.906393711290757 | 0.03766419037548541 | 0.3437200179981893 |
| short_high | gate_state_full | COMPLETED | CHECK | 21.031755252807407 | 0.06257019417667972 | 0.10383082028183131 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 5.115819871361893 | 0.00987789707699909 | 0.07212632784741771 |
| short_low | legacy | COMPLETED | CHECK | 16.3060819351162 | 0.027382294969069815 | 0.23896622739337023 |
| short_low | value_match_v2 | COMPLETED | CHECK | 16.29637363820212 | 0.027455262108952383 | 0.23895669592668042 |
| short_low | gate_state_full | COMPLETED | WARN | 45.01067435369898 | 0.048318273230989014 | 0.07627419467915907 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 32.11947922784814 | 0.03559255277458441 | 0.06380417444120375 |
