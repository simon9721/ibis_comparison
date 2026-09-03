# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_pu

- Component: `stm32g031_041_ufqfpn32`
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
| short_high | legacy | COMPLETED | CHECK | 525.4898568325306 | 0.22340006640726723 | 0.07105240659851594 |
| short_high | value_match_v2 | COMPLETED | CHECK | 86.29693823195305 | 0.026975994239041456 | 0.20111021906135715 |
| short_high | gate_state_full | COMPLETED | WARN | 14.55499602062084 | 0.005618266659847476 | 0.07117975698401949 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 13.507384980703145 | 0.005126800978193195 | 0.06653147409552779 |
| short_low | legacy | COMPLETED | CHECK | 174.29197391298393 | 0.06640591904925391 | 0.2333448878036445 |
| short_low | value_match_v2 | COMPLETED | CHECK | 174.38180580218622 | 0.06645937475730761 | 0.23333437524177836 |
| short_low | gate_state_full | COMPLETED | CHECK | 178.29040169225536 | 0.06764959840306495 | 0.0059597702034175585 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 177.00285112314816 | 0.06577660745735556 | 0.012520780562712918 |
