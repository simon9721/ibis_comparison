# sample1(original).ibs / BPS2P10F_PU50K

- Component: `WXY123`
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
| short_high | legacy | COMPLETED | CHECK | 241.0851518351032 | 0.0808024354713817 | 0.07461188056862847 |
| short_high | value_match_v2 | COMPLETED | CHECK | 182.547171499532 | 0.076915283327508 | 0.15964890532470885 |
| short_high | gate_state_full | COMPLETED | WARN | 119.42224104977873 | 0.023059512179265346 | 0.06709828513987723 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 111.80298826388842 | 0.021322476707435305 | 0.06283447964855027 |
| short_low | legacy | COMPLETED | CHECK | 262.13387002501406 | 0.07748246839283317 | 0.12520570610405193 |
| short_low | value_match_v2 | COMPLETED | CHECK | 257.1743973976146 | 0.07971462264517853 | 0.12144257660129792 |
| short_low | gate_state_full | COMPLETED | CHECK | 172.24868016778456 | 0.05194556775096134 | 0.0516055391961044 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 184.83533644562075 | 0.055683482183797886 | 0.05742545098238644 |
