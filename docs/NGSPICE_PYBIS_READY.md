# ngspice + pybis Local Setup

This repo's bundled `tools/pybis2spice` copy is ready to use on this machine with Python 3 and the downloaded ngspice executable.

## What Is Configured

- `tools/pybis2spice/ecdtools/`: a local compatibility parser for the subset of `ecdtools` used by `pybis2spice`.
- `scripts/convert_ibis_to_pybis.py`: converts an IBIS model to an ngspice-ready pybis subcircuit.
- `scripts/run_ngspice_pybis_ready_smoke.py`: regenerates the `io_buf` pybis subcircuit, runs the ngspice pybis and ngspice refspice RSF benches, and writes metrics/plots.

## Commands

Convert a model:

```powershell
py -3 scripts\convert_ibis_to_pybis.py results\io_buf_fast_edge_retest_2026-06-05\source\io_buf.ibs --component "MCM Driver 1" --model driver --out results\io_buf_fast_edge_retest_2026-06-05\ngspice\driver_OutputInput_Typical.sub --list
```

Run the smoke test:

```powershell
py -3 scripts\run_ngspice_pybis_ready_smoke.py
```

The smoke test uses `NGSPICE_EXE` when set. If unset, it uses:

```text
\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe
```

Latest verified outputs are under:

```text
results\io_buf_fast_edge_retest_2026-06-05\ngspice
```
