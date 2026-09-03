# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pd

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
| short_high | legacy | COMPLETED | CHECK | 350.97827897768997 | 0.141530325832235 | 0.4353711089863008 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.2004435346039781 | 0.00040553725027454504 | 0.2769392666962012 |
| short_high | gate_state_full | COMPLETED | CHECK | 2.8986332155810097 | 0.001405093135891537 | 0.4401005860988676 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 1.1481063638891433 | 0.00044200468087217295 | 0.4357686859499442 |
| short_low | legacy | COMPLETED | CHECK | 136.78763888132775 | 0.051604400573984695 | 0.1674514505277661 |
| short_low | value_match_v2 | COMPLETED | CHECK | 136.80509824498156 | 0.05164574096553482 | 0.16745581993825215 |
| short_low | gate_state_full | COMPLETED | WARN | 128.40726337552738 | 0.048615168543423015 | 0.00216322277131735 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
