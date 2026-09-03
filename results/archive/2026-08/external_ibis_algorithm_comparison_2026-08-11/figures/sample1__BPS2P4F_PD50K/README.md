# sample1.ibs / BPS2P4F_PD50K

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
| short_high | legacy | COMPLETED | CHECK | 181.24892132078287 | 1.2657475000602272 | 0.8531478084607097 |
| short_high | value_match_v2 | COMPLETED | CHECK | 79.35861006364328 | 1.280686257639662 | 0.8544788073795634 |
| short_high | gate_state_full | COMPLETED | CHECK | 199.8385256464385 | 1.11858771865529 | 0.9477510809760891 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 181.50225755070394 | 1.2921466082156403 | 0.8702000195271147 |
| short_low | legacy | COMPLETED | CHECK | 99.0077613098538 | 1.255703531738743 | 0.8563293893919451 |
| short_low | value_match_v2 | COMPLETED | CHECK | 96.90082732773429 | 0.20551780167638029 | 0.05204757850271245 |
| short_low | gate_state_full | COMPLETED | CHECK | 178.8785271591669 | 0.563787526120237 | 0.698787679425547 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 179.29466627946138 | 0.9446245497275272 | 0.8433588730251323 |
