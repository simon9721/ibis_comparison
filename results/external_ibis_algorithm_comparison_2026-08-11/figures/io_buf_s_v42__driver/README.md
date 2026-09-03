# io_buf_s_v42.ibs / driver

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
| short_high | legacy | COMPLETED | CHECK | 238.25141486092326 | 0.16135418917471897 | 0.12733514639612545 |
| short_high | value_match_v2 | COMPLETED | CHECK | 111.37499914065796 | 0.06476008465476915 | 0.38398564132923446 |
| short_high | gate_state_full | COMPLETED | CHECK | 49.09592014614852 | 0.03898949855765295 | 0.12768416095869473 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 47.585729549248995 | 0.037470325296318316 | 0.12757174186723955 |
| short_low | legacy | COMPLETED | CHECK | 145.6518261886832 | 0.0884891617463266 | 0.353730849364003 |
| short_low | value_match_v2 | COMPLETED | CHECK | 145.62285280099346 | 0.08849073803359317 | 0.35374551879014654 |
| short_low | gate_state_full | COMPLETED | CHECK | 168.9694136898653 | 0.09600811963240262 | 0.04844475146753813 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 145.82272728843466 | 0.0911667195951448 | 0.03816749559706331 |
