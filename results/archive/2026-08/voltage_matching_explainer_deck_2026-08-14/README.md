# Voltage Matching V2 Explainer Deck

This package explains the cached-data Voltage Matching V2 experiment and the delayed-sampling extension.

## Main Deliverable

- `Voltage_Matching_V2_Explainer_2026-08-14.pptx`
- `Voltage_Matching_V2_Explainer_2026-08-14.pdf`: PowerPoint-rendered review copy.
- `Voltage_Matching_V2_Explainer_contact_sheet.png`: all slides at a glance.
- `rendered_slides/`: one 1600 x 900 PNG per slide.

## Evidence Policy

- Original V2 figures use cached full-swing calibration and interrupted-event waveforms.
- HSPICE was not rerun for this deck.
- Delayed-sampling slides use real IBIS-derived delay parameters, but do not claim an unfinished delayed waveform result.

## Figures

- `figures/01_short_pulse_problem_inv_chain.png`
- `figures/02_full_swing_calibration_io_buf.png`
- `figures/03_voltage_to_time_inverse_mapping_io_buf.png`
- `figures/04_runtime_sample_latch_replay_io_buf.png`
- `figures/05_runtime_kukd_replay_io_buf.png`
- `figures/06_inv_chain_propagation_delay_and_mapping_ambiguity.png`
- `figures/07_three_buffer_voltage_matching_summary.png`
- `figures/08_delayed_voltage_sampling_design.png`

## Rebuild

```powershell
$env:PYTHONPATH = ".codex_deps/presentation/python;."
py -3.14 scripts/build_voltage_matching_explainer_deck.py
```
