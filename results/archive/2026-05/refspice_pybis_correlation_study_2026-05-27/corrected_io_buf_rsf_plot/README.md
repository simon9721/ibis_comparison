# Corrected continuous RSF io_buf plots

These plots match the visual style of `clean_ibis_vs_pybis_matched_pkg/plots/refspice_vs_pybis_rsf_load.png`: one continuous rise-steady-fall timeline.

The corrected refspice source is the 1 ns input-slew `io_buf.sp` run. In that raw file the fall starts at 10 ns because of SPICE `PULSE` semantics. For review, the falling segment is remapped to 9 ns so the plot has the same RSF structure as the original clean package: rise at 1 ns, steady high, fall at 9 ns.

This is a plotting/remapping step only; the source raw data is unchanged.
