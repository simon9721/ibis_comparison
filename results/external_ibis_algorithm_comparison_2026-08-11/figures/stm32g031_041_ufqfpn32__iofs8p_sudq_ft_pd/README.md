# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pd

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
| short_high | legacy | COMPLETED | CHECK | 529.0021133764554 | 0.22503101590157815 | 0.07115097956702157 |
| short_high | value_match_v2 | COMPLETED | CHECK | 86.61037991631953 | 0.02721135638195567 | 0.20814470686522346 |
| short_high | gate_state_full | COMPLETED | WARN | 41.34350932125735 | 0.03714455399877911 | 0.09392876747285893 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 12.23358066570778 | 0.004889294880417024 | 0.06694387749240349 |
| short_low | legacy | COMPLETED | CHECK | 162.69028373510736 | 0.06183072541875673 | 0.23217535803541012 |
| short_low | value_match_v2 | COMPLETED | CHECK | 162.66244644582483 | 0.061841790140969397 | 0.2321765994128119 |
| short_low | gate_state_full | COMPLETED | WARN | 146.7803081389235 | 0.05566741385177336 | 0.007023541287393291 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 180.75503213215148 | 0.07145170061263664 | 0.008197673247018459 |
