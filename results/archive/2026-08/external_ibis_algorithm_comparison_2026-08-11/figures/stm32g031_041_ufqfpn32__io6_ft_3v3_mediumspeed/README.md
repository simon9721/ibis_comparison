# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed

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
| short_high | legacy | COMPLETED | CHECK | 170.71678551188887 | 0.09986417727481639 | 0.42985638760350886 |
| short_high | value_match_v2 | COMPLETED | WARN | 1.0277839829178894 | 0.00041307834174226864 | 0.07657112761898899 |
| short_high | gate_state_full | COMPLETED | CHECK | 71.84776225064272 | 0.07509997189529811 | 0.45121588286126924 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 29.350446233609222 | 0.018115101089670058 | 0.4319396855741026 |
| short_low | legacy | COMPLETED | CHECK | 40.48032811642296 | 0.0222131729124366 | 0.11862279344796238 |
| short_low | value_match_v2 | COMPLETED | CHECK | 40.47325876643831 | 0.022214038900806816 | 0.11860868327424946 |
| short_low | gate_state_full | COMPLETED | GOOD | 60.96863289407351 | 0.0364038769155129 | 0.0016317831326035654 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
