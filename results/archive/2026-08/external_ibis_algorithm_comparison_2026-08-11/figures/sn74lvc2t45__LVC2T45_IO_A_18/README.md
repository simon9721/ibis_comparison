# sn74lvc2t45.ibs / LVC2T45_IO_A_18

- Component: `LVC2T45_YEP`
- Model type: `I/O`
- Supply: `1.8 V`
- Full-swing legacy status/class: `COMPLETED` / `WARN`

## Figures

- `00_full_swing.png`: complete rise/fall, HSPICE native IBIS versus legacy pybis.
- `01_short_high_algorithms.png`: fall-after-rise stress comparison.
- `02_short_low_algorithms.png`: rise-after-fall stress comparison.

## Stress Status

| Direction | Flow | Status | Class | Pad RMSE mV | Ku RMSE | Kd RMSE |
|---|---|---|---|---:|---:|---:|
| short_high | legacy | COMPLETED | CHECK | 163.9577240229625 | 0.22667065013231033 | 0.026763103671627306 |
| short_high | value_match_v2 | COMPLETED | CHECK | 163.97373742801352 | 0.2267439149801174 | 0.02684996894833252 |
| short_high | gate_state_full | COMPLETED | WARN | 30.672009236158 | 0.05702684800772983 | 0.03867798847053666 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 163.9741429384109 | 0.22674220841551862 | 0.02680894476222913 |
| short_low | legacy | COMPLETED | CHECK | 41.042525533667366 | 0.06286803876948462 | 0.2201536519711822 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | WARN | 51.672666601343906 | 0.09265786560056755 | 0.05696287073340064 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 44.76486849790765 | 0.06643446439787344 | 0.2201590314184537 |
