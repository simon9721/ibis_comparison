# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_highspeed_pu

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
| short_high | legacy | COMPLETED | CHECK | 141.2156405193161 | 0.24813265044379962 | 0.07749711041847265 |
| short_high | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_full | COMPLETED | WARN | 3.7320408104480656 | 0.007932990620874969 | 0.07762670113782308 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 5.348486953576423 | 0.010664691185065807 | 0.08761386847576985 |
| short_low | legacy | COMPLETED | CHECK | 16.08366527762252 | 0.02765817420125273 | 0.24008582343443147 |
| short_low | value_match_v2 | COMPLETED | CHECK | 16.137444040109504 | 0.0347907100569311 | 0.2394464985085054 |
| short_low | gate_state_full | COMPLETED | GOOD | 17.08023964127907 | 0.030623926749720632 | 0.04139868074766573 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 26.140668414602917 | 0.045170738895830516 | 0.04308590151150211 |
