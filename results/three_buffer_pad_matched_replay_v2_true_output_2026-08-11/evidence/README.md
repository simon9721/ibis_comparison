# Three-Buffer True Output-Level Reversal Evidence

All cases use the fast-edge IBIS, 50 ps input edges, and a direct 50 ohm || 2 pF load.
The purple line is the input reverse threshold; the orange line is the later native-pad turning point.

| Buffer | Pulse | Native excursion | Transistor excursion | V2 excursion | Pad RMSE | Ku RMSE | Kd RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|
| io_buf | 1750 ps | 47.4% | 65.2% | 59.2% | 62.5 mV | 0.3616 | 0.3155 |
| inv_chain | 100 ps | 90.9% | 26.1% | 100.1% | 816.6 mV | 0.4665 | 0.3483 |
| ex2 | 750 ps | 81.0% | 20.6% | 93.2% | 433.9 mV | 0.4340 | 0.2090 |

- `plots/`: one clean input/pad/Ku/Kd figure per buffer.
- `00_true_output_reversal_contact_sheet.png`: all three cases.
- `true_output_reversal_metrics.csv`: numeric evidence and source waveform paths.
