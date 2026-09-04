This folder is a clean, self-contained IBIS vs pybis comparison for the simple RSF validation case.

Contents:
- `io_buf.ibs`: source IBIS file
- `driver_OutputInput_Typical.sub`: converted pybis2spice ngspice model
- `io_buf.sp`: original transistor-level reference SPICE netlist
- `hspice_ngspice.mod`: ngspice-compatible MOS model deck used by the reference SPICE run
- `tb_ibis_vs_pybis_rsf_12n_batch.sp`: local ngspice bench
- `tb_refspice_rsf_14n_batch.sp`: local ngspice bench for the original transistor-level reference SPICE
- `plot_ibis_vs_pybis_rsf.py`: local overlay script
- `plots/`: generated PNGs

Important consistency note:
- The copied `driver_OutputInput_Typical.sub` has package `R/L/C = 0`, matching the `[Package]` section in `io_buf.ibs`.

This bench uses:
- a rise-steady-fall input
- a matched `50 ohm`, `30 ps` observation line
- the IBIS waveform blocks with `R_fixture = 50` and `V_fixture = 0`

Run ngspice from this folder:

```powershell
..\..\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe -b -r tb_ibis_vs_pybis_rsf_12n_batch.raw tb_ibis_vs_pybis_rsf_12n_batch.sp
..\..\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe -b -r tb_refspice_rsf_14n_batch.raw tb_refspice_rsf_14n_batch.sp
```

Then generate the plots:

```powershell
..\..\spice\pybis2spice\.venv\Scripts\python.exe plot_ibis_vs_pybis_rsf.py
```

Expected outputs:
- `plots/refspice_vs_pybis_vs_ibis_rsf_pad.png`
- `plots/refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png`
- `plots/refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png`
- `plots/refspice_vs_pybis_rsf_load.png`
