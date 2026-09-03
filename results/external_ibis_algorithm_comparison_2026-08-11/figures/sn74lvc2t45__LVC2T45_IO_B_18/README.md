# sn74lvc2t45.ibs / LVC2T45_IO_B_18

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
| short_high | legacy | COMPLETED | CHECK | 162.80704897612128 | 0.22517078829710932 | 0.025625179584427542 |
| short_high | value_match_v2 | COMPLETED | CHECK | 162.8046410283285 | 0.22515824542814683 | 0.0256859787529263 |
| short_high | gate_state_full | COMPLETED | WARN | 32.02843634317113 | 0.050430031310717535 | 0.017188305754680937 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 162.80511198500065 | 0.2251587941731059 | 0.025660225362234886 |
| short_low | legacy | COMPLETED | CHECK | 42.29766218750029 | 0.06411204321253468 | 0.21794231211708992 |
| short_low | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_low | gate_state_full | COMPLETED | WARN | 51.18890183129839 | 0.06811523046733274 | 0.019505492853471237 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 45.80717366250973 | 0.06760880225832283 | 0.2179962638319551 |
