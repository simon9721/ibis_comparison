# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft

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
| short_high | legacy | COMPLETED | CHECK | 406.590955449254 | 0.16893277595370002 | 0.09316258315453224 |
| short_high | value_match_v2 | COMPLETED | CHECK | 108.04051062889863 | 0.041339189794140384 | 0.18723887759806337 |
| short_high | gate_state_full | COMPLETED | WARN | 59.187481916647435 | 0.024527461887658062 | 0.09886751921804728 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 42.61415162774998 | 0.005942361802021146 | 0.09120958208174107 |
| short_low | legacy | COMPLETED | CHECK | 156.79093509848929 | 0.05892816492929415 | 0.17732856356068716 |
| short_low | value_match_v2 | COMPLETED | CHECK | 156.91263265107924 | 0.05900675047697152 | 0.17735476488417073 |
| short_low | gate_state_full | COMPLETED | WARN | 124.40642769544844 | 0.04794804964466547 | 0.049708050178868854 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 163.19147712459343 | 0.06685427087606437 | 0.059146577469884234 |
