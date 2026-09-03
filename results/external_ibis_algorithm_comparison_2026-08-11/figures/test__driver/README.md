# test.ibs / driver

- Component: `MCM Driver 1`
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
| short_high | legacy | COMPLETED | WARN | 117.65707121551917 | 0.08254447034517666 | 0.0685858123150957 |
| short_high | value_match_v2 | COMPLETED | CHECK | 20.294405854403557 | 0.018500555023875508 | 0.3275249268165991 |
| short_high | gate_state_full | COMPLETED | WARN | 30.984305889699314 | 0.048545285945882 | 0.0750203152301587 |
| short_high | gate_state_hybrid | COMPLETED | WARN | 15.51828148983818 | 0.023781966817609648 | 0.06517364108642139 |
| short_low | legacy | COMPLETED | CHECK | 392.72827136715307 | 0.2685521620290232 | 0.29095761700240924 |
| short_low | value_match_v2 | COMPLETED | CHECK | 392.696547920287 | 0.2685544092487001 | 0.2909695031995609 |
| short_low | gate_state_full | COMPLETED | CHECK | 388.5475490046734 | 0.2726871560639568 | 0.0064304538420692295 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 417.10942390814296 | 0.2769520943751454 | 0.04886201058063947 |
