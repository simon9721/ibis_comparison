# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_mediumspeed_pu

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
| short_high | legacy | COMPLETED | CHECK | 171.72186942787883 | 0.10033433678302679 | 0.03355896864633686 |
| short_high | value_match_v2 | COMPLETED | WARN | 1.4545122645640123 | 0.001557597527135877 | 0.0520574583446197 |
| short_high | gate_state_full | COMPLETED | WARN | 76.39431505451648 | 0.07996789162876228 | 0.0745375212360625 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 16.820491523530137 | 0.01098322885411196 | 0.03466169906511762 |
| short_low | legacy | COMPLETED | CHECK | 39.78454406096958 | 0.021490796072855183 | 0.11956857270914609 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | GOOD | 43.18953119727177 | 0.023073434978404375 | 0.0012781684798633256 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
