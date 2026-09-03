# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_pd

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
| short_high | legacy | COMPLETED | CHECK | 406.11824058094044 | 0.1690307241680739 | 0.09244371893169072 |
| short_high | value_match_v2 | COMPLETED | CHECK | 108.76077500413656 | 0.04156107167349773 | 0.18927691707863165 |
| short_high | gate_state_full | COMPLETED | WARN | 47.42923200966742 | 0.008698170832603377 | 0.0920618356133574 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 43.099889336215696 | 0.006106596542695666 | 0.08975970019817232 |
| short_low | legacy | COMPLETED | CHECK | 156.46968959812057 | 0.05867504784993868 | 0.1773348379330438 |
| short_low | value_match_v2 | COMPLETED | CHECK | 156.5890691721943 | 0.05875400008030757 | 0.17736160595430212 |
| short_low | gate_state_full | COMPLETED | WARN | 144.1636965800461 | 0.055228208778856466 | 0.05582304738038581 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 168.94326634807013 | 0.07077126969587505 | 0.06139508309047139 |
