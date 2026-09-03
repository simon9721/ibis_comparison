# stm32g031_041_ufqfpn32.ibs / io6_ft_1v8_mediumspeed

- Component: `stm32g031_041_ufqfpn32`
- Model type: `I/O`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `GOOD`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 57.54606223584839 | 0.1004735637195854 | 0.48196643288028707 |
| short_high | value_match_v2 | COMPLETED | CHECK | 0.3881622275455458 | 0.0009077504789963101 | 0.328350648687705 |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | CHECK | 6.923393277611173 | 0.012056040682520324 | 0.12394876788409867 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
