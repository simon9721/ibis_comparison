# sn74lvc2t45.ibs / LVC2T45_IO_B_25

- Component: `LVC2T45_YEP`
- Model type: `I/O`
- Supply: `2.5 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 219.63022588945 | 0.15615074657271744 | 0.02908527464009463 |
| short_high | value_match_v2 | COMPLETED | CHECK | 219.63630991581516 | 0.15621396780730154 | 0.029097698644764435 |
| short_high | gate_state_full | COMPLETED | GOOD | 25.19709893524128 | 0.03903063028891637 | 0.024932847734120123 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 219.63617312546168 | 0.1562194644694106 | 0.029111385539376033 |
| short_low | legacy | COMPLETED | CHECK | 61.361576810610686 | 0.04824087222992221 | 0.15443380006141016 |
| short_low | value_match_v2 | COMPLETED | CHECK | 935.6037955584934 | 0.5321742688789587 | 0.4578274825057818 |
| short_low | gate_state_full | COMPLETED | GOOD | 32.838726006662036 | 0.04501268305296436 | 0.023674183157429838 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 62.863267577442414 | 0.051289275208678424 | 0.1546157129672286 |
