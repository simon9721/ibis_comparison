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

- Pad-flow short-pulse rows: `2`; all-three improvements: `0` (`0` short-high, `0` short-low).
- Mapping-ambiguous rows: `1`. Numeric failures across all flows: `0`.
- A positive row is scoped to its tested direction and load. It does not promote the method as a general state model.
- Legacy `InputDriven` was regenerated and SHA-256 compared for all six device/profile pairs; every model is byte-identical to the pre-experiment copy.

## Summary

| device | profile | flow | cases | loads | pad RMSE mV | Ku RMSE | Kd RMSE | all improved | pad-only | ambiguous | artifact |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| inv_chain | fast_5ps | legacy | 1 | 1 | 847.865 | 0.4774 | 0.3627 | 0 | 0 | 0 | 0 |
| inv_chain | fast_5ps | coefficient_value_match | 1 | 1 | 488.374 | 0.4901 | 0.5674 | 0 | 1 | 0 | 0 |
| inv_chain | fast_5ps | pad_voltage | 1 | 1 | 816.627 | 0.4665 | 0.3483 | 0 | 0 | 1 | 0 |
| inv_chain | fast_5ps | pad_slew | 1 | 1 | 594.875 | 0.5640 | 0.7032 | 0 | 1 | 0 | 0 |

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

Calibration rows: 1. HSPICE reference rows: 2. Candidate rows: 4.
