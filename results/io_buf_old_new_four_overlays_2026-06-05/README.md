# io_buf Old/New Overlay Figures

Four presentation figures comparing the old slow `io_buf.ibs` and regenerated fast-edge `io_buf.ibs`.
Each figure shows the pad waveform over the full rise-then-fall interval plus rise/fall detail panels.

| Figure | Rise delta | Fall delta | RMSE |
|---|---:|---:|---:|
| `results/io_buf_old_new_four_overlays_2026-06-05/01_ngspice_old_slow_io_buf_pybis_vs_refspice.png` | +580.8 ps | +639.0 ps | 350.6 mV |
| `results/io_buf_old_new_four_overlays_2026-06-05/02_hspice_old_slow_io_buf_ibis_vs_spice.png` | +720.2 ps | +645.2 ps | 389.1 mV |
| `results/io_buf_old_new_four_overlays_2026-06-05/03_ngspice_new_fast_io_buf_pybis_vs_refspice.png` | +81.4 ps | +5.7 ps | 32.2 mV |
| `results/io_buf_old_new_four_overlays_2026-06-05/04_hspice_new_fast_io_buf_ibis_vs_spice.png` | +220.3 ps | +13.6 ps | 93.5 mV |

## Additional New-IBIS Figures

- `results/io_buf_old_new_four_overlays_2026-06-05/05_new_io_buf_all_four_ngspice_hspice_overlay.png`: all four new-IBIS pad curves, two from ngspice and two from HSPICE.
- `results/io_buf_old_new_four_overlays_2026-06-05/06_new_io_buf_ngspice_pybis_vs_hspice_ibis.png`: focused ngspice-pybis vs HSPICE-native-IBIS comparison.

For the focused comparison, ngspice pybis minus HSPICE native IBIS is +16.1 ps on rise and +2.8 ps on fall.

## Test Bench Equivalence Notes

Old-vs-new comparisons use the same bench topology within each simulator. The ngspice old/new pybis and refspice decks are byte-identical; the HSPICE old/new decks differ only in title comments. The transistor reference files `io_buf.sp` and `hspice_ngspice.mod` are also identical across the old/new runs. The intentional changes are the IBIS file and the generated pybis subcircuit.

The benches are not identical across simulator/model families:

- ngspice pybis and HSPICE native-IBIS runs drive the IBIS-style model directly with a 5 ps PWL input, 3.3 V supply, and a 50 ohm / 30 ps transmission-line load.
- ngspice/HSPICE refspice runs drive `io_buf.sp` with a 5 ps PULSE through a 1 ohm input resistor, use 1 ohm isolated VDD/OE sources, and include a 10 pF VDD decap before the same 50 ohm / 30 ps load.
- ngspice pybis and ngspice refspice use different ngspice tolerances because the transistor deck needs a looser convergence setup.
- HSPICE uses `.option post=2 probe accurate`; HSPICE reports `runlvl=5` when `accurate` is enabled.

The most important result-impacting difference is the simulator/refspice axis. For the new IBIS run, ngspice pybis and HSPICE native IBIS agree closely at the pad, but HSPICE refspice crosses the 50% threshold about 155 ps earlier than ngspice refspice on the rising edge. So cross-simulator overlays should be read as diagnostic, not as perfectly controlled A/B benches.
