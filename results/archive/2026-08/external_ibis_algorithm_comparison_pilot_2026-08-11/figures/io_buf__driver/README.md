# io_buf.ibs / driver

- Component: `MCM Driver 1`
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
| short_high | legacy | COMPLETED | CHECK | 238.24627220686978 | 0.1613509101118717 | 0.12732597985556313 |
| short_high | value_match_v2 | COMPLETED | CHECK | 111.36010449198633 | 0.06475137655483562 | 0.38394367362869525 |
| short_high | gate_state_full | COMPLETED | CHECK | 49.06992416938902 | 0.038998850580423815 | 0.1276746980797552 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 47.55313459532552 | 0.03745526852702062 | 0.12756363597179501 |
| short_low | legacy | COMPLETED | CHECK | 148.1659200494415 | 0.09007596234641409 | 0.35431601565316334 |
| short_low | value_match_v2 | COMPLETED | CHECK | 148.13787302921205 | 0.0900760217675451 | 0.35433497291174954 |
| short_low | gate_state_full | COMPLETED | WARN | 126.59027549260746 | 0.08057607973212351 | 0.031097408567437573 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 141.2589299126586 | 0.08957542456100917 | 0.03610732786648295 |
