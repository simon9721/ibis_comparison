# Three-Buffer Stressed PRBS7: Pad-Matched Replay V2

## Fixed Bench

- Fast-edge IBIS profile for all three buffers.
- Deterministic PRBS7 (`x^7 + x^6 + 1`), 31 analyzed bits containing every three-bit history.
- Input rise/fall: `50 ps`; direct load: `50 ohm || 2 pF`.
- Per-buffer UI is selected so native-IBIS Ku/Kd includes measured 10%-90% mid-transition reversals.
- HSPICE native IBIS provides pad and Ku/Kd; HSPICE transistor SPICE provides pad only.
- ngspice flows: unchanged legacy pybis and `InputDrivenPadMatchedReplayV2`.

## Selected Data Rates

| Buffer | UI | Data rate | Native transitions | Mid-transition | V2 active | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| io_buf | 2000 ps | 0.500 Gb/s | 9 | 6 (66.7%) | 4 | 2 |
| inv_chain | 275 ps | 3.636 Gb/s | 9 | 3 (33.3%) | 9 | 0 |
| ex2 | 1000 ps | 1.000 Gb/s | 9 | 4 (44.4%) | 6 | 4 |

## Trigger Audit

A correct PRBS retrigger detector must activate on native mid-transition reversals and return to legacy replay afterward.

| Buffer | Native stressed | Correct activations | Missed stressed | False activations | Ambiguous |
|---|---:|---:|---:|---:|---:|
| io_buf | 6 | 3 | 3 | 1 | 2 |
| inv_chain | 3 | 3 | 0 | 6 | 0 |
| ex2 | 4 | 4 | 0 | 2 | 4 |

## Correlation

| Buffer | Flow | Pad RMSE | Ku RMSE | Kd RMSE | Eye height |
|---|---|---:|---:|---:|---:|
| io_buf | legacy | 133.76 mV | 0.0954 | 0.1210 | 0.8666 V |
| io_buf | pad_match_v2 | 95.04 mV | 0.0697 | 0.2480 | 0.7858 V |
| inv_chain | legacy | 151.98 mV | 0.1370 | 0.1222 | 1.3660 V |
| inv_chain | pad_match_v2 | 663.24 mV | 0.5009 | 0.5100 | 0.7422 V |
| ex2 | legacy | 79.65 mV | 0.1104 | 0.0817 | 1.4371 V |
| ex2 | pad_match_v2 | 448.53 mV | 0.3437 | 0.3846 | -0.5334 V |

## Headline Finding

- Pad, Ku, and Kd all improve together versus legacy in `0/3` stressed PRBS cases.
- Total native mid-transition events: `13`.
- Pad-V2 mapping ambiguities: `6` transition events.
- The V2 trigger is not sequence-safe yet: `io_buf` misses stressed events, while `inv_chain` and `ex2` retain the pad-map path across settled transitions.
- This persistent activation explains the severe early/incorrect responses in `inv_chain` and `ex2`; it is an algorithm-state failure, not an HSPICE/ngspice convergence problem.
- Read the coefficient panels with the pad panel: an open eye or lower pad error is not sufficient when Ku/Kd diverge.

## Figures And Data

- `00_three_buffer_prbs_contact_sheet.png`: sequence-level overview for all buffers.
- `figures/<buffer>/01_prbs_sequence.png`: input, pad, Ku, and Kd; orange bands mark native mid-transition reversals.
- `figures/<buffer>/02_midtransition_event.png`: the event closest to 50% native progress.
- `figures/<buffer>/03_pad_match_diagnostics.png`: sampled pad, inferred replay start, replay timer, active and ambiguity flags.
- `figures/<buffer>/04_pad_eyes.png`: clean native-IBIS, transistor, and pad-V2 eyes.
- `waveforms/<buffer>.csv`: numeric data behind the figures.
- `stress_events.csv`: every PRBS reversal and its native Ku/Kd progress.
- `activation_audit.csv`: correct, missed, and false V2 activations by buffer.
- `metrics.csv`: sequence RMSE and eye metrics.
- `run_manifest.csv`: simulator status plus cache/run provenance.

Completed simulator flows: `12/12`.
