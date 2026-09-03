# io_buf_t2b_7_1.ibs / driver

- Component: `CMOS_Buffer`
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
| short_high | legacy | COMPLETED | CHECK | 125.91326567729497 | 0.10038188392618533 | 0.10131479304378943 |
| short_high | value_match_v2 | COMPLETED | CHECK | 13.260363115894517 | 0.013853478152427514 | 0.3009175255270014 |
| short_high | gate_state_full | COMPLETED | WARN | 75.54983096785062 | 0.060273089776698624 | 0.09832032153488761 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 63.85732428145148 | 0.05351402504575631 | 0.09162136860913006 |
| short_low | legacy | COMPLETED | CHECK | 567.2557737833789 | 0.367551950455787 | 0.2868026569981437 |
| short_low | value_match_v2 | COMPLETED | CHECK | 567.4575829336936 | 0.36795536737859197 | 0.28692040341441905 |
| short_low | gate_state_full | COMPLETED | CHECK | 571.0476014226584 | 0.366858045083233 | 0.04805166302997336 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 595.2958531502378 | 0.3793971371425803 | 0.05200820079799419 |
