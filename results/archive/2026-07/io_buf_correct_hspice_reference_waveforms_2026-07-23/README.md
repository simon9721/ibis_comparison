# Corrected io_buf HSPICE Reference Waveforms

## Correct Reference Pair

- Native IBIS: `results\io_buf_fast_edge_retest_2026-06-05\source\io_buf.ibs`.
- Transistor source: `models\io_buf.sp`.
- Original HSPICE MOS card: `C:\Users\sh3qm\code\s2ibispy\tests\hspice.mod`.
- Both flows are simulated by HSPICE.
- Runtime stimulus: 3.3 V, 1 ps command edges.
- Load: 50 ohm to ground in parallel with 2 pF.
- Supply: ideal 3.3 V in both flows.

The transistor gate-control traces are shown only as physical context. They are not numerically equivalent to native-IBIS `Ku/Kd`.

## Headline Finding

- Normal complete switching is aligned: native-IBIS versus transistor 50% timing differs by `8.9 ps` on rise and `3.7 ps` on fall.
- The 1 ns short-high output is tiny in both flows. Native IBIS peaks at `0.0475 V`; the transistor peaks at `0.0955 V`. Small absolute error here does not prove state agreement.
- The 2 ns short-high pulse has similar overall shape, with peaks of `0.9140 V` and `1.0068 V`.
- The 1 ns short-low case remains a real disagreement even with corrected sources. Native IBIS crosses 50% on recovery at `11.0892 ns`; the transistor crosses at `12.8119 ns`, a difference of `1.7227 ns`.
- The 2 ns short-low case crosses 50% on recovery at `12.8113 ns` for native IBIS and `13.8090 ns` for the transistor, a difference of `0.9977 ns`.

The corrected result therefore separates two issues. The earlier large complete-edge disagreement was a stale-reference problem. The remaining short-low disagreement is an interrupted-transition/history limitation of native IBIS table playback relative to the source transistor.

## Pad Comparison

| Case | RMSE (mV) | Max error (mV) | Native IBIS range (V) | Transistor range (V) |
|---|---:|---:|---:|---:|
| edge_1ps_base_50r_2pf | 27.387 | 98.559 | -0.0124 to 1.6269 | -0.0125 to 1.6139 |
| short_pulse_1ns_high | 22.032 | 69.377 | -0.0124 to 0.0475 | -0.0408 to 0.0955 |
| short_pulse_2ns_high | 30.830 | 153.341 | -0.0124 to 0.9140 | -0.0125 to 1.0068 |
| short_pulse_1ns_low | 354.004 | 1558.920 | -0.0124 to 1.6203 | -0.0355 to 1.5988 |
| short_pulse_2ns_low | 226.079 | 911.544 | -0.0124 to 1.6203 | -0.0191 to 1.5988 |

## Figures

- `figures/correct_pair_pad_contact_sheet.png`
- `figures/<case>/01_correct_pair_pad_overlay.png`
- `figures/<case>/02_internal_switching_context.png`

## Numeric Data

- `waveform_metrics.csv`
- `reference_cache_manifest.csv`
- `source_manifest.csv`
- `cases/<case>/aligned_correct_pair_waveforms.csv`

Every HSPICE flow retains its exact `.sp`, `.tr0`, `.lis`, and stdout log under `cases/`.
