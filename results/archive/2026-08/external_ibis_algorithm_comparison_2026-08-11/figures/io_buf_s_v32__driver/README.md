# io_buf_s_v32.ibs / driver

- Component: `MCM Driver 1`
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
| short_high | legacy | COMPLETED | CHECK | 236.7535585989199 | 0.16002261426948783 | 0.12240395687386732 |
| short_high | value_match_v2 | COMPLETED | CHECK | 120.63799441432143 | 0.06967593582868045 | 0.3858233729576902 |
| short_high | gate_state_full | COMPLETED | CHECK | 46.29771532754267 | 0.038666076318331896 | 0.12718131443101016 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 39.71368735127651 | 0.03265496778646303 | 0.12109954593043551 |
| short_low | legacy | COMPLETED | CHECK | 129.29818129365415 | 0.07830206763778387 | 0.35257595934491415 |
| short_low | value_match_v2 | COMPLETED | CHECK | 129.36250269482582 | 0.07836162920918989 | 0.35254098608656315 |
| short_low | gate_state_full | COMPLETED | WARN | 124.38329444584392 | 0.0793582450116569 | 0.03528104648228282 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 126.70816507220935 | 0.08122909735377132 | 0.035939024456224614 |
