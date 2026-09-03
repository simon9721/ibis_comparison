# sample1(original).ibs / BPS2P4F_PU50K

- Component: `WXY123`
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
| short_high | legacy | COMPLETED | CHECK | 151.04305271995352 | 0.1716175221251122 | 0.17651889267649376 |
| short_high | value_match_v2 | COMPLETED | GOOD | 4.8947036488671 | 0.009049470415860104 | 0.04896520810446623 |
| short_high | gate_state_full | COMPLETED | CHECK | 12.92417824392014 | 0.0108900363316187 | 0.1727178108935606 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 12.26387473361212 | 0.009323725028752653 | 0.16900342308723212 |
| short_low | legacy | COMPLETED | GOOD | 30.486994817333773 | 0.027135438537667828 | 0.04835682901099416 |
| short_low | value_match_v2 | COMPLETED | GOOD | 30.471517725686525 | 0.02739747572648099 | 0.04849230895306977 |
| short_low | gate_state_full | COMPLETED | CHECK | 176.3130191209336 | 0.07979028693876494 | 0.1566185715048422 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 52.56421624353346 | 0.06686191810899703 | 0.017609706729941638 |
