# io_buf Corrected Value-Matched Replay v2

This study fixes the v1 value-matched timer bug and tests whether table retiming is enough to handle interrupted short pulses. HSPICE references are restored from cache when unchanged; they are validation references only.

## Headline

- Required cases: `edge_1ps_base_50r_2pf, short_pulse_500ps_high, short_pulse_1ns_high, short_pulse_2ns_high, double_toggle_1ps`
- Long-pulse v2 balanced pad RMSE delta versus legacy: `-0.078 mV`
- V2 ambiguous rows: `short_pulse_500ps_high:ngspice_v2_balanced, short_pulse_500ps_high:ngspice_v2_ku_only, short_pulse_500ps_high:ngspice_v2_kd_only, short_pulse_500ps_high:ngspice_v2_split, short_pulse_1ns_high:ngspice_v2_balanced, short_pulse_1ns_high:ngspice_v2_ku_only, short_pulse_1ns_high:ngspice_v2_kd_only, short_pulse_1ns_high:ngspice_v2_split, short_pulse_2ns_high:ngspice_v2_balanced, short_pulse_2ns_high:ngspice_v2_ku_only, short_pulse_2ns_high:ngspice_v2_kd_only, short_pulse_2ns_high:ngspice_v2_split, double_toggle_1ps:ngspice_v2_balanced, double_toggle_1ps:ngspice_v2_ku_only, double_toggle_1ps:ngspice_v2_kd_only, double_toggle_1ps:ngspice_v2_split`
- V2 numeric-fail rows: `none`
- `short_pulse_2ns_high` completed v2 flows: `ngspice_v2_balanced, ngspice_v2_ku_only, ngspice_v2_kd_only, ngspice_v2_split`
- HSPICE transistor-level `io_buf.sp` is pad-only; `Ku/Kd` validation uses HSPICE native IBIS.

## What Changed From v1

- V1 computed `VMARG = VMSTART + HNX`, which mixed a new value-matched start with the old legacy elapsed timer.
- V2 latches `VMSTART_LATCH`, latches reverse-edge time as `VMT0`, and computes `VMARG = VMSTART_LATCH + VMELAPSED`.
- V2 keeps `HPREHOLD` asserted from reverse-edge detection until value-match replay takes over, so `KUTARGET/KDTARGET` cannot briefly fall back to legacy replay between latch phases.
- V2 also tests Ku-only, Kd-only, and split Ku/Kd starts to separate a timer bug from true Ku/Kd table-start ambiguity.

## Short-Pulse 1 ns Detail

- HSPICE native IBIS pad peak: `0.0616 V`; transistor `io_buf.sp` pad peak: `0.1281 V`.
- Legacy pybis pad peak: `1.5155 V`; v1 pad peak: `0.0420 V`; v2 balanced pad peak: `0.0129 V`.
- HSPICE `Ku` peak: `0.0746`; legacy: `1.0125`; v1: `0.0466`; v2 balanced: `0.0310`.
- HSPICE `Kd` minimum: `-0.0632`; legacy: `-0.0718`; v1: `0.0115`; v2 balanced: `0.9180`.
- V2 balanced start disagreement: `2.481 ns`; v2 balanced match-active VMARG backstep: `0 ns`.

## Key Files

- `candidate_metrics.csv`: per-flow metrics.
- `reference_cache_manifest.csv`: HSPICE cache/run source.
- `figures/<case>/01_input_pad_overlay.png`
- `figures/<case>/02_ku_overlay.png`
- `figures/<case>/03_kd_overlay.png`
- `figures/<case>/04_value_match_snapshot.png`
- `figures/<case>/05_timer_diagnostics.png`
- `figures/<case>/06_summary_bars.png`
- `figures/summary_bars.png`

## Case Summary

| Case | Flow | Status | Pad RMSE mV | Ku RMSE | Kd RMSE | Pad peak V | Ku peak | Kd min | Start disagree ns | Active VMARG backstep ns |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.5536 | 1.0129 | -0.0718 | n/a | n/a |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | PAD_REFERENCE | 525.498 | n/a | n/a | 1.6681 | n/a | n/a | n/a | n/a |
| edge_1ps_base_50r_2pf | ngspice_legacy | GOOD | 5.289 | 0.00434 | 0.00561 | 1.5569 | 1.0120 | -0.0718 | n/a | n/a |
| edge_1ps_base_50r_2pf | ngspice_value_matched_v1 | GOOD | 5.577 | 0.00436 | 0.00583 | 1.5564 | 1.0108 | -0.0718 | 2.090 | 0 |
| edge_1ps_base_50r_2pf | ngspice_v2_balanced | GOOD | 5.211 | 0.00392 | 0.00561 | 1.5575 | 1.0125 | -0.0718 | 1.871 | 0 |
| edge_1ps_base_50r_2pf | ngspice_v2_ku_only | GOOD | 5.211 | 0.00392 | 0.00561 | 1.5575 | 1.0125 | -0.0718 | 1.871 | 0 |
| edge_1ps_base_50r_2pf | ngspice_v2_kd_only | GOOD | 5.211 | 0.00392 | 0.00561 | 1.5575 | 1.0125 | -0.0718 | 1.871 | 0 |
| edge_1ps_base_50r_2pf | ngspice_v2_split | GOOD | 5.211 | 0.00392 | 0.00561 | 1.5575 | 1.0125 | -0.0718 | 1.871 | 0 |
| short_pulse_500ps_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.0478 | 0.0466 | -0.0225 | n/a | n/a |
| short_pulse_500ps_high | hspice_transistor_sp | PAD_REFERENCE | 30.529 | n/a | n/a | 0.0426 | n/a | n/a | n/a | n/a |
| short_pulse_500ps_high | ngspice_legacy | CHECK | 678.863 | 0.50245 | 0.57847 | 1.5154 | 1.0125 | -0.0717 | n/a | n/a |
| short_pulse_500ps_high | ngspice_value_matched_v1 | VALUE_MATCH_AMBIGUOUS | 23.320 | 0.02662 | 0.59214 | 0.0360 | 0.0465 | 0.2490 | 2.123 | 0.48 |
| short_pulse_500ps_high | ngspice_v2_balanced | VALUE_MATCH_AMBIGUOUS | 20.176 | 0.02191 | 0.59158 | 0.0118 | 0.0276 | 0.9470 | 2.171 | 0 |
| short_pulse_500ps_high | ngspice_v2_ku_only | VALUE_MATCH_AMBIGUOUS | 24.369 | 0.02598 | 0.51061 | 0.0475 | 0.0464 | -0.0201 | 2.171 | 0 |
| short_pulse_500ps_high | ngspice_v2_kd_only | VALUE_MATCH_AMBIGUOUS | 22.683 | 0.02382 | 0.66307 | 0.0475 | 0.0469 | -0.0182 | 2.171 | 0 |
| short_pulse_500ps_high | ngspice_v2_split | VALUE_MATCH_AMBIGUOUS | 21.589 | 0.02598 | 0.59247 | 0.0275 | 0.0464 | 0.9978 | 2.171 | 0 |
| short_pulse_1ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.0616 | 0.0746 | -0.0632 | n/a | n/a |
| short_pulse_1ns_high | hspice_transistor_sp | PAD_REFERENCE | 40.136 | n/a | n/a | 0.1281 | n/a | n/a | n/a | n/a |
| short_pulse_1ns_high | ngspice_legacy | CHECK | 653.256 | 0.47041 | 0.50381 | 1.5155 | 1.0125 | -0.0718 | n/a | n/a |
| short_pulse_1ns_high | ngspice_value_matched_v1 | VALUE_MATCH_AMBIGUOUS | 22.503 | 0.02309 | 0.63267 | 0.0420 | 0.0466 | 0.0115 | 2.476 | 0.98 |
| short_pulse_1ns_high | ngspice_v2_balanced | VALUE_MATCH_AMBIGUOUS | 25.579 | 0.02652 | 0.63487 | 0.0129 | 0.0310 | 0.9180 | 2.481 | 0 |
| short_pulse_1ns_high | ngspice_v2_ku_only | VALUE_MATCH_AMBIGUOUS | 26.905 | 0.03036 | 0.51664 | 0.0475 | 0.0468 | -0.0181 | 2.481 | 0 |
| short_pulse_1ns_high | ngspice_v2_kd_only | VALUE_MATCH_AMBIGUOUS | 27.774 | 0.02881 | 0.72436 | 0.0475 | 0.0465 | -0.0191 | 2.481 | 0 |
| short_pulse_1ns_high | ngspice_v2_split | VALUE_MATCH_AMBIGUOUS | 26.069 | 0.03036 | 0.63570 | 0.0275 | 0.0468 | 0.9978 | 2.481 | 0 |
| short_pulse_2ns_high | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 0.8251 | 0.5432 | -0.0720 | n/a | n/a |
| short_pulse_2ns_high | hspice_transistor_sp | PAD_REFERENCE | 399.310 | n/a | n/a | 1.2145 | n/a | n/a | n/a | n/a |
| short_pulse_2ns_high | ngspice_legacy | CHECK | 361.362 | 0.28330 | 0.23142 | 1.5214 | 1.0125 | -0.0724 | n/a | n/a |
| short_pulse_2ns_high | ngspice_value_matched_v1 | NUMERIC_FAIL | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| short_pulse_2ns_high | ngspice_v2_balanced | VALUE_MATCH_AMBIGUOUS | 243.549 | 0.15234 | 0.58037 | 0.3060 | 0.2808 | -0.0192 | 1.871 | 0 |
| short_pulse_2ns_high | ngspice_v2_ku_only | VALUE_MATCH_AMBIGUOUS | 250.305 | 0.16776 | 0.43359 | 0.3060 | 0.2808 | -0.0192 | 1.871 | 0 |
| short_pulse_2ns_high | ngspice_v2_kd_only | VALUE_MATCH_AMBIGUOUS | 267.274 | 0.16579 | 0.66451 | 0.3060 | 0.2808 | 0.0534 | 1.871 | 0 |
| short_pulse_2ns_high | ngspice_v2_split | VALUE_MATCH_AMBIGUOUS | 267.336 | 0.16776 | 0.66450 | 0.3060 | 0.2808 | 0.0534 | 1.871 | 0 |
| double_toggle_1ps | hspice_native_ibis | REFERENCE | n/a | n/a | n/a | 1.5447 | 1.0024 | -0.0064 | n/a | n/a |
| double_toggle_1ps | hspice_transistor_sp | PAD_REFERENCE | 233.892 | n/a | n/a | 1.5009 | n/a | n/a | n/a | n/a |
| double_toggle_1ps | ngspice_legacy | CHECK | 567.523 | 0.45138 | 0.62934 | 1.1926 | 0.7684 | 0.0092 | n/a | n/a |
| double_toggle_1ps | ngspice_value_matched_v1 | VALUE_MATCH_AMBIGUOUS | 265.210 | 0.23326 | 0.35997 | 1.4402 | 0.9235 | 0.0045 | 1.871 | 0.00959 |
| double_toggle_1ps | ngspice_v2_balanced | VALUE_MATCH_AMBIGUOUS | 566.841 | 0.45030 | 0.62627 | 1.1924 | 0.7678 | 0.0104 | 1.871 | 0 |
| double_toggle_1ps | ngspice_v2_ku_only | VALUE_MATCH_AMBIGUOUS | 566.841 | 0.45030 | 0.62627 | 1.1924 | 0.7678 | 0.0104 | 1.871 | 0 |
| double_toggle_1ps | ngspice_v2_kd_only | VALUE_MATCH_AMBIGUOUS | 566.841 | 0.45030 | 0.62627 | 1.1924 | 0.7678 | 0.0104 | 1.871 | 0 |
| double_toggle_1ps | ngspice_v2_split | VALUE_MATCH_AMBIGUOUS | 566.841 | 0.45030 | 0.62627 | 1.1924 | 0.7678 | 0.0104 | 1.871 | 0 |

## HSPICE Reference Cache

| Case | Reference | Source |
|---|---|---:|
| edge_1ps_base_50r_2pf | hspice_native_ibis | cache |
| edge_1ps_base_50r_2pf | hspice_transistor_sp | cache |
| short_pulse_500ps_high | hspice_native_ibis | cache |
| short_pulse_500ps_high | hspice_transistor_sp | cache |
| short_pulse_1ns_high | hspice_native_ibis | cache |
| short_pulse_1ns_high | hspice_transistor_sp | cache |
| short_pulse_2ns_high | hspice_native_ibis | cache |
| short_pulse_2ns_high | hspice_transistor_sp | cache |
| double_toggle_1ps | hspice_native_ibis | cache |
| double_toggle_1ps | hspice_transistor_sp | cache |

## Interpretation Rule

Pad-only improvement is not enough. V2 must remove the `VMARG` timer backstep and improve `Ku` and `Kd` agreement. If `TF_KU` and `TF_KD` still disagree strongly, the case remains `VALUE_MATCH_AMBIGUOUS` even when ngspice completes.
