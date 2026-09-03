# sample1(original).ibs / BT2Z50CX

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
| short_high | legacy | COMPLETED | CHECK | 159.88348646556662 | 0.1069947950283612 | 0.0820322099884208 |
| short_high | value_match_v2 | COMPLETED | CHECK | 144.26076750607078 | 0.11487358034344605 | 0.10147120257095672 |
| short_high | gate_state_full | COMPLETED | WARN | 122.8548481469962 | 0.07348074386366686 | 0.0699590932318629 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 118.68855759331599 | 0.06958668635808411 | 0.06877703263951554 |
| short_low | legacy | COMPLETED | WARN | 71.51583214482551 | 0.05012441738561126 | 0.03410069636367285 |
| short_low | value_match_v2 | COMPLETED | WARN | 71.58305888565316 | 0.05026269271683619 | 0.03410690956060393 |
| short_low | gate_state_full | COMPLETED | GOOD | 39.78832802323963 | 0.013991730950160295 | 0.010374631158958349 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 37.31922008414166 | 0.017807792729482363 | 0.01297140125145164 |
