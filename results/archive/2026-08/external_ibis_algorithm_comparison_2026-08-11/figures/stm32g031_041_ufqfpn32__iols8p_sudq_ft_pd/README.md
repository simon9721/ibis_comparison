# stm32g031_041_ufqfpn32.ibs / iols8p_sudq_ft_pd

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
| short_high | legacy | COMPLETED | CHECK | 260.64493674740413 | 0.10878550104035818 | 0.4228300514542445 |
| short_high | value_match_v2 | COMPLETED | WARN | 0.7920022616964679 | 0.0006554132659855218 | 0.08899384937933016 |
| short_high | gate_state_full | COMPLETED | CHECK | 47.79893938095638 | 0.04855049520473188 | 0.4255068309075093 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 0.5922293600182877 | 0.0006571066385511486 | 0.4228222727607972 |
| short_low | legacy | COMPLETED | CHECK | 650.4905740963432 | 0.2571303881879763 | 0.11513219488015286 |
| short_low | value_match_v2 | COMPLETED | CHECK | 650.5068588710282 | 0.25713793574061306 | 0.11514868285964239 |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
