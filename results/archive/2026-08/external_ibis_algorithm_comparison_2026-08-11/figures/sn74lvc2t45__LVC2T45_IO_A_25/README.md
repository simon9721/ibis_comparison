# sn74lvc2t45.ibs / LVC2T45_IO_A_25

- Component: `LVC2T45_YEP`
- Model type: `I/O`
- Supply: `2.5 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 221.88060095842607 | 0.15744766841306088 | 0.029392725237497492 |
| short_high | value_match_v2 | COMPLETED | CHECK | 221.89182350937241 | 0.15743276322791427 | 0.029447453862178685 |
| short_high | gate_state_full | COMPLETED | WARN | 30.911658476916895 | 0.04431702165497897 | 0.058734108620701844 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 221.89396110004685 | 0.1574381570634824 | 0.029493875968500043 |
| short_low | legacy | COMPLETED | CHECK | 61.59510961650763 | 0.048497554546318544 | 0.1548485084768213 |
| short_low | value_match_v2 | COMPLETED | CHECK | 936.170411155229 | 0.5323847670763864 | 0.4581246254141035 |
| short_low | gate_state_full | COMPLETED | WARN | 50.01551371150892 | 0.06482784843293886 | 0.024307349352742327 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 62.8134435985368 | 0.05034971968295256 | 0.15449513051007235 |
