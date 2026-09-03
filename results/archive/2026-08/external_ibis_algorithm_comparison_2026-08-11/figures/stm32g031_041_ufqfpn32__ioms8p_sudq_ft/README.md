# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft

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
| short_high | legacy | COMPLETED | CHECK | 343.8645415463991 | 0.13849482925740786 | 0.4264214634046558 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.2089781471891754 | 0.0004170453176553065 | 0.27046498245572814 |
| short_high | gate_state_full | COMPLETED | CHECK | 47.97244769211639 | 0.05112934182933543 | 0.43815817935996404 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 10.56125098556005 | 0.006664724108510292 | 0.4268563178888999 |
| short_low | legacy | COMPLETED | CHECK | 137.67994058025903 | 0.052182368780352706 | 0.1673318358796163 |
| short_low | value_match_v2 | COMPLETED | CHECK | 137.01884189854195 | 0.0521976446913521 | 0.16725092542090123 |
| short_low | gate_state_full | COMPLETED | WARN | 131.6392818195628 | 0.05010325863971359 | 0.002060092284957123 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
