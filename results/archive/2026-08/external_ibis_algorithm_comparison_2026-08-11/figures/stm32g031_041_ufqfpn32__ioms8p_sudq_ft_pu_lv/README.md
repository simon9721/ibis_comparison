# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu_lv

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
| short_high | legacy | COMPLETED | CHECK | 157.6460088616173 | 0.17117470131410883 | 0.07010217266477226 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.8166805221032314 | 0.0018125709164486226 | 0.10054129423962764 |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | COMPLETED | WARN | 1.1536871517470788 | 0.0018816535876078515 | 0.07007797874805571 |
| short_low | legacy | COMPLETED | CHECK | 98.24322978587675 | 0.10259538703877195 | 0.19068386004746088 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
