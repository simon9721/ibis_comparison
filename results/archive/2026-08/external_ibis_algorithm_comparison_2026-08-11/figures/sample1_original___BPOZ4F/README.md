# sample1(original).ibs / BPOZ4F

- Component: `WXY123`
- Model type: `3-state`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 150.02131034517714 | 0.16839862476697348 | 0.1734162798009254 |
| short_high | value_match_v2 | COMPLETED | WARN | 6.025420411989968 | 0.011305422926483743 | 0.05299952717651445 |
| short_high | gate_state_full | COMPLETED | CHECK | 13.70094892573678 | 0.01439108246029806 | 0.1858486474055077 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 9.458043001631838 | 0.0058919407128087365 | 0.17131167177240417 |
| short_low | legacy | COMPLETED | WARN | 31.47353367119465 | 0.026928578226085194 | 0.051284465641542876 |
| short_low | value_match_v2 | COMPLETED | GOOD | 32.02291054168033 | 0.04312721857940384 | 0.049361270867821806 |
| short_low | gate_state_full | COMPLETED | CHECK | 126.17386999131105 | 0.06389552702852894 | 0.11978013844799067 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 48.603369036279304 | 0.06152711182520333 | 0.01647375419433275 |
