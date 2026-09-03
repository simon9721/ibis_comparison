# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft_lv

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
| short_high | legacy | COMPLETED | CHECK | 232.50620253331502 | 0.25120290712242443 | 0.0890605751594428 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.7186395922788456 | 0.0018015921413027092 | 0.40374826865180014 |
| short_high | gate_state_full | COMPLETED | WARN | 1.7381244577250512 | 0.001819614574968554 | 0.0894491573362735 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 1.6655356656241875 | 0.0017733912032552037 | 0.08921105735201945 |
| short_low | legacy | COMPLETED | CHECK | 70.64833205513358 | 0.07385061279505153 | 0.24885695624044196 |
| short_low | value_match_v2 | COMPLETED | CHECK | 70.69508669788985 | 0.07381765949063249 | 0.24881455740100922 |
| short_low | gate_state_full | COMPLETED | WARN | 72.61586155045812 | 0.07558369012060685 | 0.007197457917802511 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
