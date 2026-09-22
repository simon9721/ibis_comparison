# Three-Buffer Stressed PRBS7: Pad-Matched Replay V2

## Fixed Bench

- Fast-edge IBIS profile for all three buffers.
- Deterministic PRBS7 (`x^7 + x^6 + 1`), 31 analyzed bits containing every three-bit history.
- Input rise/fall: `50 ps`; direct load: `50 ohm || 2 pF`.
- Per-buffer UI is selected by an HSPICE output screen, not by Ku/Kd alone.
- A true output reversal is an isolated one-bit pulse whose native pad turns around after 5%-95% of loaded swing without completing the original full swing.
- HSPICE native IBIS provides pad and Ku/Kd; HSPICE transistor SPICE provides pad only.
- ngspice flows: unchanged legacy pybis and `InputDrivenPadMatchedReplayV2`.

## Selected Data Rates

| Buffer | UI | Data rate | Native transitions | True output reversals | V2 active | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| io_buf | 1750 ps | 0.571 Gb/s | 9 | 2 (22.2%) | 4 | 2 |
| inv_chain | 100 ps | 10.000 Gb/s | 9 | 1 (11.1%) | 9 | 3 |
| ex2 | 750 ps | 1.333 Gb/s | 9 | 1 (11.1%) | 6 | 3 |

## Trigger Audit

A correct PRBS retrigger detector must activate on true native output reversals and return to legacy replay afterward.

| Buffer | True output reversals | Correct activations | Missed reversals | False activations | Ambiguous |
|---|---:|---:|---:|---:|---:|
| io_buf | 2 | 2 | 0 | 2 | 2 |
| inv_chain | 1 | 1 | 0 | 8 | 3 |
| ex2 | 1 | 1 | 0 | 5 | 3 |

## Correlation

| Buffer | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Eye height |
|---|---|---:|---:|---:|---:|
| io_buf | legacy | 172.59 mV | 0.1192 | 0.1381 | 0.6973 V |
| io_buf | pad_match_v2 | 130.43 mV | 0.0917 | 0.2829 | 0.5221 V |
| inv_chain | legacy | 505.86 mV | 0.4173 | 0.3776 | -0.4826 V |
| inv_chain | pad_match_v2 | 663.64 mV | 0.5303 | 0.5783 | 0.0011 V |
| ex2 | legacy | 252.57 mV | 0.2378 | 0.1833 | 1.1343 V |
| ex2 | pad_match_v2 | 465.47 mV | 0.3856 | 0.4061 | -0.7074 V |

## Headline Finding

- Pad, Ku, and Kd all improve together versus legacy in `0/3` stressed PRBS cases.
- Total true native output-reversal events: `4`.
- Pad-V2 mapping ambiguities: `8` transition events.
- Pad-V2 numeric failures: `0`.
- Trigger correctness is reported separately as correct, missed, and false activations; a sequence-level pass requires zero misses and zero false activations.
- Persistent activation or a bounded timeout is an algorithm-state/numerical failure even when one isolated event looks reasonable.
- Read the coefficient panels with the pad panel: an open eye or lower pad error is not sufficient when Ku/Kd diverge.

## Figures And Data

- `00_three_buffer_prbs_contact_sheet.png`: sequence-level overview for all buffers.
- `figures/<buffer>/01_prbs_sequence.png`: input, pad, Ku, and Kd; orange bands mark true native output reversals.
- `figures/<buffer>/02_midtransition_event.png`: the true output reversal closest to 50% excursion.
- `figures/<buffer>/03_pad_match_diagnostics.png`: sampled pad, inferred replay start, replay timer, active and ambiguity flags.
- `figures/<buffer>/04_pad_eyes.png`: clean native-IBIS, transistor, and pad-V2 eyes.
- `waveforms/<buffer>.csv`: numeric data behind the figures.
- `stress_events.csv`: every PRBS reversal and its native Ku/Kd progress.
- `activation_audit.csv`: correct, missed, and false V2 activations by buffer.
- `metrics.csv`: sequence RMSE and eye metrics.
- `run_manifest.csv`: simulator status plus cache/run provenance.

Completed simulator flows: `12/12`.
