# inv_t2b.ibs / driver3

- Component: `invchain`
- Model type: `Output`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | GOOD | 20.088329246601614 | 0.02122071814728505 | 0.020765458459990623 |
| short_high | value_match_v2 | COMPLETED | CHECK | 210.45596227308408 | 0.14612313027386173 | 0.15583336142197263 |
| short_high | gate_state_full | COMPLETED | CHECK | 42.667401430472765 | 0.11401172971651816 | 0.07699317749320836 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 23.370791259230323 | 0.02284583242652456 | 0.02140952778937888 |
| short_low | legacy | COMPLETED | GOOD | 23.261045929496948 | 0.022460524087884282 | 0.023591564000554947 |
| short_low | value_match_v2 | COMPLETED | GOOD | 23.369100081574526 | 0.022584651073259902 | 0.02387122047654413 |
| short_low | gate_state_full | COMPLETED | WARN | 59.66374704594504 | 0.025859728361116354 | 0.05973123705690029 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 22.27524000601366 | 0.02210511032960899 | 0.02097316404217544 |
