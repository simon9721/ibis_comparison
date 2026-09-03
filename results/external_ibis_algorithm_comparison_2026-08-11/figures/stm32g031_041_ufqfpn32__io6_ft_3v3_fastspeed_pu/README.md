# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_fastspeed_pu

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
| short_high | legacy | COMPLETED | CHECK | 309.4539447000503 | 0.1807623204502828 | 0.1507919451392309 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.8074128596967896 | 0.001371797944622283 | 0.12440055163353334 |
| short_high | gate_state_full | COMPLETED | CHECK | 4.261260823801388 | 0.0031088864100073544 | 0.16004718616372593 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 3.7781625339260163 | 0.0038050935832975303 | 0.14742786510282715 |
| short_low | legacy | COMPLETED | CHECK | 53.900748975727694 | 0.029727660494182906 | 0.19997366321682375 |
| short_low | value_match_v2 | COMPLETED | CHECK | 53.67001365549257 | 0.029665827090380507 | 0.1999758504100378 |
| short_low | gate_state_full | COMPLETED | GOOD | 56.820125401823965 | 0.031052213308716735 | 0.009313948256446884 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 70.26064199746553 | 0.04039274044179303 | 0.009382000784020482 |
