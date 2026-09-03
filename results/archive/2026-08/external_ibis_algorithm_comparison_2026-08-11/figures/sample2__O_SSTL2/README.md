# sample2.ibs / O_SSTL2

- Component: `XYZ123`
- Model type: `Output`
- Supply: `3.3 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 205.846318419848 | 0.21000649853675957 | 0.16888172814153082 |
| short_high | value_match_v2 | COMPLETED | CHECK | 26.618422698418858 | 0.034151807747142576 | 0.1293384205049314 |
| short_high | gate_state_full | COMPLETED | CHECK | 151.79976303322834 | 0.14304506706179917 | 0.1513424490355852 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 151.60295301822902 | 0.14148006536356675 | 0.15248078360493583 |
| short_low | legacy | COMPLETED | CHECK | 135.39100548040867 | 0.125798141768475 | 0.17211071840424472 |
| short_low | value_match_v2 | COMPLETED | CHECK | 135.3840162732479 | 0.1256844807329556 | 0.1720754365887817 |
| short_low | gate_state_full | COMPLETED | WARN | 89.16862278608363 | 0.09017101418681743 | 0.014997374197114591 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 97.4765921803939 | 0.10314627874396698 | 0.01507467474880391 |
