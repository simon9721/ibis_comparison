# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_fastspeed_pd

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
| short_high | legacy | COMPLETED | CHECK | 307.58085017496893 | 0.17993472090715681 | 0.22616722141644174 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.9962210117090105 | 0.0010889202884779912 | 0.20999728192240374 |
| short_high | gate_state_full | COMPLETED | CHECK | 3.7942359138947275 | 0.002782561531805125 | 0.22950235063748955 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 8.516122106556768 | 0.009490217683267353 | 0.22611023637589187 |
| short_low | legacy | COMPLETED | CHECK | 54.40845932204816 | 0.029702709804126107 | 0.19837802527969045 |
| short_low | value_match_v2 | COMPLETED | CHECK | 54.181594968904484 | 0.02965274876706044 | 0.19838006341734382 |
| short_low | gate_state_full | COMPLETED | WARN | 69.30790619332598 | 0.0397991842652134 | 0.009206996762068135 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 73.79562378483473 | 0.0424715541790614 | 0.009046705130465378 |
