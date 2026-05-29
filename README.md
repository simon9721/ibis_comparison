# IBIS_Comparison

This project compares several flows for the same `io_buf` driver family:

- HSPICE native IBIS results
- transistor-level `io_buf.sp` in ngspice and Xyce
- `pybis2spice` conversion plus ngspice and Xyce

The current accepted benchmark is PRBS7 through the new 50 ohm RLGC channel,
with physical clock-folded eye plots generated from the transient output.

## Layout

- `models/`
  Source models shared by simulator decks: `io_buf.ibs`, `io_buf.sp`, and
  `hspice_ngspice.mod`.
- `channels/`
  Shared legacy channel snippets that are not local to one simulator folder.
- `hspice/native_ibis_exp1/`
  Historical HSPICE native-IBIS Exp 1 deck and `.tr0/.lis/.st0/.ic0` outputs.
- `ngspice_refspice/` and `xyce_refspice/`
  Transistor-level `io_buf.sp` reference benches.
- `ngspice_pybis/` and `xyce_pybis/`
  Converted pybis/minimum-modification benches and outputs.
- `scripts/`
  Runners, plotting tools, regression checks, and analysis helpers.
- `results/`
  Accepted comparison bundles and generated review artifacts.
- `plots/`
  Older plot output kept for reference.
- `docs/reports/`
  Detailed status reports and historical findings.
- `docs/references/`
  Local PDF manuals and papers. These are ignored by git.
- `eye/`
  Local ignored eye-tool reference workspace.
- `experiments/`
  Local ignored scratch/HSPICE workspace.

## Where To Start

- Current plan: [ibis_comparison_plan.md](C:/Users/simom/Desktop/IBIS_Comparison/ibis_comparison_plan.md)
- Detailed progress report: [docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md](C:/Users/simom/Desktop/IBIS_Comparison/docs/reports/IBIS_COMPARISON_PROGRESS_REPORT_2026-05-11.md)
- Pybis stressed-channel behavior summary: [docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md](C:/Users/simom/Desktop/IBIS_Comparison/docs/reports/PYBIS_TWO_BEHAVIORS_2026-05-13.md)
- Transient/eye review summary: [docs/reports/TRANSIENT_EYE_REVIEW_2026-05-13.md](C:/Users/simom/Desktop/IBIS_Comparison/docs/reports/TRANSIENT_EYE_REVIEW_2026-05-13.md)
- Reusable transient plotting tool: [docs/TRANSIENT_PLOT_TOOL.md](C:/Users/simom/Desktop/IBIS_Comparison/docs/TRANSIENT_PLOT_TOOL.md)
- Reusable ngspice CLI/GUI testbench tool: [docs/ngspice_lab.md](C:/Users/simom/Desktop/Projects/IBIS_Comparison/docs/ngspice_lab.md)
- Current review plot bundle: [results/transient_review_plots_2026-05-13/README.md](C:/Users/simom/Desktop/IBIS_Comparison/results/transient_review_plots_2026-05-13/README.md)
- Accepted benchmark bundle: [results/final_prbs_rlgc_comparison_2026-05-11/README.md](C:/Users/simom/Desktop/IBIS_Comparison/results/final_prbs_rlgc_comparison_2026-05-11/README.md)
- Xyce pybis ladder bundle: [results/xyce_pybis_minmod_ladder_2026-05-11/README.md](C:/Users/simom/Desktop/IBIS_Comparison/results/xyce_pybis_minmod_ladder_2026-05-11/README.md)

## Current Commands

```powershell
python scripts\run_accepted_prbs_rlgc_regression.py
python scripts\run_xyce_pybis_minmod_ladder.py
python scripts\transient_plot.py --list-signals hspice\native_ibis_exp1\tb_exp1.tr0 --fmt hspice
& 'C:\Users\simom\Desktop\Projects\spice\pybis2spice\.venv\Scripts\python.exe' scripts\ngspice_lab.py gui
```

Useful direct tool examples:

```powershell
python scripts\eye_diagram.py hspice\native_ibis_exp1\tb_exp1.tr0 --signal v(n10b) --ui 5e-9
python scripts\check_ibis.py
```

## Current Summary

- ngspice and Xyce both run the transistor-level `io_buf.sp` PRBS/RLGC accepted
  benchmark and agree closely.
- ngspice pybis is stable for the accepted PRBS/RLGC comparison.
- Xyce pybis needs the documented minimum-modification/tail-fix setup for the
  accepted benchmark.
- HSPICE native IBIS historical `.tr0` files exist, but a matched HSPICE +
  transistor-level `io_buf.sp` run is still deferred.
