# sample1(original).ibs / BPS2P4F_PD50K

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
| short_high | legacy | COMPLETED | CHECK | 150.97363878618583 | 0.17137233377061825 | 0.17466635978104975 |
| short_high | value_match_v2 | COMPLETED | WARN | 5.318406601620517 | 0.00988092368682984 | 0.05014506399683479 |
| short_high | gate_state_full | COMPLETED | CHECK | 11.687544274157988 | 0.009826961953775002 | 0.17756718519205447 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 9.717501942483597 | 0.006294132203342803 | 0.17042614860384575 |
| short_low | legacy | COMPLETED | WARN | 31.678837092653055 | 0.02733912349641055 | 0.0506405510875189 |
| short_low | value_match_v2 | COMPLETED | GOOD | 29.430290717445196 | 0.040433381350752126 | 0.04466734234613866 |
| short_low | gate_state_full | COMPLETED | WARN | 64.82183831419101 | 0.06350269947473308 | 0.03985587490694709 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 58.18852564918503 | 0.0709412952001332 | 0.017045106442486718 |
