# io_buf Gate-State Mapping Evidence

Cached/table-derived evidence only; no HSPICE or ngspice simulation was run.

Files:

- `01_original_tables_vs_gate_mapped_time.png`: original complete-edge Ku(t)/Kd(t) tables versus coefficients reconstructed from GUP(t)/GDN(t). Purple traces show the hidden state. For Kd, both the core directional map and final residual-corrected coefficient are shown.
- `02_directional_gate_transfer_maps.png`: the actual directional PWL maps. Black/gray points are original table samples paired with reconstructed gate state; colored curves are the fitted maps written to SPICE.
- `gate_mapping_time_data.csv`: numerical time, gate state, original coefficient, core mapped coefficient, and residual-corrected coefficient.
- `gate_transfer_map_points.csv`: exact PWL state/coefficient points for the four directional maps.

Interpretation:

1. Delay and tau reconstruct continuous GUP/GDN trajectories from complete-edge tables.
2. Original coefficient samples are paired with those state values.
3. Separate on/off maps are required because the same state can imply different coefficient strength by direction.
4. Ku uses the directional map directly. The best current Kd adds a dynamic residual to the core Kd(GDN) map.
