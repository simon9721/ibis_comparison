# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_highspeed

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
| short_high | legacy | COMPLETED | CHECK | 139.52017555270686 | 0.2456198063095879 | 0.07515740615144574 |
| short_high | value_match_v2 | COMPLETED | CHECK | 21.476234972234135 | 0.03691726905602404 | 0.3449567204954104 |
| short_high | gate_state_full | COMPLETED | CHECK | 21.555945357874783 | 0.06387735053281766 | 0.10741234063373142 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 4.023789391304458 | 0.008107755731244351 | 0.0706366911803695 |
| short_low | legacy | COMPLETED | CHECK | 16.321380932167205 | 0.028172148503420747 | 0.2360140898317925 |
| short_low | value_match_v2 | COMPLETED | CHECK | 16.323208836476862 | 0.028230381320850567 | 0.2360046408992781 |
| short_low | gate_state_full | COMPLETED | CHECK | 88.50544749770184 | 0.10877908830681816 | 0.1028001868222826 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 33.18435793436358 | 0.05491769476848706 | 0.0479247937839558 |
