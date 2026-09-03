# t2b_0616.ibs / driver2

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
| short_high | legacy | COMPLETED | GOOD | 22.163219165071034 | 0.022256778674375994 | 0.021779000735431545 |
| short_high | value_match_v2 | COMPLETED | CHECK | 211.99978078955738 | 0.14699754335134668 | 0.15742957893559953 |
| short_high | gate_state_full | COMPLETED | GOOD | 21.06464263465425 | 0.022371723300698546 | 0.020919679076245857 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 23.504051991425424 | 0.022636959251595635 | 0.021726250972865707 |
| short_low | legacy | COMPLETED | GOOD | 24.520126281535326 | 0.02280552128057428 | 0.02434282201357453 |
| short_low | value_match_v2 | COMPLETED | GOOD | 24.92467653153904 | 0.036729122408584586 | 0.03569739979445208 |
| short_low | gate_state_full | COMPLETED | WARN | 83.17036767934917 | 0.024363932957821847 | 0.08934814826363478 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 23.24353852228657 | 0.022886253924400624 | 0.02031753908050499 |
