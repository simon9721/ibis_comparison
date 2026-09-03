# HSPICE short-pulse comparison: slow IBIS, fast IBIS, transistor

Existing HSPICE references were restored from cache. For the newly added
`short_pulse_2ns_low` case, the regenerated-IBIS and original-transistor
references were simulated once; the old slow-IBIS result was reused.

## Common bench

- All three candidates run in HSPICE.
- Ideal `3.3 V` supply and enable.
- Runtime command rise/fall time: `1 ps`.
- Direct output load: `50 ohm` to ground in parallel with `2 pF` external capacitance.
- Both IBIS files contain typical `C_comp = 1.2 pF`.
- Temperature: `27 C`.
- No channel or transmission line.

## Cases

- `short_pulse_1ns_high`: high command from `5 ns` to `6 ns`.
- `short_pulse_2ns_high`: high command from `5 ns` to `7 ns`.
- `short_pulse_1ns_low`: settled high, then low command from `10 ns` to `11 ns`.
- `short_pulse_2ns_low`: settled high, then low command from `10 ns` to `12 ns`.

## Pad results

| Case | Flow | RMSE vs transistor | Peak | Minimum | Recovery delay after reverse |
|---|---|---:|---:|---:|---:|
| 1 ns high pulse | HSPICE IBIS: old slow-characterized file | 25.0 mV | 0.0616 V | -0.0111 V | n/a |
| 1 ns high pulse | HSPICE IBIS: regenerated 5 ps file | 12.5 mV | 0.0475 V | -0.0124 V | n/a |
| 1 ns high pulse | HSPICE transistor: io_buf.sp | 0.0 mV | 0.0957 V | -0.0408 V | n/a |
| 2 ns high pulse | HSPICE IBIS: old slow-characterized file | 199.2 mV | 0.8251 V | -0.0111 V | n/a |
| 2 ns high pulse | HSPICE IBIS: regenerated 5 ps file | 20.5 mV | 0.9140 V | -0.0124 V | n/a |
| 2 ns high pulse | HSPICE transistor: io_buf.sp | 0.0 mV | 1.0075 V | -0.0125 V | n/a |
| 1 ns low pulse after settled high | HSPICE IBIS: old slow-characterized file | 410.4 mV | 1.5539 V | 0.0008 V | 1.455 ns |
| 1 ns low pulse after settled high | HSPICE IBIS: regenerated 5 ps file | 612.5 mV | 1.6203 V | 0.0141 V | 0.090 ns |
| 1 ns low pulse after settled high | HSPICE transistor: io_buf.sp | 0.0 mV | 1.5988 V | -0.0356 V | 1.778 ns |
| 2 ns low pulse after settled high | HSPICE IBIS: old slow-characterized file | 381.0 mV | 1.5539 V | 0.0008 V | 2.346 ns |
| 2 ns low pulse after settled high | HSPICE IBIS: regenerated 5 ps file | 318.5 mV | 1.6203 V | 0.0009 V | 0.812 ns |
| 2 ns low pulse after settled high | HSPICE transistor: io_buf.sp | 0.0 mV | 1.5988 V | -0.0191 V | 1.793 ns |

## Findings

- The regenerated 5 ps IBIS is the correct complete-edge source-correlation pair, but that does not guarantee transistor-equivalent interrupted switching.
- For the `1 ns high` pulse, all outputs are small. The transistor peaks earlier and higher than either IBIS result, so small absolute voltage error is not proof of matching internal history.
- For the `2 ns high` pulse, regenerated IBIS is closer to the transistor than the old IBIS in both peak amplitude and overall waveform.
- For the `1 ns low` pulse, regenerated IBIS recovers far too early. The old slow IBIS happens to be closer in recovery timing, but this comes from its stored complete-edge delay and should not be interpreted as a generally correct short-pulse model.
- For the `2 ns low` pulse, regenerated IBIS remains early while the old slow IBIS becomes late relative to the transistor. Neither fixed complete-edge replay captures the width-dependent recovery law.
- Slow versus fast IBIS still have identical static drive strength; these differences are entirely dynamic.

## Figures

- `plots/01_short_pulse_1ns_high_pad_overlay.png`
- `plots/02_short_pulse_2ns_high_pad_overlay.png`
- `plots/03_short_pulse_1ns_low_pad_overlay.png`
- `plots/04_short_pulse_2ns_low_pad_overlay.png`
- `plots/05_short_pulse_rmse_summary.png`
- `plots/06_short_low_recovery_timing.png`
- `plots/contact_sheet.png`

## Numeric data

- `short_pulse_metrics.csv`
- `aligned_short_pulse_waveforms.csv`
- `reference_manifest.csv`

## Model sources

- Old IBIS: `C:\Users\sh3qm\code\ibis_comparison\hspice\sparam\io_buf.ibs` (`6c4b8b0a75c4000626d17a3cf1006cb26cb92d619d22d0e3b9860fb948d6076a`).
- Regenerated IBIS: `C:\Users\sh3qm\code\ibis_comparison\results\io_buf_fast_edge_retest_2026-06-05\source\io_buf.ibs` (`1794e5cec67a8710cb3bbdb149f7ef442251e3eb573a2245b304b4663669b149`).
- Transistor: `C:\Users\sh3qm\code\ibis_comparison\models\io_buf.sp` with `C:\Users\sh3qm\code\s2ibispy\tests\hspice.mod`.
