# sample1.ibs / BPOZ2F

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
| short_high | legacy | COMPLETED | CHECK | 164.18968095597089 | 0.33803667059945736 | 0.23660292223254553 |
| short_high | value_match_v2 | COMPLETED | CHECK | 71.8721046621854 | 0.2685249185123259 | 0.162095233876889 |
| short_high | gate_state_full | COMPLETED | CHECK | 173.72162711105022 | 0.33490821986925196 | 0.23471182661833412 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 167.12926776308555 | 0.3486769235022175 | 0.241782632901144 |
| short_low | legacy | COMPLETED | CHECK | 82.1666719121335 | 0.22910234440608485 | 0.11759002221767577 |
| short_low | value_match_v2 | COMPLETED | CHECK | 618.9141581989705 | 0.7463814595753474 | 0.9114242687891353 |
| short_low | gate_state_full | COMPLETED | CHECK | 324.4810124693742 | 0.44205152794831143 | 0.08127627718622553 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 323.72067849135556 | 0.44476585381300127 | 0.08841211715621819 |
