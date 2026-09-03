# sn74lvc2t45.ibs / LVC2T45_IO_B_33

- Component: `LVC2T45_YEP`
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
| short_high | legacy | COMPLETED | CHECK | 294.2511586333576 | 0.14705518803462259 | 0.029326031541725965 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1089.0311513914573 | 0.4009086317110966 | 0.4781973862144817 |
| short_high | gate_state_full | COMPLETED | GOOD | 27.112079413811074 | 0.03459095610463653 | 0.04720414093258128 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 21.131648285459896 | 0.029763169090182583 | 0.031190846273653653 |
| short_low | legacy | COMPLETED | CHECK | 74.07350787938286 | 0.0399167197014397 | 0.1072426660103318 |
| short_low | value_match_v2 | COMPLETED | CHECK | 1256.872823866811 | 0.4843247797608772 | 0.4345817504285733 |
| short_low | gate_state_full | COMPLETED | GOOD | 25.68316622102693 | 0.035796322610124665 | 0.025530354786911357 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 44.091930877468 | 0.045442176912416546 | 0.02597299826712588 |
