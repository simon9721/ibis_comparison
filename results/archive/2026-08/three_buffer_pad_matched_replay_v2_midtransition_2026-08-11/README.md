# Three-Buffer Pad-Voltage-Matched Replay

This is the experimental `v2` fixed-bench replay study. The pad map is calibrated from legacy pybis at `50 ohm || 2 pF`; HSPICE is validation only.

## Algorithm

- At a reverse edge, sample pad voltage once. The slew-aware variant also samples the magnitude of the pre-edge pad slope.
- Invert the opposite-transition calibration trajectory to obtain one shared replay start time.
- Replay the original aligned Ku/Kd table pair from `latched_start + fresh_elapsed_time`.
- There is no continuous pad feedback. Legacy pybis remains active outside detected interrupted transitions.
- V2 uses direct legacy Ku/Kd while inactive; only the sample/latch/replay transaction uses held or pad-matched coefficients.

## Interpretation

- `COEFFICIENT_AND_PAD_IMPROVED` is the only positive short-pulse result.
- `PAD_ONLY_FALSE_PASS` means output voltage improved while Ku or Kd became less correct.
- `PAD_MAPPING_AMBIGUOUS` means the same pad voltage maps to target-table times separated by more than 0.5 ns.
- Load-matrix results test portability of a map calibrated only at 50 ohm || 2 pF.

## Headline Result

- Pad-flow short-pulse rows: `96`; all-three improvements: `12` (`3` short-high, `9` short-low).
- Mapping-ambiguous rows: `34`. Numeric failures across all flows: `1`.
- A positive row is scoped to its tested direction and load. It does not promote the method as a general state model.
- Legacy `InputDriven` was regenerated and SHA-256 compared for all six device/profile pairs; every model is byte-identical to the pre-experiment copy.

## Summary

| device | profile | flow | cases | loads | pad RMSE mV | Ku RMSE | Kd RMSE | all improved | pad-only | ambiguous | artifact |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| io_buf | slow_1ns | legacy | 9 | 1 | 478.637 | 0.3522 | 0.4568 | 0 | 0 | 0 | 0 |
| io_buf | slow_1ns | coefficient_value_match | 9 | 1 | 19.343 | 0.0216 | 0.4980 | 1 | 4 | 0 | 1 |
| io_buf | slow_1ns | pad_voltage | 9 | 1 | 533.076 | 0.3685 | 0.4423 | 1 | 0 | 1 | 4 |
| io_buf | slow_1ns | pad_slew | 9 | 1 | 463.261 | 0.3295 | 0.4768 | 1 | 1 | 1 | 4 |
| io_buf | fast_5ps | legacy | 9 | 1 | 262.343 | 0.5558 | 0.3822 | 0 | 0 | 0 | 0 |
| io_buf | fast_5ps | coefficient_value_match | 8 | 1 | 134.009 | 0.4064 | 0.3858 | 1 | 3 | 0 | 0 |
| io_buf | fast_5ps | pad_voltage | 9 | 1 | 123.612 | 0.4708 | 0.2947 | 3 | 0 | 3 | 2 |
| io_buf | fast_5ps | pad_slew | 9 | 1 | 90.570 | 0.4750 | 0.3549 | 2 | 0 | 5 | 1 |
| inv_chain | slow_1ns | legacy | 9 | 1 | 283.309 | 0.3594 | 0.3454 | 0 | 0 | 0 | 0 |
| inv_chain | slow_1ns | coefficient_value_match | 9 | 1 | 480.580 | 0.3740 | 0.3338 | 7 | 0 | 0 | 1 |
| inv_chain | slow_1ns | pad_voltage | 9 | 1 | 717.164 | 0.4598 | 0.3740 | 0 | 0 | 4 | 1 |
| inv_chain | slow_1ns | pad_slew | 9 | 1 | 717.679 | 0.4574 | 0.3741 | 2 | 1 | 3 | 1 |
| inv_chain | fast_5ps | legacy | 9 | 1 | 277.041 | 0.3660 | 0.3501 | 0 | 0 | 0 | 0 |
| inv_chain | fast_5ps | coefficient_value_match | 9 | 1 | 338.168 | 0.3575 | 0.3545 | 5 | 1 | 0 | 2 |
| inv_chain | fast_5ps | pad_voltage | 9 | 1 | 670.039 | 0.4178 | 0.4472 | 0 | 0 | 1 | 2 |
| inv_chain | fast_5ps | pad_slew | 9 | 1 | 669.920 | 0.4178 | 0.3550 | 0 | 3 | 0 | 0 |
| ex2 | slow_1ns | legacy | 9 | 1 | 640.332 | 0.4317 | 0.3526 | 0 | 0 | 0 | 0 |
| ex2 | slow_1ns | coefficient_value_match | 9 | 1 | 398.469 | 0.3368 | 0.4701 | 3 | 1 | 0 | 1 |
| ex2 | slow_1ns | pad_voltage | 9 | 1 | 730.733 | 0.4770 | 0.3299 | 0 | 0 | 6 | 2 |
| ex2 | slow_1ns | pad_slew | 9 | 1 | 730.885 | 0.4770 | 0.3455 | 1 | 1 | 3 | 3 |
| ex2 | fast_5ps | legacy | 9 | 1 | 172.102 | 0.2859 | 0.2291 | 0 | 0 | 0 | 0 |
| ex2 | fast_5ps | coefficient_value_match | 9 | 1 | 56.357 | 0.1171 | 0.4140 | 5 | 2 | 0 | 1 |
| ex2 | fast_5ps | pad_voltage | 9 | 1 | 536.196 | 0.3336 | 0.2247 | 2 | 0 | 3 | 2 |
| ex2 | fast_5ps | pad_slew | 9 | 1 | 535.780 | 0.3338 | 0.3224 | 0 | 1 | 4 | 2 |

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

Calibration rows: 6. HSPICE reference rows: 108. Candidate rows: 216.
