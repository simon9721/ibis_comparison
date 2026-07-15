# io_buf Value-Matched Replay Redo

This is the clean redo of the value-matched replay baseline. It compares HSPICE native IBIS, HSPICE transistor-level `io_buf.sp`, ngspice legacy pybis, and ngspice value-matched pybis.

## Headline

- Required cases: `edge_1ps_base_50r_2pf, short_pulse_1ns_high, short_pulse_2ns_high`
- Long-pulse value-matched pad RMSE delta versus legacy: `0.288 mV`
- Value-match ambiguous cases: `short_pulse_1ns_high`
- Value-matched failed cases: `short_pulse_2ns_high`
- HSPICE transistor-level `io_buf.sp` is pad-only; `Ku/Kd` validation uses HSPICE native IBIS.

## Findings

- Long-pulse control is preserved. Value-matched replay stays close to legacy and HSPICE native IBIS, with only a small pad RMSE increase on the control case.
- `short_pulse_1ns_high` shows the useful part of value matching: pad RMSE drops from legacy's large full-pulse error to a small partial-pulse error, and `Ku` peak moves much closer to HSPICE native IBIS.
- The same `short_pulse_1ns_high` case also shows the core limitation: `Kd` is wrong. The value-matched replay keeps `Kd` too high, so this is not coefficient-correct even though the pad waveform looks much better.
- `short_pulse_2ns_high` is not simulation-ready for this method. The value-matched ngspice run times out, so the method fails the numerical robustness gate for this redo.
- The `short_pulse_2ns_high` timeout was investigated separately. It is not zero-progress: shorter stop-time runs complete through `7.25 ns`, but timestep collapse after the reverse edge prevents the full run from finishing with the default `coeff_tau=1p`.
- The transistor-level `io_buf.sp` reference is useful as a pad-level sanity reference, but it is not expected to match native IBIS exactly because it is a different model abstraction and has no exposed `Ku/Kd`.

## Short-Pulse 1 ns Detail

- HSPICE native IBIS pad peak: `0.0616 V`; transistor `io_buf.sp` pad peak: `0.1281 V`.
- Legacy pybis pad peak: `1.5155 V`; value-matched pad peak: `0.0268 V`.
- HSPICE native IBIS `Ku` peak: `0.0746`; legacy pybis `Ku` peak: `1.0125`; value-matched `Ku` peak: `0.0465`.
- HSPICE native IBIS `Kd` minimum: `-0.0632`; legacy pybis `Kd` minimum: `-0.0718`; value-matched `Kd` minimum: `0.5514`.
- Value-matched inferred falling-table start disagreement reaches `1.871 ns`, so the case is classified as `VALUE_MATCH_AMBIGUOUS`.

## Key Files

- `candidate_metrics.csv`: per-flow metrics.
- `reference_cache_manifest.csv`: HSPICE cache/run source.
- `figures/<case>/01_input_pad_overlay.png`
- `figures/<case>/02_ku_overlay.png`
- `figures/<case>/03_kd_overlay.png`
- `figures/<case>/04_value_match_diagnostics.png`
- `figures/summary_bars.png`
- `timeout_investigation/README.md`: root-cause analysis for the 2 ns value-matched timeout.

## Case Summary

| Case | Flow | Status | Pad RMSE mV | Ku RMSE | Kd RMSE | Pad peak V | Ku peak | Kd min |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.5536 | 1.0129 | -0.0718 |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | PAD_REFERENCE | 525.498 | n/a | n/a | 1.6681 | n/a | n/a |
| edge_1ps_base_50r_2pf | ngspice_legacy | GOOD | 5.289 | 0.00434 | 0.00561 | 1.5569 | 1.0120 | -0.0718 |
| edge_1ps_base_50r_2pf | ngspice_value_matched | GOOD | 5.577 | 0.00436 | 0.00583 | 1.5564 | 1.0108 | -0.0718 |
| short_pulse_1ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.0616 | 0.0746 | -0.0632 |
| short_pulse_1ns_high | hspice_transistor_sp | PAD_REFERENCE | 40.136 | n/a | n/a | 0.1281 | n/a | n/a |
| short_pulse_1ns_high | ngspice_legacy | CHECK | 653.256 | 0.47041 | 0.50381 | 1.5155 | 1.0125 | -0.0718 |
| short_pulse_1ns_high | ngspice_value_matched | VALUE_MATCH_AMBIGUOUS | 24.638 | 0.02586 | 0.63544 | 0.0268 | 0.0465 | 0.5514 |
| short_pulse_2ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.8251 | 0.5432 | -0.0720 |
| short_pulse_2ns_high | hspice_transistor_sp | PAD_REFERENCE | 399.310 | n/a | n/a | 1.2145 | n/a | n/a |
| short_pulse_2ns_high | ngspice_legacy | CHECK | 361.362 | 0.28330 | 0.23142 | 1.5214 | 1.0125 | -0.0724 |
| short_pulse_2ns_high | ngspice_value_matched | FAILED | n/a | n/a | n/a | n/a | n/a | n/a |

## HSPICE Reference Cache

| Case | Reference | Source |
|---|---|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | cache |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | cache |
| short_pulse_1ns_high | hspice_native_ibis | cache |
| short_pulse_1ns_high | hspice_transistor_sp | cache |
| short_pulse_2ns_high | hspice_native_ibis | cache |
| short_pulse_2ns_high | hspice_transistor_sp | cache |

## Interpretation Rule

Pad-only improvement is not enough. The value-matched method must improve `Ku` and `Kd` agreement with HSPICE native IBIS, and cases with large `TF_KU`/`TF_KD` disagreement are classified as `VALUE_MATCH_AMBIGUOUS`.
