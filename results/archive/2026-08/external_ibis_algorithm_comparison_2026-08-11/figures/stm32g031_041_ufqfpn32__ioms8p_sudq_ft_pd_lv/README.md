# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd_lv

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
| short_high | legacy | COMPLETED | CHECK | 149.84124234138284 | 0.16297322798886696 | 0.09333268266551313 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.5002113765290058 | 0.0006335588764465476 | 0.12200846107654452 |
| short_high | gate_state_full | COMPLETED | WARN | 1.085387025571156 | 0.0013614229871385711 | 0.09331549589561712 |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | CHECK | 369.4012472814942 | 0.39665854293298947 | 0.19246322642201757 |
| short_low | value_match_v2 | COMPLETED | CHECK | 369.3975315884157 | 0.3966560937675805 | 0.19246268782252451 |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
