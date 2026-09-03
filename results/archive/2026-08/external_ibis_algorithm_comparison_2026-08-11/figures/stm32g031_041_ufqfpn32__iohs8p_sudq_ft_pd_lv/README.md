# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_pd_lv

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
| short_high | legacy | COMPLETED | CHECK | 244.5231867650641 | 0.2705337177931206 | 0.08989982138250337 |
| short_high | value_match_v2 | COMPLETED | CHECK | 43.20859913676622 | 0.0442069953209161 | 0.31535857887972907 |
| short_high | gate_state_full | COMPLETED | WARN | 7.340102254659955 | 0.008964469482911772 | 0.08876058945357819 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 5.642862691344774 | 0.006848317408788662 | 0.08993455534683632 |
| short_low | legacy | COMPLETED | CHECK | 45.94776648738879 | 0.048104742247709505 | 0.267309509618027 |
| short_low | value_match_v2 | COMPLETED | CHECK | 46.475076535653365 | 0.04888859451896636 | 0.2679446594659717 |
| short_low | gate_state_full | COMPLETED | GOOD | 34.55574995535515 | 0.03660253002445319 | 0.03612483493991854 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 54.145397100917386 | 0.058347115652279534 | 0.03992892534405197 |
