# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_fastspeed

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
| short_high | legacy | COMPLETED | CHECK | 102.67405291510401 | 0.1808175120857075 | 0.44874283415480154 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.8347032640139369 | 0.001380623712273047 | 0.15106203090843862 |
| short_high | gate_state_full | COMPLETED | CHECK | 4.6340571652045455 | 0.013956840785979346 | 0.4489285054610963 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 0.7433947181344638 | 0.001734494464984131 | 0.4485963734960105 |
| short_low | legacy | COMPLETED | CHECK | 12.287439120129816 | 0.02092691085280004 | 0.21670751598103377 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | GOOD | 12.551577288971785 | 0.02130213109517936 | 0.0052185958845525696 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
