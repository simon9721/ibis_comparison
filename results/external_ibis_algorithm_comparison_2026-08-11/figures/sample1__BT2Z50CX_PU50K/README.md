# sample1.ibs / BT2Z50CX_PU50K

- Component: `WXY123`
- Model type: `I/O`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `WARN`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 160.75247072286035 | 0.10781695406343642 | 0.08417375079113609 |
| short_high | value_match_v2 | COMPLETED | CHECK | 143.71393644136933 | 0.11482644323189715 | 0.1015241492276457 |
| short_high | gate_state_full | COMPLETED | WARN | 123.79841661579204 | 0.07424294183663904 | 0.0735242454686772 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 120.27044784727397 | 0.07095299249656475 | 0.07186932843852377 |
| short_low | legacy | COMPLETED | GOOD | 60.545532378046715 | 0.04759549941338578 | 0.02921026674944512 |
| short_low | value_match_v2 | COMPLETED | GOOD | 60.54901126071178 | 0.04768294210096195 | 0.029228564542170737 |
| short_low | gate_state_full | COMPLETED | GOOD | 38.03465287761477 | 0.01972953958909796 | 0.012963684833539971 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 28.43273731471559 | 0.01859100301094182 | 0.007111118512504975 |
