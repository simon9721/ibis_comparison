This folder is a clean, self-contained IBIS vs pybis comparison for the simple RSF validation case.

Contents:
- `t2b_0615_v5.ibs`: source IBIS file
- `driver2_OutputInput_Typical.sub`: converted pybis2spice ngspice model
- `InvChainSubCkt_loadC.sp`: original transistor-level source reference deck
- `invchain_ref_ngspice.sub`: ngspice-friendly transistor-level reference subckt
- `HL18G-S3.7S.lib`: device model library used by the reference SPICE run
- `tb_ibis_vs_pybis_rsf_6p5n_batch.sp`: local ngspice bench
- `tb_refspice_rsf_7n_batch.sp`: local ngspice bench for the original transistor-level reference SPICE
- `plot_ibis_vs_pybis_rsf.py`: local overlay script
- `plots/`: generated PNGs

Important consistency notes:
- The copied `driver2_OutputInput_Typical.sub` has package `R/L/C = 0`, matching the `[Package]` section in `t2b_0615_v5.ibs`.
- The chosen IBIS source is `t2b_0615_v5.ibs` because it is the direct T2B-generated `driver2` model that matches the original inverter-chain reference behavior. The alternate `driver3` IBIS file in `inv_chain/` is active-low and has different `C_comp`, so it was not used for this clean comparison.

This bench uses:
- a rise-steady-fall input
- a matched `50 ohm`, `30 ps` observation line
- the IBIS waveform blocks with `R_fixture = 50` and `V_fixture = 0`

Run ngspice from this folder:

```powershell
..\..\..\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe -b -r tb_ibis_vs_pybis_rsf_6p5n_batch.raw tb_ibis_vs_pybis_rsf_6p5n_batch.sp
..\..\..\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe -b -r tb_refspice_rsf_7n_batch.raw tb_refspice_rsf_7n_batch.sp
```

Then generate the plots:

```powershell
..\..\..\spice\pybis2spice\.venv\Scripts\python.exe plot_ibis_vs_pybis_rsf.py
```

Expected outputs:
- `plots/refspice_vs_pybis_vs_ibis_rsf_pad.png`
- `plots/refspice_vs_pybis_vs_ibis_rsf_rise_zoom.png`
- `plots/refspice_vs_pybis_vs_ibis_rsf_fall_zoom.png`
- `plots/refspice_vs_pybis_rsf_load.png`
