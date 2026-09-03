# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed_pd

- Component: `stm32g031_041_ufqfpn32`
- Model type: `I/O`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 345.2395352184551 | 0.19794155136225927 | 0.028403918776623818 |
| short_high | value_match_v2 | COMPLETED | WARN | 0.8492543991770329 | 0.0008061286584264135 | 0.08939461443909574 |
| short_high | gate_state_full | COMPLETED | WARN | 2.113165031689044 | 0.0015835668792030986 | 0.08734752365250144 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 12.564086319365341 | 0.009897321000896521 | 0.06446519927240027 |
| short_low | legacy | COMPLETED | CHECK | 17.047687577061463 | 0.010983674737600166 | 0.20834769564800149 |
| short_low | value_match_v2 | COMPLETED | CHECK | 16.99329573317266 | 0.01112929441959282 | 0.2083753460241767 |
| short_low | gate_state_full | COMPLETED | GOOD | 28.314740871698127 | 0.020909008742011854 | 0.008477597811897447 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 22.55244452669346 | 0.013164529945475078 | 0.00786565554223239 |
