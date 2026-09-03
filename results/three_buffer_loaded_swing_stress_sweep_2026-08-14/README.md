# Three-Buffer Loaded-Swing Stress Sweep

This study sweeps output-level reversal stress from 90% to 50% of each HSPICE transistor buffer's measured loaded swing.
All cases use fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.
The HSPICE transistor response selects the pulse width; the exact same stimulus is then applied to HSPICE native IBIS and the ngspice gate-state model.

## Selected Stimuli

| Buffer | Direction | Target | Pulse width | Achieved transistor swing | Native-IBIS swing |
|---|---|---:|---:|---:|---:|
| ex2 | short high | 90% | 974.720 ps | 90.92% | 92.16% |
| ex2 | short high | 80% | 895.261 ps | 80.69% | 89.37% |
| ex2 | short high | 70% | 857.595 ps | 70.82% | 87.73% |
| ex2 | short high | 60% | 830.102 ps | 60.30% | 86.51% |
| ex2 | short high | 50% | 809.637 ps | 49.90% | 85.11% |
| ex2 | short low | 90% | 771.694 ps | 90.26% | 101.98% |
| ex2 | short low | 80% | 733.688 ps | 80.51% | 101.64% |
| ex2 | short low | 70% | 715.062 ps | 70.16% | 97.51% |
| ex2 | short low | 60% | 701.704 ps | 60.14% | 95.48% |
| ex2 | short low | 50% | 688.219 ps | 49.71% | 94.86% |
| inv_chain | short high | 90% | 134.970 ps | 90.31% | 97.07% |
| inv_chain | short high | 80% | 119.044 ps | 80.79% | 94.96% |
| inv_chain | short high | 70% | 110.786 ps | 70.57% | 93.50% |
| inv_chain | short high | 60% | 106.290 ps | 60.11% | 92.50% |
| inv_chain | short high | 50% | 103.490 ps | 49.02% | 91.83% |
| inv_chain | short low | 90% | 115.992 ps | 89.93% | 93.93% |
| inv_chain | short low | 80% | 113.508 ps | 79.66% | 92.25% |
| inv_chain | short low | 70% | 112.175 ps | 69.69% | 91.72% |
| inv_chain | short low | 60% | 111.092 ps | 60.01% | 90.65% |
| inv_chain | short low | 50% | 110.291 ps | 49.60% | 88.51% |
| io_buf | short high | 90% | 2354.134 ps | 89.09% | 75.39% |
| io_buf | short high | 80% | 2090.041 ps | 80.58% | 65.05% |
| io_buf | short high | 70% | 1852.558 ps | 70.31% | 53.42% |
| io_buf | short high | 60% | 1666.313 ps | 60.53% | 42.19% |
| io_buf | short high | 50% | 1505.293 ps | 50.02% | 29.73% |
| io_buf | short low | 90% | 307.403 ps | 90.75% | 40.68% |
| io_buf | short low | 80% | 255.999 ps | 80.25% | 27.72% |
| io_buf | short low | 70% | 220.102 ps | 70.13% | 18.43% |
| io_buf | short low | 60% | 191.302 ps | 60.58% | 11.11% |
| io_buf | short low | 50% | 162.850 ps | 50.01% | 8.80% |

## Gate-State Agreement

| Buffer | Direction | Target | Pad RMSE | Ku RMSE | Kd RMSE |
|---|---|---:|---:|---:|---:|
| ex2 | short high | 90% | 29.42 mV | 0.08231 | 0.06131 |
| ex2 | short high | 80% | 31.47 mV | 0.07942 | 0.05047 |
| ex2 | short high | 70% | 31.36 mV | 0.07962 | 0.05465 |
| ex2 | short high | 60% | 38.14 mV | 0.09207 | 0.05910 |
| ex2 | short high | 50% | 45.37 mV | 0.10078 | 0.05804 |
| ex2 | short low | 90% | 58.16 mV | 0.10096 | 0.05662 |
| ex2 | short low | 80% | 43.85 mV | 0.06939 | 0.06227 |
| ex2 | short low | 70% | 261.78 mV | 0.28314 | 0.17761 |
| ex2 | short low | 60% | 281.47 mV | 0.32667 | 0.21751 |
| ex2 | short low | 50% | 281.38 mV | 0.31243 | 0.22319 |
| inv_chain | short high | 90% | 323.82 mV | 0.36729 | 0.30687 |
| inv_chain | short high | 80% | 340.62 mV | 0.34835 | 0.29905 |
| inv_chain | short high | 70% | 358.20 mV | 0.35690 | 0.30176 |
| inv_chain | short high | 60% | 369.11 mV | 0.35238 | 0.28773 |
| inv_chain | short high | 50% | 322.96 mV | 0.36721 | 0.29699 |
| inv_chain | short low | 90% | 343.21 mV | 0.43577 | 0.37164 |
| inv_chain | short low | 80% | 366.82 mV | 0.46417 | 0.37157 |
| inv_chain | short low | 70% | 371.00 mV | 0.48248 | 0.36396 |
| inv_chain | short low | 60% | 373.42 mV | 0.44682 | 0.37091 |
| inv_chain | short low | 50% | 399.66 mV | 0.45414 | 0.38297 |
| io_buf | short high | 90% | 138.42 mV | 0.33606 | 0.13417 |
| io_buf | short high | 80% | 581.95 mV | 0.34565 | 0.31799 |
| io_buf | short high | 70% | 647.31 mV | 0.40710 | 0.33266 |
| io_buf | short high | 60% | 165.67 mV | 0.40427 | 0.18112 |
| io_buf | short high | 50% | 699.02 mV | 0.47931 | 0.34364 |
| io_buf | short low | 90% | 593.96 mV | 0.78213 | 0.55937 |
| io_buf | short low | 80% | 561.65 mV | 0.77945 | 0.55328 |
| io_buf | short low | 70% | 534.37 mV | 0.78567 | 0.56121 |
| io_buf | short low | 60% | 567.33 mV | 0.82278 | 0.55339 |
| io_buf | short low | 50% | 478.83 mV | 0.79254 | 0.55971 |

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

Completed gate-state simulations: `30/30`.
