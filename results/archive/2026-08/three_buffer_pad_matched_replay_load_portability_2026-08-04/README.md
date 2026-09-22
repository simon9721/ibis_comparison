# Three-Buffer Pad-Voltage-Matched Replay

This is an experimental fixed-bench replay study. The pad map is calibrated from legacy pybis at `50 ohm || 2 pF`; HSPICE is validation only.

## Algorithm

- At a reverse edge, sample pad voltage once. The slew-aware variant also samples the magnitude of the pre-edge pad slope.
- Invert the opposite-transition calibration trajectory to obtain one shared replay start time.
- Replay the original aligned Ku/Kd table pair from `latched_start + fresh_elapsed_time`.
- There is no continuous pad feedback. Legacy pybis remains active outside detected interrupted transitions.

## Interpretation

- `COEFFICIENT_AND_PAD_IMPROVED` is the only positive short-pulse result.
- `PAD_ONLY_FALSE_PASS` means output voltage improved while Ku or Kd became less correct.
- `PAD_MAPPING_AMBIGUOUS` means the same pad voltage maps to target-table times separated by more than 0.5 ns.
- Load-matrix results test portability of a map calibrated only at 50 ohm || 2 pF.

## Headline Result

- Pad-flow short-pulse rows: `192`; all-three improvements: `46` (`0` short-high, `46` short-low).
- Mapping-ambiguous rows: `17`. Numeric failures across all flows: `8`.
- A positive row is scoped to its tested direction and load. It does not promote the method as a general state model.
- Legacy `InputDriven` was regenerated and SHA-256 compared for all six device/profile pairs; every model is byte-identical to the pre-experiment copy.

## Summary

| device | profile | flow | cases | loads | pad RMSE mV | Ku RMSE | Kd RMSE | all improved | pad-only | ambiguous | artifact |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| io_buf | slow_1ns | legacy | 24 | 8 | 342.916 | 0.3559 | 0.4905 | 0 | 0 | 0 | 0 |
| io_buf | slow_1ns | coefficient_value_match | 24 | 8 | 15.578 | 0.0200 | 0.4912 | 0 | 10 | 0 | 5 |
| io_buf | slow_1ns | pad_voltage | 24 | 8 | 75.535 | 0.2306 | 0.2649 | 1 | 0 | 5 | 8 |
| io_buf | slow_1ns | pad_slew | 24 | 8 | 74.482 | 0.2301 | 0.4570 | 3 | 0 | 2 | 11 |
| io_buf | fast_5ps | legacy | 24 | 8 | 193.876 | 0.5726 | 0.3827 | 0 | 0 | 0 | 0 |
| io_buf | fast_5ps | coefficient_value_match | 24 | 8 | 69.522 | 0.4172 | 0.3798 | 6 | 10 | 0 | 0 |
| io_buf | fast_5ps | pad_voltage | 22 | 8 | 115.095 | 0.5418 | 0.3018 | 8 | 5 | 5 | 3 |
| io_buf | fast_5ps | pad_slew | 22 | 8 | 135.318 | 0.5521 | 0.3046 | 6 | 7 | 0 | 8 |
| inv_chain | slow_1ns | legacy | 22 | 8 | 530.364 | 0.3864 | 0.3736 | 0 | 0 | 0 | 0 |
| inv_chain | slow_1ns | coefficient_value_match | 24 | 8 | 465.119 | 0.3541 | 0.2757 | 22 | 0 | 0 | 0 |
| inv_chain | slow_1ns | pad_voltage | 24 | 8 | 607.225 | 0.5475 | 0.4057 | 5 | 5 | 0 | 0 |
| inv_chain | slow_1ns | pad_slew | 24 | 8 | 607.116 | 0.5475 | 0.4057 | 5 | 5 | 0 | 0 |
| inv_chain | fast_5ps | legacy | 22 | 8 | 216.104 | 0.3577 | 0.3443 | 0 | 0 | 0 | 0 |
| inv_chain | fast_5ps | coefficient_value_match | 24 | 8 | 335.016 | 0.3161 | 0.2750 | 12 | 0 | 0 | 7 |
| inv_chain | fast_5ps | pad_voltage | 24 | 8 | 501.452 | 0.3887 | 0.3174 | 5 | 0 | 0 | 6 |
| inv_chain | fast_5ps | pad_slew | 24 | 8 | 501.452 | 0.3887 | 0.3174 | 5 | 0 | 0 | 6 |
| ex2 | slow_1ns | legacy | 24 | 8 | 479.389 | 0.4771 | 0.3737 | 0 | 0 | 0 | 0 |
| ex2 | slow_1ns | coefficient_value_match | 24 | 8 | 260.066 | 0.3346 | 0.4877 | 8 | 8 | 0 | 0 |
| ex2 | slow_1ns | pad_voltage | 24 | 8 | 192.715 | 0.3165 | 0.1193 | 8 | 8 | 0 | 0 |
| ex2 | slow_1ns | pad_slew | 24 | 8 | 193.188 | 0.3179 | 0.1193 | 7 | 7 | 2 | 0 |
| ex2 | fast_5ps | legacy | 24 | 8 | 505.488 | 0.4526 | 0.4218 | 0 | 0 | 0 | 0 |
| ex2 | fast_5ps | coefficient_value_match | 24 | 8 | 49.495 | 0.1168 | 0.4814 | 12 | 8 | 0 | 0 |
| ex2 | fast_5ps | pad_voltage | 24 | 8 | 62.722 | 0.2494 | 0.1394 | 9 | 0 | 0 | 8 |
| ex2 | fast_5ps | pad_slew | 24 | 8 | 62.779 | 0.2494 | 0.1394 | 8 | 0 | 3 | 6 |

## Files

- `candidate_metrics.csv`
- `summary_by_device_profile.csv`
- `calibration_manifest.csv`
- `reference_manifest.csv`
- `run_manifest.csv`
- `calibration/*/pad_replay_reference.json`
- `generated_models/`
- `plots/cases/`
- `plots/diagnostics/`
- `waveform_data/`

- `verification/legacy_model_hash_check.csv` (nominal study)

Calibration rows: 6. HSPICE reference rows: 144. Candidate rows: 576.
