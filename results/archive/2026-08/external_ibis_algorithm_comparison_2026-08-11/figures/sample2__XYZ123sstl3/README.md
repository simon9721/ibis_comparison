# sample2.ibs / XYZ123sstl3

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
| short_high | legacy | COMPLETED | CHECK | 218.57872879556507 | 0.1899767246389885 | 0.15478279731141176 |
| short_high | value_match_v2 | COMPLETED | CHECK | 40.22288079335294 | 0.0441594112342241 | 0.14749836762865062 |
| short_high | gate_state_full | COMPLETED | CHECK | 168.9228024256971 | 0.13727659104459505 | 0.13764437699885954 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 167.85753938502722 | 0.13508774708140797 | 0.13683597191975186 |
| short_low | legacy | COMPLETED | CHECK | 161.66501276544807 | 0.13086207971839156 | 0.1855250036944681 |
| short_low | value_match_v2 | COMPLETED | CHECK | 161.74119188811417 | 0.13097212048423074 | 0.185572301406266 |
| short_low | gate_state_full | COMPLETED | CHECK | 113.94002142980773 | 0.10385310432113441 | 0.01678758282769937 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 113.11309718195189 | 0.102979355307021 | 0.012816077760725256 |
