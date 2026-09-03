# sample1(original).ibs / BT2Z50CX_PU50K

- Component: `WXY123`
- Model type: `I/O`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `WARN`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 160.07055648976197 | 0.10738136630799941 | 0.08409760588081433 |
| short_high | value_match_v2 | COMPLETED | CHECK | 143.93365503783883 | 0.1149258836338084 | 0.10152898249782062 |
| short_high | gate_state_full | COMPLETED | WARN | 123.76902374679533 | 0.07404706898812032 | 0.07774841553919377 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 119.0062174151868 | 0.07007292190992316 | 0.07098769902499007 |
| short_low | legacy | COMPLETED | GOOD | 61.27857816406549 | 0.047976502150920725 | 0.029279006738021723 |
| short_low | value_match_v2 | COMPLETED | GOOD | 61.32166494856945 | 0.048092020261724364 | 0.029297153105845505 |
| short_low | gate_state_full | COMPLETED | GOOD | 38.293788808582754 | 0.019962549400731038 | 0.012914876149661646 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 29.94845106165778 | 0.020513106037171176 | 0.007414200120363749 |
