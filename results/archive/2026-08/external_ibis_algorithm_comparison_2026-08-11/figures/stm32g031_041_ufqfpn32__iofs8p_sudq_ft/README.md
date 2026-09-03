# stm32g031_041_ufqfpn32.ibs / iofs8p_sudq_ft

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
| short_high | legacy | COMPLETED | CHECK | 521.8623448085673 | 0.22168009966744945 | 0.0707587274834775 |
| short_high | value_match_v2 | COMPLETED | CHECK | 85.46831816764727 | 0.02689291136144872 | 0.20390699414894273 |
| short_high | gate_state_full | COMPLETED | WARN | 14.26952472489444 | 0.005456798980174525 | 0.07087891650847772 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 15.3304509885596 | 0.005405463101171104 | 0.06758510619508458 |
| short_low | legacy | COMPLETED | CHECK | 171.23153146150958 | 0.06523882443671317 | 0.22842333900923872 |
| short_low | value_match_v2 | COMPLETED | CHECK | 170.99674402616992 | 0.06516447713063972 | 0.22843190967522436 |
| short_low | gate_state_full | COMPLETED | CHECK | 174.81504972293015 | 0.06614481852494253 | 0.0061232181814013095 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 198.81829881242473 | 0.08009612079215933 | 0.00982206339964851 |
