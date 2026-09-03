# sample1.ibs / BT2Z50CX

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
| short_high | legacy | COMPLETED | CHECK | 159.88347032067512 | 0.10699479349090614 | 0.08203219131579628 |
| short_high | value_match_v2 | COMPLETED | CHECK | 144.256967120904 | 0.11487358194768484 | 0.10147120897942999 |
| short_high | gate_state_full | COMPLETED | WARN | 122.71985949534977 | 0.07347851899761257 | 0.06995908625965162 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 118.68794646219142 | 0.06958583944616681 | 0.06877741623413124 |
| short_low | legacy | COMPLETED | WARN | 71.51583241055816 | 0.05012441024065934 | 0.03410072913881823 |
| short_low | value_match_v2 | COMPLETED | WARN | 71.58306047600892 | 0.050262685718769726 | 0.03410694273933019 |
| short_low | gate_state_full | COMPLETED | GOOD | 39.78447097063361 | 0.013989413163531477 | 0.010374793912936844 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 37.31946542457759 | 0.017809689834038692 | 0.012971414871844634 |
