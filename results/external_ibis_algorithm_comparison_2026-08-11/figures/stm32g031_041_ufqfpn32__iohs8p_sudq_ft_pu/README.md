# stm32g031_041_ufqfpn32.ibs / iohs8p_sudq_ft_pu

- Component: `stm32g031_041_ufqfpn32`
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
| short_high | legacy | COMPLETED | CHECK | 407.2439114658544 | 0.169153742513375 | 0.09314790054070314 |
| short_high | value_match_v2 | COMPLETED | CHECK | 108.0358001378079 | 0.04123418173762523 | 0.18446690220928189 |
| short_high | gate_state_full | COMPLETED | CHECK | 51.775850825758624 | 0.02637792524622709 | 0.10243905547026692 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 42.932213649521536 | 0.006061054101309827 | 0.09503858362753198 |
| short_low | legacy | COMPLETED | CHECK | 156.26469533730392 | 0.05867681552067885 | 0.17691186529477176 |
| short_low | value_match_v2 | COMPLETED | CHECK | 155.94048370068748 | 0.058559904067173034 | 0.17688171604606642 |
| short_low | gate_state_full | COMPLETED | WARN | 140.34392415136497 | 0.053923217523504346 | 0.05486780106208889 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 164.4121583278567 | 0.06803900999066545 | 0.059182086733269156 |
