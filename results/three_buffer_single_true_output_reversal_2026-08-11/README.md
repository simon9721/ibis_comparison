# Three-Buffer Single True Output-Level Reversal

This package contains isolated short-high and short-low pulses only. No PRBS results are included.
All cases use the fast-edge IBIS profile, 50 ps input edges, and a direct 50 ohm || 2 pF load.
Pulse widths are selected against 50% of the HSPICE transistor buffer's measured loaded swing, not raw VDD.

## Selected Cases

| Buffer | Direction | Pulse | Transistor excursion | Native-IBIS excursion | Native partial reversal |
|---|---|---:|---:|---:|---|
| io_buf | short high | 1503.9 ps | 49.9% | 29.6% | True |
| io_buf | short low | 162.5 ps | 49.9% | 8.8% | True |
| inv_chain | short high | 103.5 ps | 51.0% | 91.9% | True |
| inv_chain | short low | 110.2 ps | 48.1% | 88.6% | True |
| ex2 | short high | 808.6 ps | 49.5% | 85.1% | True |
| ex2 | short low | 689.1 ps | 50.4% | 94.9% | True |

## Compared Models

- `voltage-matching`: `InputDrivenPadMatchedReplayV2`.
- `gate state model`: `InputDrivenTwoStateGateDirectionalDualResidualFull`.
- `hybrid`: `InputDrivenTwoStateGateDirectionalDualResidualHybrid`; legacy replay normally, gate-state path during detected reversal.
- HSPICE native IBIS supplies pad, Ku, and Kd. HSPICE transistor supplies pad only.
- The hybrid reversal branch activated in every selected event; these are not inactive legacy-path comparisons.

## Why The Target Is Loaded-Swing Midpoint

With the fixed 50 ohm load, the fully settled transistor outputs are below VDD. For io_buf and ex2 they are also below 0.5*VDD, so a literal 50% VDD peak is unreachable without changing the bench. The study therefore targets 50% of each transistor buffer's own measured loaded swing, which is the comparable electrical midpoint.

## Figure Markers

- Purple dashed line: the instant the input crosses its threshold on the reverse edge.
- Green horizontal line: 50% of the transistor reference's measured loaded output swing.

## Candidate Metrics

| Buffer | Direction | Model | Pad RMSE | Ku RMSE | Kd RMSE | Output excursion |
|---|---|---|---:|---:|---:|---:|
| io_buf | short high | voltage-matching | 56.3 mV | 0.4324 | 0.3391 | 41.3% |
| io_buf | short high | gate state model | 644.9 mV | 0.4653 | 0.3565 | 185.9% |
| io_buf | short high | hybrid | 157.2 mV | 0.4098 | 0.1914 | 65.0% |
| io_buf | short low | voltage-matching | 111.9 mV | 0.4676 | 0.2916 | 38.3% |
| io_buf | short low | gate state model | 367.5 mV | 0.5804 | 0.3839 | 138.8% |
| io_buf | short low | hybrid | 369.4 mV | 0.5432 | 0.3752 | 114.0% |
| inv_chain | short high | voltage-matching | 851.4 mV | 0.4930 | 0.3347 | 100.2% |
| inv_chain | short high | gate state model | 316.0 mV | 0.3453 | 0.2870 | 62.3% |
| inv_chain | short high | hybrid | 340.3 mV | 0.3036 | 0.2891 | 65.3% |
| inv_chain | short low | voltage-matching | 618.2 mV | 0.5330 | 0.3737 | 26.2% |
| inv_chain | short low | gate state model | 310.4 mV | 0.4217 | 0.3412 | 101.0% |
| inv_chain | short low | hybrid | 297.7 mV | 0.3849 | 0.2886 | 101.1% |
| ex2 | short high | voltage-matching | 379.4 mV | 0.4020 | 0.1584 | 93.1% |
| ex2 | short high | gate state model | 43.7 mV | 0.0877 | 0.0535 | 82.5% |
| ex2 | short high | hybrid | 60.7 mV | 0.0969 | 0.0780 | 81.1% |
| ex2 | short low | voltage-matching | 638.5 mV | 0.4711 | 0.2121 | 12.2% |
| ex2 | short low | gate state model | 224.7 mV | 0.2457 | 0.1670 | 100.5% |
| ex2 | short low | hybrid | 223.8 mV | 0.2437 | 0.1776 | 100.4% |

## Main Findings

- Short-high: io_buf favors voltage-matching at the pad, inv_chain favors the gate-state/hybrid family, and ex2 is strongest with the full gate-state model. None is coefficient-correct across all three buffers.
- Short-low: io_buf again has the lowest pad RMSE with voltage-matching, while inv_chain and ex2 favor the gate-state/hybrid family. Their gate-state outputs generally complete or over-complete the swing rather than preserving the selected partial event.
- The transistor-selected 50% pulse does not imply a 50% native-IBIS response: short-low native excursions range from 8.8% for io_buf to 94.9% for ex2. The two references therefore remain separate in every figure.
- No one method wins across all three buffers, so none is ready as a general interrupted-transition replacement.

## Files

- `00_midpoint_pulse_selection.png`: pulse-width refinement to the transistor 50% point.
- `01_three_buffer_contact_sheet.png`: all three isolated comparisons.
- `figures/`: one input/pad/Ku/Kd figure per buffer and direction.
- `02_coefficient_direction_contact_sheet.png`: Ku/Kd direction-change markers for all buffers.
- `03_short_low_midpoint_pulse_selection.png`: short-low transistor midpoint refinement.
- `04_short_low_contact_sheet.png`: all three short-low isolated comparisons.
- `05_short_low_coefficient_direction_contact_sheet.png`: short-low Ku/Kd direction changes.
- `06_voltage_matching_short_high_contact_sheet.png`: voltage-matching-only short-high evidence.
- `07_voltage_matching_short_low_contact_sheet.png`: voltage-matching-only short-low evidence.
- `voltage_matching_only/`: sampled pad voltage, opposite-trajectory mapping, and Ku/Kd replay for every selected event.
- `voltage_matching_mapping_events.csv`: numeric sampled voltage and inferred opposite-table starting point.
- `coefficient_direction/`: one Ku/Kd direction-change figure per buffer and direction.
- `coefficient_turn_times.csv`: exact coefficient extrema relative to the input reverse threshold.
- `waveforms/`: numeric data behind each figure.
- `selection.csv`: midpoint selection evidence.
- `candidate_metrics.csv`: pad and coefficient correlation.
- `run_manifest.csv`: simulator completion and provenance.

Completed ngspice flows: `27/27`.
