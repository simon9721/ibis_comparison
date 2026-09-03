# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_highspeed_pd

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
| short_high | legacy | COMPLETED | CHECK | 297.1355912142861 | 0.1743658046343942 | 0.10116128053780035 |
| short_high | value_match_v2 | COMPLETED | CHECK | 13.508257734796617 | 0.009939345576286758 | 0.20173589495880917 |
| short_high | gate_state_full | COMPLETED | CHECK | 6.486008558913452 | 0.0061344781767856595 | 0.10353387747289854 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 6.373709462309395 | 0.0056524096484844456 | 0.09884354889039425 |
| short_low | legacy | COMPLETED | CHECK | 69.81682079445542 | 0.03694779215021363 | 0.1652421478110274 |
| short_low | value_match_v2 | COMPLETED | CHECK | 69.63295495042898 | 0.03669746161147131 | 0.1652424506436882 |
| short_low | gate_state_full | COMPLETED | WARN | 67.68105435679249 | 0.037288195163199284 | 0.044808603932159 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 74.16157135059218 | 0.04041964217311744 | 0.049924373994544156 |
