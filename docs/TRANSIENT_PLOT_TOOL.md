# Transient Plot Tool

Use `scripts/transient_plot.py` for future transient waveform plots instead of
creating one-off plotting scripts for each experiment.

The tool supports:

- HSPICE ASCII `.tr0` files
- ngspice binary `.raw` files
- Xyce `.csv` / `.prn` output files
- single-waveform plots
- multi-waveform overlays
- one or more zoom windows
- optional full-transient panel plus zoom panels
- optional delta panels against a selected reference trace
- optional CSV metrics for each trace/window
- signal listing for unfamiliar output files

## Trace Syntax

Each waveform is passed with `--trace`:

```text
path|signal|label|fmt
```

Fields:

- `path`: waveform file path
- `signal`: signal name, such as `v(n10b)` or `v(tx_out)`
- `label`: legend label
- `fmt`: `auto`, `hspice`, `ngspice`, or `xyce`

Only `path` is mandatory if `--signal` provides a default signal.  The format is
usually inferred from the extension, but explicit format is recommended for
clarity in saved commands.

PowerShell treats parentheses specially in bare arguments, so quote node names
when using `--signal` directly:

```powershell
--signal "v(n10b)"
```

Inside a quoted `--trace` string, no extra quoting is needed.

## List Signals

```powershell
python scripts\transient_plot.py `
  --list-signals hspice\native_ibis_exp1\tb_exp1.tr0 `
  --fmt hspice
```

## Single Plot

```powershell
python scripts\transient_plot.py `
  --trace "ngspice_pybis\tb_pybis_prbs7_new50ohm.raw|v(n10b)|ngspice pybis|ngspice" `
  --window 30ns 80ns `
  --out results\my_plot.png
```

## Overlay With Full View, Zoom, And Metrics

```powershell
python scripts\transient_plot.py `
  --trace "ngspice_refspice\tb_refspice_prbs7_new50ohm_batch.raw|v(n10b)|ngspice refspice|ngspice" `
  --trace "xyce_refspice\tb_refspice_prbs7_new50ohm_xyce.cir.csv|v(n10b)|Xyce refspice|xyce" `
  --include-full `
  --window 30ns 80ns `
  --diff-to 0 `
  --out results\ngspice_xyce_overlay.png `
  --metrics-out results\ngspice_xyce_overlay_metrics.csv
```

`--diff-to 0` means trace index 0 is the reference.  Difference panels are
plotted in mV, and the metrics CSV includes RMSE and max absolute error for
each non-reference trace.

## Spike/Zoom Example

```powershell
python scripts\transient_plot.py `
  --trace "results\pybis_spike_trend_sweep_2026-05-12\runs\hist_h1_g1_p3_30cm_loss5\xyce_ref\hist_h1_g1_p3_30cm_loss5_xyce_ref.cir.csv|v(n10b)|Xyce refspice|xyce" `
  --trace "results\pybis_spike_trend_sweep_2026-05-12\runs\hist_h1_g1_p3_30cm_loss5\xyce_pybis\hist_h1_g1_p3_30cm_loss5_xyce_pybis.cir.csv|v(n10b)|Xyce pybis|xyce" `
  --trace "results\pybis_spike_trend_sweep_2026-05-12\runs\hist_h1_g1_p3_30cm_loss5\ngspice_pybis_corrected\hist_h1_g1_p3_30cm_loss5_ngspice_pybis_corrected.raw|v(n10b)|ngspice pybis corrected|ngspice" `
  --window 11.5ns 14ns `
  --marker 12.77ns:rise-spike `
  --diff-to 0 `
  --out results\spike_overlay.png `
  --metrics-out results\spike_overlay_metrics.csv
```

## Tested Smoke Cases

The tool was tested against real files from all three simulator families.

Output folder:

- `results/transient_plot_tool_validation_2026-05-13/`

Generated examples:

- `ngspice_single_with_zoom.png`
- `xyce_single_zoom.png`
- `hspice_single_zoom.png`
- `ngspice_xyce_refspice_overlay_diff.png`
- `spike_case_overlay_diff.png`
- `hspice_ngspice_xyce_format_smoke_overlay.png`
- `default_signal_trace_smoke.png`

The same folder includes metrics CSV files for each generated plot.

## Companion Eye Review Tooling

The reusable transient utility is paired with `scripts/eye_diagram.py` for eye
review PNGs.  During the 2026-05-13 review work, the eye tool gained:

- `--eye-out` for writing an eye diagram to an exact PNG path
- `--no-transitions` for suppressing the transition zoom PNG
- `--no-metrics` for suppressing the metrics CSV
- brighter overlay eyes with adaptive opacity and higher DPI

Example:

```powershell
python scripts\eye_diagram.py ngspice_refspice\tb_refspice_prbs7_new50ohm_batch.raw `
  --fmt ngspice `
  --signal "v(n10b)" `
  --ui 5e-9 `
  --skip_ui 10 `
  --n_ui 2 `
  --center_x `
  --mode overlay `
  --eye-out results\review\eye_ngspice_refspice.png `
  --no-transitions `
  --no-metrics
```

## Notes

- Large files are decimated with a min/max envelope method, so narrow spikes are
  preserved better than with simple stride decimation.
- Time strings support `s`, `ms`, `us`, `ns`, `ps`, and `fs`.
- Signal names are resolved case-insensitively and support both `node` and
  `v(node)` forms where possible.
- The HSPICE parser expects ASCII `.tr0` output.
