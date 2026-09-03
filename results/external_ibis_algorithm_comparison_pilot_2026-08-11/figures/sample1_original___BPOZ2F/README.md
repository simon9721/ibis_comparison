# sample1(original).ibs / BPOZ2F

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
| short_high | legacy | COMPLETED | CHECK | 151.87021362254734 | 0.22920484495441193 | 0.19496802494485607 |
| short_high | value_match_v2 | COMPLETED | WARN | 1.2677255520347799 | 0.0021705233467791494 | 0.06398677432068231 |
| short_high | gate_state_full | COMPLETED | CHECK | 3.075322350753193 | 0.0058645763332083704 | 0.19294402449081993 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 17.44834469105286 | 0.033335222335008026 | 0.19401711303354016 |
| short_low | legacy | COMPLETED | GOOD | 14.253096414291623 | 0.019374402278826343 | 0.03983447760088104 |
| short_low | value_match_v2 | COMPLETED | GOOD | 14.278397349674417 | 0.019492338482430014 | 0.04031562611340456 |
| short_low | gate_state_full | COMPLETED | CHECK | 85.5049832221409 | 0.11165242001110086 | 0.0246812165893339 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 82.95155107123608 | 0.10848488936756422 | 0.027842596970342352 |
