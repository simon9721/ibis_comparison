# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed_pd

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
| short_high | legacy | COMPLETED | CHECK | 102.94737847572473 | 0.18144762143123896 | 0.4458158642744426 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.8540370971039363 | 0.0014365686956058356 | 0.1514877389325099 |
| short_high | gate_state_full | COMPLETED | CHECK | 9.45199084282182 | 0.029076863679508607 | 0.4472275439833313 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 5.704379110389011 | 0.01292181981050331 | 0.4449570197282127 |
| short_low | legacy | COMPLETED | CHECK | 12.068499023062351 | 0.020340048757334216 | 0.2163713332551185 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | GOOD | 15.879013655538705 | 0.027372812616235632 | 0.005492666181638608 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 8.331083538652898 | 0.014927799576080251 | 0.005495851812013503 |
