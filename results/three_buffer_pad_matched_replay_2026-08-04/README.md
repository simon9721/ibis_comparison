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

- Pad-flow short-pulse rows: `96`; all-three improvements: `14` (`0` short-high, `14` short-low).
- Mapping-ambiguous rows: `16`. Numeric failures across all flows: `3`.
- A positive row is scoped to its tested direction and load. It does not promote the method as a general state model.

## Summary

| device | profile | flow | cases | loads | pad RMSE mV | Ku RMSE | Kd RMSE | all improved | pad-only | ambiguous | artifact |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| io_buf | slow_1ns | legacy | 9 | 1 | 478.637 | 0.3522 | 0.4568 | 0 | 0 | 0 | 0 |
| io_buf | slow_1ns | coefficient_value_match | 9 | 1 | 19.343 | 0.0216 | 0.4980 | 1 | 4 | 0 | 1 |
| io_buf | slow_1ns | pad_voltage | 9 | 1 | 236.288 | 0.2592 | 0.3243 | 0 | 0 | 2 | 3 |
| io_buf | slow_1ns | pad_slew | 9 | 1 | 241.615 | 0.2586 | 0.4238 | 1 | 1 | 3 | 2 |
| io_buf | fast_5ps | legacy | 9 | 1 | 262.343 | 0.5558 | 0.3822 | 0 | 0 | 0 | 0 |
| io_buf | fast_5ps | coefficient_value_match | 8 | 1 | 134.009 | 0.4064 | 0.3858 | 1 | 3 | 0 | 0 |
| io_buf | fast_5ps | pad_voltage | 8 | 1 | 128.330 | 0.5088 | 0.3107 | 3 | 0 | 2 | 3 |
| io_buf | fast_5ps | pad_slew | 8 | 1 | 147.973 | 0.5368 | 0.2914 | 2 | 0 | 1 | 5 |
| inv_chain | slow_1ns | legacy | 9 | 1 | 283.309 | 0.3594 | 0.3454 | 0 | 0 | 0 | 0 |
| inv_chain | slow_1ns | coefficient_value_match | 9 | 1 | 480.580 | 0.3740 | 0.3338 | 7 | 0 | 0 | 1 |
| inv_chain | slow_1ns | pad_voltage | 9 | 1 | 702.254 | 0.4547 | 0.4053 | 1 | 2 | 2 | 1 |
| inv_chain | slow_1ns | pad_slew | 9 | 1 | 702.258 | 0.4547 | 0.3618 | 1 | 2 | 1 | 1 |
| inv_chain | fast_5ps | legacy | 9 | 1 | 277.041 | 0.3660 | 0.3501 | 0 | 0 | 0 | 0 |
| inv_chain | fast_5ps | coefficient_value_match | 9 | 1 | 338.168 | 0.3575 | 0.3545 | 5 | 1 | 0 | 2 |
| inv_chain | fast_5ps | pad_voltage | 9 | 1 | 682.250 | 0.4029 | 0.4335 | 1 | 0 | 0 | 2 |
| inv_chain | fast_5ps | pad_slew | 9 | 1 | 682.322 | 0.4029 | 0.3204 | 1 | 0 | 0 | 2 |
| ex2 | slow_1ns | legacy | 9 | 1 | 640.332 | 0.4317 | 0.3526 | 0 | 0 | 0 | 0 |
| ex2 | slow_1ns | coefficient_value_match | 9 | 1 | 398.469 | 0.3368 | 0.4701 | 3 | 1 | 0 | 1 |
| ex2 | slow_1ns | pad_voltage | 9 | 1 | 348.688 | 0.3784 | 0.3373 | 2 | 1 | 0 | 3 |
| ex2 | slow_1ns | pad_slew | 9 | 1 | 348.693 | 0.3784 | 0.3373 | 2 | 1 | 1 | 2 |
| ex2 | fast_5ps | legacy | 9 | 1 | 172.102 | 0.2859 | 0.2291 | 0 | 0 | 0 | 0 |
| ex2 | fast_5ps | coefficient_value_match | 9 | 1 | 56.357 | 0.1171 | 0.4140 | 5 | 2 | 0 | 1 |
| ex2 | fast_5ps | pad_voltage | 9 | 1 | 126.794 | 0.2571 | 0.2215 | 2 | 0 | 2 | 3 |
| ex2 | fast_5ps | pad_slew | 9 | 1 | 340.958 | 0.3176 | 0.3154 | 2 | 0 | 2 | 2 |

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

Calibration rows: 0. HSPICE reference rows: 0. Candidate rows: 216.
