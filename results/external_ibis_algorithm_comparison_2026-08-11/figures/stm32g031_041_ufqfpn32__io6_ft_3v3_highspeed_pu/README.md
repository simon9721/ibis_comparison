# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_highspeed_pu

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
| short_high | legacy | COMPLETED | CHECK | 289.27158328811583 | 0.16944106610549428 | 0.09516352988844737 |
| short_high | value_match_v2 | COMPLETED | CHECK | 21.653022091244576 | 0.01440233931467784 | 0.20534619757449654 |
| short_high | gate_state_full | COMPLETED | WARN | 7.0763978639718115 | 0.00689114332084378 | 0.09616245359638881 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 7.240442821195011 | 0.006164849498945749 | 0.0981033555256293 |
| short_low | legacy | COMPLETED | CHECK | 75.12977217605564 | 0.040238546951957464 | 0.16714250019689708 |
| short_low | value_match_v2 | COMPLETED | CHECK | 74.87457308238507 | 0.039614256765001354 | 0.16714939884219493 |
| short_low | gate_state_full | COMPLETED | GOOD | 48.03727170367065 | 0.02722103359666649 | 0.04091607057958377 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 98.29674124004237 | 0.057672186979234236 | 0.04817068227659843 |
