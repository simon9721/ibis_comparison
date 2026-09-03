# sample1.ibs / BPS2P4F_PU50K

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
| short_high | legacy | COMPLETED | CHECK | 162.1950932646921 | 0.2991442096590953 | 0.22505314753037658 |
| short_high | value_match_v2 | COMPLETED | CHECK | 72.9399283914983 | 0.24831472298876606 | 0.15169375267152607 |
| short_high | gate_state_full | COMPLETED | CHECK | 207.88920469427285 | 0.2926573703706739 | 0.2377816522792263 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 168.00948948263277 | 0.3027050999157563 | 0.23139170976232853 |
| short_low | legacy | COMPLETED | CHECK | 96.09444874437656 | 0.24802069770123025 | 0.14575527592390664 |
| short_low | value_match_v2 | COMPLETED | CHECK | 96.27742503447314 | 0.24407642662594303 | 0.14105613358596242 |
| short_low | gate_state_full | COMPLETED | CHECK | 187.50011001655176 | 0.226949799353748 | 0.09919063442642735 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 208.1560786229994 | 0.25452273992950514 | 0.13288208650063912 |
