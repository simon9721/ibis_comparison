# io_buf_s2i_7_1.ibs / driver

- Component: `CMOS_Buffer`
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
| short_high | legacy | COMPLETED | CHECK | 132.89494159194405 | 0.09614419343450029 | 0.1050366066592523 |
| short_high | value_match_v2 | NGSPICE_TIMEOUT |  |  |  |  |
| short_high | gate_state_full | COMPLETED | GOOD | 39.26687370355339 | 0.045082166549561035 | 0.041998417205109856 |
| short_high | gate_state_hybrid | COMPLETED | GOOD | 40.70185649235175 | 0.04141983234733533 | 0.012265679865437251 |
| short_low | legacy | COMPLETED | CHECK | 560.319354967733 | 0.3721779582926499 | 0.29288262472034104 |
| short_low | value_match_v2 | COMPLETED | CHECK | 560.4753168137696 | 0.3723594905367166 | 0.2929870965574166 |
| short_low | gate_state_full | COMPLETED | CHECK | 553.430113249829 | 0.37106125013381774 | 0.053176962846691996 |
| short_low | gate_state_hybrid | COMPLETED | CHECK | 538.3025962522735 | 0.36153051580252665 | 0.04901429444063583 |
