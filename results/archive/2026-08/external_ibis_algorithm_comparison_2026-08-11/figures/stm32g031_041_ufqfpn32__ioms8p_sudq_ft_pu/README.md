# stm32g031_041_ufqfpn32.ibs / ioms8p_sudq_ft_pu

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
| short_high | legacy | COMPLETED | CHECK | 307.68599257005417 | 0.12380534594579581 | 0.11744176273057859 |
| short_high | value_match_v2 | COMPLETED | GOOD | 1.284519635670282 | 0.0008079454243545264 | 0.044596462299859356 |
| short_high | gate_state_full | COMPLETED | CHECK | 34.90640277677626 | 0.03996369195624598 | 0.12349307364236083 |
| short_high | gate_state_hybrid | COMPLETED | CHECK | 1.6864577264284726 | 0.000874823050346935 | 0.11725558043926444 |
| short_low | legacy | COMPLETED | CHECK | 136.470460057967 | 0.051747116217646556 | 0.16762980478321954 |
| short_low | value_match_v2 | COMPLETED | CHECK | 136.52502141858088 | 0.051803740749887604 | 0.16762645607078144 |
| short_low | gate_state_full | COMPLETED | WARN | 123.08609000511831 | 0.046723185669514666 | 0.002014603232338958 |
| short_low | gate_state_hybrid | NGSPICE_TIMEOUT |  |  |  |  |
