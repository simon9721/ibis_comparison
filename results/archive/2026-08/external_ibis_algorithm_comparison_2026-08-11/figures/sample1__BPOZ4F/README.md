# sample1.ibs / BPOZ4F

- Component: `WXY123`
- Model type: `3-state`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `CHECK`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 172.81063747228148 | 1.3998975532717493 | 0.9327374239184502 |
| short_high | value_match_v2 | COMPLETED | CHECK | 82.63128334005448 | 1.385579152061598 | 0.9136126647521504 |
| short_high | gate_state_full | COMPLETED | CHECK | 212.68204445260267 | 1.1989451618609568 | 1.0141664014939957 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 179.29809504374956 | 1.3963283914569249 | 0.9292701325833742 |
| short_low | legacy | COMPLETED | CHECK | 105.74339656214183 | 1.383034839063637 | 0.9289431312146601 |
| short_low | value_match_v2 | COMPLETED | CHECK | 105.4729753777924 | 0.2938228385506942 | 0.05780319713421857 |
| short_low | gate_state_full | COMPLETED | CHECK | 189.1770992710666 | 0.8416831097998211 | 0.7514193750968668 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 174.92754238119244 | 1.110243092758753 | 0.9097065855329655 |
