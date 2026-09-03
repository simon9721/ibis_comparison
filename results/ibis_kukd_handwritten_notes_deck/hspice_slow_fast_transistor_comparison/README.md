# HSPICE slow/fast IBIS versus source transistor

This is a cached-data-only figure package for the IBIS Ku/Kd meeting deck. No
simulation was rerun. All waveforms come from the same HSPICE study and the
same electrical bench.

## Compared models

- Old slow-characterized native IBIS: `C:\Users\sh3qm\code\ibis_comparison\hspice\sparam\io_buf.ibs`.
- Regenerated 5 ps native IBIS: `C:\Users\sh3qm\code\ibis_comparison\results\io_buf_fast_edge_retest_2026-06-05\source\io_buf.ibs`.
- Source transistor: `C:\Users\sh3qm\code\ibis_comparison\models\io_buf.sp` with the original HSPICE model card
  `C:\Users\sh3qm\code\s2ibispy\tests\hspice.mod`.

## Common test bench

- Simulator: HSPICE for all three flows.
- Supply and enable: ideal `3.3 V`.
- Input: `0 -> 3.3 V` at `5 ns`, held high until `15 ns`, then returned low.
- Runtime input rise/fall: `1 ps`.
- Termination: `50 ohm` to ground in parallel with `2 pF` external capacitance.
- IBIS internal capacitance: `C_comp = 1.2 pF` typical in both IBIS files.
- Temperature: `27 C`.
- No channel or transmission line is present in this direct-load comparison.

## Timing result

| Flow | Rise t50 | Error vs transistor | Fall t50 | Error vs transistor |
|---|---:|---:|---:|---:|
| Source transistor | 1.8516 ns | reference | 0.3117 ns | reference |
| Old slow IBIS | 2.3629 ns | +511.3 ps | 0.9397 ns | +628.0 ps |
| Regenerated 5 ps IBIS | 1.8606 ns | +9.0 ps | 0.3156 ns | +3.9 ps |

The fast IBIS follows the source transistor closely. The old model stores a
large timing offset in its V-T waveform tables; this is not a static
drive-strength difference.

## Drive strength

At the `50 ohm` loaded-high operating point:

| Flow | Settled high | Load current | Effective pullup resistance |
|---|---:|---:|---:|
| Old slow IBIS | 1.5447 V | 30.895 mA | 56.81 ohm |
| Regenerated 5 ps IBIS | 1.5447 V | 30.895 mA | 56.81 ohm |
| Source transistor | 1.5447 V | 30.893 mA | 56.82 ohm |

The old and fast IBIS files have the same static I-V tables and therefore the
same static pullup strength. This bench quantifies pullup strength; it does not
independently extract a static pulldown resistance.

## Figures

- `plots/01_full_pulse_overlay.png`
- `plots/02_rising_edge_overlay.png`
- `plots/03_falling_edge_overlay.png`
- `plots/04_timing_error_vs_transistor.png`
- `plots/05_pullup_drive_strength.png`
- `plots/06_stored_vt_timing_source.png`
- `plots/contact_sheet.png`

## Numeric data

- `comparison_summary.csv`
- `aligned_waveforms.csv`
- `driver_strength.csv`
- `source_manifest.csv`

## Short-pulse extension

The matched three-flow short-pulse comparison is under `short_pulse_cases/`.
It covers `1 ns high`, `2 ns high`, and `1 ns low` using cached HSPICE data.
