# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_lv

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
| short_high | legacy | COMPLETED | CHECK | 156.51261254709587 | 0.1699685245582152 | 0.4958402058475889 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.5532075075144873 | 0.0007084001711429802 | 0.3771171314853166 |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 0.583085057135099 | 0.0007177454007743392 | 0.49583680314368117 |
| short_low | legacy | COMPLETED | CHECK | 23.127801503959887 | 0.024652615839030983 | 0.19295580091171788 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
