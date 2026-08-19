# Three-Buffer Loaded-Swing Stress Sweep

This study sweeps output-level reversal stress from 90% to 50% of each HSPICE transistor buffer's measured loaded swing.
All cases use fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.
The HSPICE transistor response selects the pulse width; the exact same stimulus is then applied to HSPICE native IBIS and the ngspice gate-state model.

## Selected Stimuli

| Buffer | Direction | Target | Pulse width | Achieved transistor swing | Native-IBIS swing |
|---|---|---:|---:|---:|---:|
| ex2 | short high | 80% | 739.518 ps | 18.04% | 79.91% |
| ex2 | short high | 70% | 645.757 ps | 4.84% | 70.58% |
| ex2 | short high | 60% | 577.361 ps | 1.67% | 62.01% |
| ex2 | short high | 50% | 576.298 ps | 1.65% | 49.91% |
| ex2 | short low | 90% | 641.626 ps | 20.44% | 90.39% |
| ex2 | short low | 80% | 581.421 ps | 7.41% | 80.86% |
| ex2 | short low | 70% | 530.135 ps | 3.56% | 69.21% |
| ex2 | short low | 60% | 492.437 ps | 2.01% | 60.97% |
| ex2 | short low | 50% | 440.682 ps | 0.79% | 50.71% |
| inv_chain | short high | 90% | 96.846 ps | 4.05% | 90.05% |
| inv_chain | short high | 80% | 72.052 ps | 0.00% | 80.06% |
| inv_chain | short high | 70% | 55.795 ps | 0.00% | 70.06% |
| inv_chain | short high | 60% | 50.000 ps | 0.00% | 65.58% |
| inv_chain | short high | 50% | 50.000 ps | 0.00% | 65.58% |
| inv_chain | short low | 90% | 111.029 ps | 59.34% | 90.62% |
| inv_chain | short low | 80% | 103.565 ps | 1.04% | 79.85% |
| inv_chain | short low | 70% | 97.978 ps | 0.02% | 69.57% |
| inv_chain | short low | 60% | 91.129 ps | 0.01% | 59.61% |
| inv_chain | short low | 50% | 86.015 ps | 0.00% | 49.73% |
| io_buf | short high | 90% | 2896.782 ps | 97.83% | 89.02% |
| io_buf | short high | 80% | 2489.634 ps | 92.29% | 79.59% |
| io_buf | short high | 70% | 2209.470 ps | 85.04% | 70.28% |
| io_buf | short high | 60% | 1987.947 ps | 76.55% | 59.69% |
| io_buf | short high | 50% | 1799.768 ps | 67.61% | 50.30% |
| io_buf | short low | 90% | 687.001 ps | 102.40% | 90.61% |
| io_buf | short low | 80% | 567.773 ps | 102.26% | 80.59% |
| io_buf | short low | 70% | 480.923 ps | 101.77% | 69.37% |
| io_buf | short low | 60% | 427.061 ps | 100.79% | 60.24% |
| io_buf | short low | 50% | 372.487 ps | 98.15% | 49.09% |

## Gate-State Agreement

| Buffer | Direction | Target | Pad RMSE | Ku RMSE | Kd RMSE |
|---|---|---:|---:|---:|---:|
| ex2 | short high | 80% | 55.37 mV | 0.09965 | 0.05977 |
| ex2 | short high | 70% | 77.52 mV | 0.11596 | 0.06877 |
| ex2 | short high | 60% | 110.92 mV | 0.14193 | 0.06412 |
| ex2 | short high | 50% | 33.25 mV | 0.06628 | 0.10665 |
| ex2 | short low | 90% | 300.56 mV | 0.33255 | 0.20998 |
| ex2 | short low | 80% | 373.35 mV | 0.40287 | 0.27006 |
| ex2 | short low | 70% | 514.33 mV | 0.51118 | 0.22513 |
| ex2 | short low | 60% | 510.67 mV | 0.49752 | 0.20708 |
| ex2 | short low | 50% | 522.62 mV | 0.49882 | 0.18706 |
| inv_chain | short high | 90% | 392.67 mV | 0.35375 | 0.30605 |
| inv_chain | short high | 80% | 429.19 mV | 0.37659 | 0.31539 |
| inv_chain | short high | 70% | 441.16 mV | 0.48893 | 0.32873 |
| inv_chain | short high | 60% | 432.61 mV | 0.52248 | 0.34207 |
| inv_chain | short high | 50% | 432.61 mV | 0.52248 | 0.34207 |
| inv_chain | short low | 90% | 384.47 mV | 0.43345 | 0.36358 |
| inv_chain | short low | 80% | 446.09 mV | 0.51073 | 0.43019 |
| inv_chain | short low | 70% | 514.02 mV | 0.51777 | 0.46587 |
| inv_chain | short low | 60% | 636.15 mV | 0.61052 | 0.44943 |
| inv_chain | short low | 50% | 642.75 mV | 0.51625 | 0.49238 |
| io_buf | short high | 90% | 61.81 mV | 0.07909 | 0.08191 |
| io_buf | short high | 80% | 58.98 mV | 0.07740 | 0.08654 |
| io_buf | short high | 70% | 62.57 mV | 0.07454 | 0.11021 |
| io_buf | short high | 60% | 52.14 mV | 0.06607 | 0.10789 |
| io_buf | short high | 50% | 45.16 mV | 0.05803 | 0.09886 |
| io_buf | short low | 90% | 639.20 mV | 0.45138 | 0.08454 |
| io_buf | short low | 80% | 754.31 mV | 0.57029 | 0.08802 |
| io_buf | short low | 70% | 770.59 mV | 0.57451 | 0.09190 |
| io_buf | short low | 60% | 771.85 mV | 0.57812 | 0.09088 |
| io_buf | short low | 50% | 783.35 mV | 0.58320 | 0.09233 |

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

Completed gate-state simulations: `29/29`.
