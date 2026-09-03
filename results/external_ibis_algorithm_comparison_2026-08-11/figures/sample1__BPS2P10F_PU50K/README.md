# sample1.ibs / BPS2P10F_PU50K

- Component: `WXY123`
- Model type: `I/O`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `CHECK`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 256.0185186040993 | 0.3427003173336414 | 0.5226683444114324 |
| short_high | value_match_v2 | COMPLETED | CHECK | 201.34754467457543 | 0.35751208568064585 | 0.5668230834268965 |
| short_high | gate_state_full | COMPLETED | CHECK | 262.2587615047875 | 0.30712216612864013 | 0.546178009338191 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 253.72416642432887 | 0.3581642692659901 | 0.5478402691367971 |
| short_low | legacy | COMPLETED | CHECK | 313.03248233611464 | 0.36408798807712395 | 0.5154605428671333 |
| short_low | value_match_v2 | COMPLETED | CHECK | 287.62418727669257 | 0.12546556979322016 | 0.12983396903978275 |
| short_low | gate_state_full | COMPLETED | CHECK | 209.73770794753943 | 0.2965633980928535 | 0.12926942736224767 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 1471.7841708026763 | 0.8997180673596384 | 0.1399394267375879 |
