# Corrected io_buf refspice vs pybis plot set

This folder mirrors the plot set from `clean_ibis_vs_pybis_matched_pkg/plots`, but uses the corrected `io_buf.sp` refspice run with a 1 ns input rise/fall slew.

The plots are edge-aligned to input transition start. This is intentional: the corrected refspice deck uses a 1 ns input slew, while the pybis run is the direct `io_buf.ibs` table-replay comparison. Absolute RSF time would put the falling edges at different times and make the overlay misleading.

Generated plots:

- `refspice_vs_pybis_vs_ibis_rsf_pad.png`
- `refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png`
- `refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png`
- `refspice_vs_pybis_rsf_load.png`
- `ibis_vs_pybis_rsf_pad.png`
- `ibis_vs_pybis_rsf_rise_zoom.png`
- `ibis_vs_pybis_rsf_fall_zoom.png`
- `corrected_io_buf_plot_metrics.csv`
