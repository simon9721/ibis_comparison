# sn74lvc2t45.ibs / LVC2T45_IO_A_33

- Component: `LVC2T45_YEP`
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
| short_high | legacy | COMPLETED | CHECK | 292.2960165494357 | 0.14619513877258553 | 0.026677541342358977 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1089.7771100322109 | 0.40122234290398934 | 0.4788927570884605 |
| short_high | gate_state_full | COMPLETED | GOOD | 35.82599915064759 | 0.03249066856282261 | 0.02381074609262205 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 53.97208595757724 | 0.03795878250548126 | 0.02724039309932312 |
| short_low | legacy | COMPLETED | CHECK | 72.46892536877041 | 0.04172690666290302 | 0.10758698578097574 |
| short_low | value_match_v2 | COMPLETED | CHECK | 1257.4479519319768 | 0.4845069631150753 | 0.4354006665745951 |
| short_low | gate_state_full | COMPLETED | WARN | 158.05847590212178 | 0.09430162470478486 | 0.04742117866912191 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 105.38147488382207 | 0.06276516956824349 | 0.03586655435936979 |
