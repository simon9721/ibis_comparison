# buffer.ibs / driver

- Component: `MCM Driver 1`
- Model type: `Output`
- Supply: `3.3 V`
- Full-swing legacy status/class: `CONVERSION_OR_ANALYSIS_FAIL` / ``

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | PYBIS_UNAVAILABLE |  |  |  |  |
| short_high | value_match_v2 | CONVERSION_FAIL |  |  |  |  |
| short_high | gate_state_full | CONVERSION_FAIL |  |  |  |  |
| short_high | gate_state_hybrid | CONVERSION_FAIL |  |  |  |  |
| short_low | legacy | PYBIS_UNAVAILABLE |  |  |  |  |
| short_low | value_match_v2 | CONVERSION_FAIL |  |  |  |  |
| short_low | gate_state_full | CONVERSION_FAIL |  |  |  |  |
| short_low | gate_state_hybrid | CONVERSION_FAIL |  |  |  |  |
