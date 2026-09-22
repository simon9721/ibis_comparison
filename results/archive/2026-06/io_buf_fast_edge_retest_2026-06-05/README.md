# io_buf Fast-Edge Regeneration Retest

Source IBIS:
`\\minerfiles.mst.edu\dfs\users\sh3qm\Desktop\out\io_buf.ibs`

Local copy:
`results/io_buf_fast_edge_retest_2026-06-05/source/io_buf.ibs`

## HSPICE Native IBIS vs HSPICE SPICE

The regenerated IBIS file was tested with the same RSF-style HSPICE comparison used for the previous `io_buf` run:

- Native HSPICE IBIS instance: `io_buf.ibs`, model `driver`
- Reference SPICE: `clean_ibis_vs_pybis_matched_pkg/io_buf.sp`
- Stimulus: 0 V to 3.3 V, 5 ps rise/fall, rise at 1 ns, fall at 9 ns
- Load: 50 ohm transmission line, 30 ps delay, 50 ohm termination

| Node | Native - SPICE rise 50% | Native - SPICE fall 50% | RMSE |
|---|---:|---:|---:|
| pad | +220.26 ps | +13.56 ps | 93.46 mV |
| load | +220.26 ps | +13.52 ps | 93.45 mV |

For comparison, the previous `io_buf` HSPICE native-IBIS result was about +720 ps on rise and +645 ps on fall.

## Files

- `hspice/metrics_summary.csv`: 50% crossing metrics
- `hspice/run_summary.csv`: HSPICE return codes
- `hspice/plots/io_buf_hspice_rsf_pad_overlay.png`: pad overlay
- `hspice/plots/io_buf_hspice_rsf_load_overlay.png`: load overlay
- `hspice/benches/`: generated HSPICE decks and outputs
- `ngspice/metrics_summary.csv`: ngspice pybis vs ngspice refspice 50% crossing metrics
- `ngspice/run_summary.csv`: ngspice return codes
- `ngspice/plots/io_buf_ngspice_pybis_ref_pad_overlay.png`: pad overlay
- `ngspice/plots/io_buf_ngspice_pybis_ref_load_overlay.png`: load overlay
- `ngspice/benches/`: generated ngspice decks, converted subckt, raw files, and logs

## ngspice + pybis Status

The bundled `tools/pybis2spice` copy now includes a local `ecdtools` compatibility parser, so `driver_OutputInput_Typical.sub` can be regenerated on this machine without installing the external `ecdtools` package.

Verified command:

```powershell
py -3 scripts\run_ngspice_pybis_ready_smoke.py
```

This uses `NGSPICE_EXE` if set, otherwise it defaults to:

```text
\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe
```

ngspice pybis vs ngspice refspice metrics:

| Node | pybis - refspice rise 50% | pybis - refspice fall 50% | RMSE |
|---|---:|---:|---:|
| pad | +81.39 ps | +5.75 ps | 32.15 mV |
| load | +81.39 ps | +5.75 ps | 32.15 mV |
