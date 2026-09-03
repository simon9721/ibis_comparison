# sn74lvc2t45.ibs / LVC2T45_IO_A_50

- Component: `LVC2T45_YEP`
- Model type: `I/O`
- Supply: `5 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 342.70738196009415 | 0.1177164201698366 | 0.033761064411464745 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1752.0877795658978 | 0.3901490919259205 | 0.45146621492113886 |
| short_high | gate_state_full | COMPLETED | GOOD | 47.24154579524287 | 0.02606245763248248 | 0.026864590728093257 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 37.729008844650785 | 0.02564505526284049 | 0.030566202130507602 |
| short_low | legacy | COMPLETED | WARN | 120.39256173479923 | 0.03739102957095926 | 0.09887263510311503 |
| short_low | value_match_v2 | COMPLETED | WARN | 121.17005777012824 | 0.03881838555249358 | 0.09888426899125662 |
| short_low | gate_state_full | COMPLETED | GOOD | 46.48846316189533 | 0.03125033880645599 | 0.02677377274949252 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 45.90032854778704 | 0.039197993296995866 | 0.030833431905461003 |
