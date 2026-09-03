# stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu

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
| short_high | legacy | COMPLETED | CHECK | 148.8766086817637 | 0.053654066847884145 | 0.4737342240937183 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.1773677859700635 | 0.0011600630179620507 | 0.2776939706513499 |
| short_high | gate_state_full | NGSPICE_FAIL |  |  |  |  |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | CHECK | 886.3943183652632 | 0.4148210907715569 | 0.10537293824838366 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
