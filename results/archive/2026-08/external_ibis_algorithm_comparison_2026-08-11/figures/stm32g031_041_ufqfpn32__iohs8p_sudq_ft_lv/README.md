# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_lv

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
| short_high | legacy | COMPLETED | CHECK | 245.73729549960416 | 0.27121717727843864 | 0.09128997465972796 |
| short_high | value_match_v2 | COMPLETED | CHECK | 43.445130173911494 | 0.04443152190539767 | 0.31674220082897503 |
| short_high | gate_state_full | COMPLETED | WARN | 6.8069144792669825 | 0.00833065652364057 | 0.09523607262581074 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 13.450132441165426 | 0.01388129960528513 | 0.10597928846982314 |
| short_low | legacy | COMPLETED | CHECK | 45.63099576176483 | 0.04813604188664371 | 0.26499771989363713 |
| short_low | value_match_v2 | COMPLETED | CHECK | 45.95161029122452 | 0.054127450954535375 | 0.2624388842717621 |
| short_low | gate_state_full | COMPLETED | WARN | 42.639256014494336 | 0.0448406889241647 | 0.0411375755211426 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 55.17993712615138 | 0.06018686919436376 | 0.039765191431449874 |
