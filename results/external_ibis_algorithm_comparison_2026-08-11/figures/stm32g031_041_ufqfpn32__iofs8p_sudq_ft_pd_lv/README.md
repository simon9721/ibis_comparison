# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pd_lv

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
| short_high | legacy | COMPLETED | CHECK | 229.46037227700404 | 0.24845273341592805 | 0.08766897889294895 |
| short_high | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_full | COMPLETED | WARN | 16.600719131254966 | 0.043434180480660334 | 0.09469492034181322 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 1.5973342882380492 | 0.0017045665844877607 | 0.0878429646761023 |
| short_low | legacy | COMPLETED | CHECK | 67.96055647327637 | 0.07060716417528634 | 0.23988408180945742 |
| short_low | value_match_v2 | COMPLETED | CHECK | 67.97848713552716 | 0.07063558694711955 | 0.23988247036568608 |
| short_low | gate_state_full | COMPLETED | CHECK | 129.45460571936852 | 0.10234538310044028 | 0.06384142579541434 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 69.52016137342085 | 0.07205436276436707 | 0.01958879220958282 |
