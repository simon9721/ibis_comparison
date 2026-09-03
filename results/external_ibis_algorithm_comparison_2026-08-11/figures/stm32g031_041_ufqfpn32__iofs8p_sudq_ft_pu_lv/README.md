# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pu_lv

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
| short_high | legacy | COMPLETED | CHECK | 233.58279588247353 | 0.2526822030470443 | 0.07522611545270846 |
| short_high | value_match_v2 | COMPLETED | CHECK | 3.0877281169802813 | 0.0033602972147488766 | 0.4215172907430748 |
| short_high | gate_state_full | COMPLETED | WARN | 22.883001047754 | 0.04965332772466135 | 0.07785348478697818 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 18.80886422581464 | 0.02177143492534224 | 0.0775934515731244 |
| short_low | legacy | COMPLETED | CHECK | 36.377762113701195 | 0.03824820754885351 | 0.2742190870040089 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | CHECK | 139.50236547564123 | 0.09969827293426249 | 0.07832309750325185 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 36.42970972680338 | 0.0382542485968869 | 0.2742377871430548 |
