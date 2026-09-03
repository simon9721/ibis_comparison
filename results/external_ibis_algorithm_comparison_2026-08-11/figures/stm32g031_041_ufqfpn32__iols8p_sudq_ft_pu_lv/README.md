# stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pu_lv

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
| short_high | legacy | COMPLETED | WARN | 59.54264879343757 | 0.06411021692165246 | 0.015528344541987125 |
| short_high | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | CHECK | 54.53637933646739 | 0.05747913975323918 | 0.10778720953242782 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
