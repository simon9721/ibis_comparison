# stm32g031_041_ufqfpn32.ibs / io6_ft_3v3_fastspeed

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
| short_high | legacy | COMPLETED | CHECK | 307.93989907498656 | 0.17995230335306658 | 0.37476325541265276 |
| short_high | value_match_v2 | COMPLETED | CHECK | 1.3300185876487176 | 0.0008313110202111207 | 0.14261371005244117 |
| short_high | gate_state_full | COMPLETED | CHECK | 57.068402603050565 | 0.06200542999580926 | 0.38400815711289554 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 40.54092379994008 | 0.04215291654367487 | 0.3750093080069247 |
| short_low | legacy | COMPLETED | CHECK | 55.46740837978482 | 0.0308713730043375 | 0.20129175765810436 |
| short_low | value_match_v2 | COMPLETED | CHECK | 55.466847312655275 | 0.0309305506449899 | 0.20128825572672854 |
| short_low | gate_state_full | COMPLETED | GOOD | 62.64531141559518 | 0.0353086114559907 | 0.009665422052782965 |
| short_low | gate_state_hybrid | COMPLETED | WARN | 90.9325495986884 | 0.05590104359181625 | 0.009262333974719086 |
