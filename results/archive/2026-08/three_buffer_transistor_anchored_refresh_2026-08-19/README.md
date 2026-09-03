# Three-Buffer Loaded-Swing Stress Sweep

This study sweeps output-level reversal stress from 90% to 50% of each HSPICE transistor buffer's measured loaded swing.
All cases use fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.
The HSPICE transistor response selects the pulse width; the exact same stimulus is then applied to HSPICE native IBIS and the ngspice gate-state model.

## Selected Stimuli

| Buffer | Direction | Target | Pulse width | Achieved transistor swing | Native-IBIS swing |
|---|---|---:|---:|---:|---:|
| io_buf | short high | 90% | 2354.134 ps | 89.09% | 75.10% |
| io_buf | short high | 80% | 2090.041 ps | 80.58% | 64.16% |
| io_buf | short high | 60% | 1666.313 ps | 60.53% | 41.04% |
| io_buf | short high | 50% | 1505.293 ps | 50.02% | 29.34% |
| io_buf | short low | 90% | 307.403 ps | 90.75% | 33.37% |
| io_buf | short low | 80% | 255.999 ps | 80.25% | 20.23% |
| io_buf | short low | 70% | 220.102 ps | 70.13% | 10.97% |
| io_buf | short low | 60% | 191.302 ps | 60.58% | 4.29% |
| io_buf | short low | 50% | 162.850 ps | 50.01% | 2.90% |

## Gate-State Agreement

| Buffer | Direction | Target | Pad RMSE | Ku RMSE | Kd RMSE |
|---|---|---:|---:|---:|---:|
| io_buf | short high | 90% | 56.55 mV | 0.07774 | 0.09303 |
| io_buf | short high | 80% | 61.12 mV | 0.07385 | 0.10583 |
| io_buf | short high | 60% | 51.09 mV | 0.05673 | 0.12830 |
| io_buf | short high | 50% | 43.70 mV | 0.05161 | 0.12508 |
| io_buf | short low | 90% | 787.76 mV | 0.58164 | 0.09333 |
| io_buf | short low | 80% | 811.07 mV | 0.59022 | 0.09488 |
| io_buf | short low | 70% | 795.18 mV | 0.57310 | 0.09589 |
| io_buf | short low | 60% | 808.75 mV | 0.57651 | 0.09832 |
| io_buf | short low | 50% | 812.25 mV | 0.57431 | 0.09935 |

## Initial Findings

- `ex2` short-high is the strongest gate-state result: pad RMSE rises gradually from 29.42 mV at 90% swing to 45.37 mV at 50%, while Ku/Kd remain comparatively close.
- `ex2` short-low has a clear stress boundary between 80% and 70%: pad RMSE jumps from 43.85 mV to 261.78 mV and both coefficient errors increase sharply.
- `inv_chain` does not show a useful gate-state region in this full-gate implementation; pad and coefficient errors remain large from slight through strong stress in both directions.
- `io_buf` is also not robust: short-low is poor at every level, while short-high is strongly non-monotonic and includes visible coefficient excursions outside the native-IBIS trajectory.
- Equal transistor loaded-swing targets do not create equal native-IBIS stress. At the 50% transistor target, native-IBIS excursion ranges from 8.80% for io_buf short-low to 94.86% for ex2 short-low.

## Figure Rules

Each case contains exactly two figures:

- `01_pad_voltage.png`: HSPICE transistor, HSPICE native IBIS, and gate-state model only.
- `02_ku_kd.png`: Ku and Kd panels, each containing HSPICE native IBIS and gate-state model only.
- Flat pre-event and post-recovery regions are cropped automatically from both figures.

Numeric waveforms are stored beside each case as `waveforms.csv`.
Selection evidence is stored in `selection.csv` and `selection_search.csv`.

Completed gate-state simulations: `9/9`.
