# hct1g08.ibs / HCT1G08_OUTN_50

- Component: `74HCT1G08_GW`
- Model type: `Output`
- Supply: `5 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 469.85375185514727 | 0.13366481300044755 | 0.10567014780812786 |
| short_high | value_match_v2 | COMPLETED | CHECK | 339.96527747751014 | 0.10122633983970974 | 0.20783669224298507 |
| short_high | gate_state_full | COMPLETED | WARN | 179.0440289619671 | 0.05428906558110092 | 0.0791457978410607 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 172.13082440394606 | 0.05125342042320161 | 0.07984688603634772 |
| short_low | legacy | COMPLETED | CHECK | 633.0952146622406 | 0.19658296457340943 | 0.1590233235734778 |
| short_low | value_match_v2 | COMPLETED | CHECK | 629.8708036995722 | 0.19714444708257262 | 0.15441051213375295 |
| short_low | gate_state_full | COMPLETED | CHECK | 523.8247893084234 | 0.17012204375119502 | 0.04399315828156759 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 517.7598968822504 | 0.1692217327638098 | 0.04132670194641544 |
