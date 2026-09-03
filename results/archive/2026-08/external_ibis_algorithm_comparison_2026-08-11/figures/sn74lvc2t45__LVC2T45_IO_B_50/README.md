# sn74lvc2t45.ibs / LVC2T45_IO_B_50

- Component: `LVC2T45_YEP`
- Model type: `I/O`
- Supply: `5 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 365.1950749471645 | 0.12242560976158469 | 0.03292394937279977 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1745.9470670742733 | 0.3883986671743405 | 0.4487562975447168 |
| short_high | gate_state_full | COMPLETED | GOOD | 53.36942379345488 | 0.026902051613428252 | 0.031632065326124226 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 68.22433301808901 | 0.03695513427284644 | 0.03232134306540993 |
| short_low | legacy | COMPLETED | WARN | 126.09016203450751 | 0.039651352421522776 | 0.09399471537663465 |
| short_low | value_match_v2 | COMPLETED | CHECK | 1880.7873277468564 | 0.44504238850165884 | 0.40834090713094934 |
| short_low | gate_state_full | COMPLETED | GOOD | 50.87714582260638 | 0.030565001053638435 | 0.030896301288864933 |
| short_low | gate_state_hybrid | COMPLETED | GOOD | 54.1844304281531 | 0.03916423607055554 | 0.03395734596748015 |
