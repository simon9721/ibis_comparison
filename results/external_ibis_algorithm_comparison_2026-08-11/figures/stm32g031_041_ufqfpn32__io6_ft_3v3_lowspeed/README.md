# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_lowspeed

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
| short_high | legacy | COMPLETED | WARN | 77.79290639375381 | 0.04589525856006853 | 0.010110782116217356 |
| short_high | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | legacy | COMPLETED | WARN | 9.434258821549525 | 0.006114707238811661 | 0.05514949222859312 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
