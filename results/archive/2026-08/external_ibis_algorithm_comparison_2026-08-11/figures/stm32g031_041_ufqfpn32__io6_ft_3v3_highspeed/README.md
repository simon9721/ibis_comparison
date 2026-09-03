# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_highspeed

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
| short_high | legacy | COMPLETED | CHECK | 297.1631317886314 | 0.17404938968901518 | 0.1019326184230549 |
| short_high | value_match_v2 | COMPLETED | CHECK | 13.73519726762641 | 0.010070907258438962 | 0.20056496349454855 |
| short_high | gate_state_full | COMPLETED | CHECK | 45.52572667981353 | 0.05432822362135637 | 0.1067423418454622 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 6.475748430859802 | 0.005742368400319228 | 0.10276913830891805 |
| short_low | legacy | COMPLETED | CHECK | 71.12707833986104 | 0.03783564935552498 | 0.16555122094176597 |
| short_low | value_match_v2 | COMPLETED | CHECK | 70.9306684896685 | 0.03758633991239791 | 0.16554950419829748 |
| short_low | gate_state_full | COMPLETED | WARN | 71.32818455271415 | 0.039627137840677853 | 0.047715483022348716 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 87.7376768680629 | 0.050858287154334686 | 0.04753375744879134 |
