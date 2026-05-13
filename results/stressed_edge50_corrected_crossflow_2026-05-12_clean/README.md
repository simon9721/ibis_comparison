# Corrected stressed edge50 cross-flow transient run

Clean rerun for PRBS7-80, UI=2 ns, 30 cm coarse10 RLGC, loss x5.

The ngspice pybis flow uses a syntax translation of the Xyce edge50_flat4p2 model, not the current polarity-only ngspice_pybis/driver_OutputInput_Typical.sub variant.

Corrected ngspice model: `results/stressed_edge50_corrected_crossflow_2026-05-12_clean/models/driver_OutputInput_Typical_relaxed92_edge50_tailflat4p2_ngspice_syntax.sub`

| Flow | Simulator | Model | Return | Output |
|---|---|---|---:|---:|
| ngspice_refspice | ngspice | io_buf.sp | 0 | True |
| ngspice_pybis_edge50_corrected | ngspice | pybis edge50 translated from Xyce model | 0 | True |
| xyce_refspice | Xyce | io_buf.sp | 0 | True |
| xyce_pybis_edge50 | Xyce | pybis edge50_flat4p2 | 0 | True |


## Plots

- `plots/ui2_len30cm_loss5_coarse10_corrected_transient_overlay_all_visible.png`: all four corrected transient waves, with dashed/dotted styles so overlap does not hide traces.
- `plots/ui2_len30cm_loss5_coarse10_corrected_transient_pair_overlays.png`: refspice pair and pybis pair, each shown separately and zoomed.
- `plots/ui2_len30cm_loss5_coarse10_corrected_transient_deltas.png`: voltage deltas for refspice pair and pybis pair.

## Metrics

See `transient_pair_metrics.csv`. Metrics use a common 10 ps interpolation grid after skipping the first 20 ns startup region.

Key values:

- ngspice refspice vs Xyce refspice: 8.25 mV RMSE.
- corrected ngspice pybis edge50 vs Xyce pybis edge50: 11.67 mV RMSE.

## Provenance

See `variant_provenance_notes.md` for why the current `ngspice_pybis/driver_OutputInput_Typical.sub` polarity-only selector was excluded from the corrected overlay.
