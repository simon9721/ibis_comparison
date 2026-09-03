# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_pu_lv

- Component: `stm32g031_041_ufqfpn32`
- Model type: `I/O`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 244.9719662056174 | 0.2704819332216169 | 0.09081022773011356 |
| short_high | value_match_v2 | COMPLETED | CHECK | 43.55477086114646 | 0.04425570838243569 | 0.3165050858871525 |
| short_high | gate_state_full | COMPLETED | CHECK | 29.15419771028523 | 0.0697939947725973 | 0.12336438865522255 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 13.943927761504742 | 0.014574790612993119 | 0.0882846931733299 |
| short_low | legacy | COMPLETED | CHECK | 44.426513799351675 | 0.04717000871709536 | 0.25948740871303494 |
| short_low | value_match_v2 | COMPLETED | CHECK | 44.4533708169097 | 0.047227186700124296 | 0.25947886761038563 |
| short_low | gate_state_full | COMPLETED | GOOD | 35.884849584305755 | 0.04410226464763037 | 0.03332225655798023 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 49.657889470114256 | 0.05212309333830065 | 0.04383831613476988 |
