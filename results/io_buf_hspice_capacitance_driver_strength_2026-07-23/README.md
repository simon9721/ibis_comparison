# io_buf HSPICE Capacitance and Driver-Strength Investigation

## What Was Tested

- Long 1 ps-edge pulse, 3.3 V supply.
- External capacitance: `1 fF` through `10 pF`, with a `50 ohm` load.
- Resistive load: `25`, `50`, `100`, `200`, and `1000 ohm`, with `2 pF`.
- HSPICE native IBIS.
- HSPICE native IBIS using the regenerated 5 ps-characterization file.
- Direct transistor `io_buf.sp` using the original HSPICE model card used to generate the IBIS file.
- The same transistor with the existing 1 ohm supply fixture.
- The previous transistor reference using the ngspice-modified MOS model card.

## Baseline Finding: 50 ohm || 2 pF

- Old slow-file native-IBIS 50% rise delay: `2.3629 ns`.
- Regenerated 5 ps-file native-IBIS 50% rise delay: `1.8606 ns`.
- Direct transistor, original model and ideal supply: `1.8516 ns`.
- Previous transistor reference: `1.6612 ns`.
- Old-file native-versus-correct-transistor delay gap: `511.3 ps`.
- Regenerated-file native-versus-correct-transistor delay gap: `9.0 ps`.
- Previous gap: `701.7 ps`.
- The 1 ohm supply fixture changes 50% delay by only `-7.4 ps`.
- Changing from the original MOS card to the ngspice-modified card changes it by `-183.0 ps`.

Two stale-reference effects were present. The previous HSPICE transistor reference used a MOS card modified for ngspice numerical behavior, and the short-pulse studies selected `hspice/sparam/io_buf.ibs`, which is the old slow-edge IBIS file. The original HSPICE MOS card and the regenerated 5 ps IBIS file are the appropriate pair for this audit.

## Direct Stored-Table Source Check

- Old IBIS first rising V-T table 50% time: `2.2468 ns`.
- Regenerated 5 ps IBIS first rising V-T table 50% time: `1.7439 ns`.
- Cached direct transistor characterization, original model and 5 ps input: `1.7444 ns`.

The regenerated stored table and its direct transistor source agree within `0.5 ps`. The old file stores the slower response directly; this is not a transient initialization artifact.

## Driver Strength

At 50 ohm:

- Native IBIS settled high: `1.5447 V`; effective pullup resistance: `56.81 ohm`.
- Regenerated native IBIS settled high: `1.5447 V`; effective pullup resistance: `56.81 ohm`.
- Original-model transistor settled high: `1.5447 V`; effective pullup resistance: `56.82 ohm`.
- Previous modified-model transistor settled high: `1.6036 V`; effective pullup resistance: `52.89 ohm`.

The load sweep in `plots/04_driver_strength_load_sweep.png` shows the nonlinear pullup drive curve directly. Static strength and dynamic delay are separate checks.

## Capacitance Diagnosis

For external capacitance up to 2 pF, the fitted 50% delay laws are:

- Native IBIS: `2.2488 ns + 0.0572 ns/pF * Cload`.
- Regenerated 5 ps native IBIS: `1.7455 ns + 0.0576 ns/pF * Cload`.
- Original-model transistor: `1.7461 ns + 0.0523 ns/pF * Cload`.
- Difference in capacitance slope: `+0.0049 ns/pF`.
- Regenerated-file difference in capacitance slope: `+0.0053 ns/pF`.

The regenerated-file and correct-transistor capacitance slopes differ by only `0.0053 ns/pF`. Capacitance therefore does not explain the unusual waveform; it exposes the same nearly constant timing offset already stored in the old IBIS V-T tables.

Remember that the IBIS model already contains `C_comp = 1.2 pF`. The sweep values are external capacitance added to both models; `1 fF` is the practical near-zero external-load point.

## Conclusion

- The unusual HSPICE comparison was primarily a reference-selection problem: an old slow-characterized IBIS file was compared with a transistor deck using a different, modified MOS card.
- With the regenerated 5 ps IBIS and the original HSPICE MOS card, the 50 ohm || 2 pF rise and fall gaps are only `9.0 ps` and `3.9 ps`.
- Static pullup strength also agrees: `56.81 ohm` effective IBIS output resistance versus `56.82 ohm` for the source transistor.
- External capacitance from 1 fF to 10 pF behaves consistently in the regenerated IBIS and source transistor; it is not the root cause.
- Earlier short-pulse results remain valid measurements of the old file's playback behavior, but the core short-pulse baseline must be repeated with the regenerated 5 ps IBIS before drawing production conclusions.

## Figures

- `plots/01_baseline_model_card_supply_decomposition.png`
- `plots/02_capacitance_delay_and_slew.png`
- `plots/03_capacitance_endpoint_waveforms.png`
- `plots/04_driver_strength_load_sweep.png`
- `plots/05_internal_switching_timing.png`
- `plots/06_stored_vt_table_vs_source_transistor.png`

## Data

- `metrics.csv`: every flow/capacitance/load measurement.
- `delay_fit_summary.csv`: low-capacitance delay intercept and slope.
- Every run keeps its `.sp`, `.tr0`, `.lis`, and stdout log under `runs/`.
