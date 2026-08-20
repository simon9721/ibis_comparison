# Data Figure Editor

This is a small desktop editor for CSV-backed Matplotlib figures. It is intended for changing presentation details without rewriting plotting scripts while keeping the result reproducible.

## Launch

```powershell
scripts\launch_figure_editor.cmd
```

You can also open a data file immediately:

```powershell
scripts\launch_figure_editor.cmd results\some_study\waveform_data\case.csv
```

## Editable Properties

- X column and plotted Y columns
- Trace label, color, line width/style, marker, alpha, visibility, and layer order
- Title and axis labels
- Title, label, tick, and legend font sizes
- Font family and linear/log/symmetric-log axis scales
- Axis limits, grid, legend position/columns, canvas size, background, and DPI
- Transparent-background export
- Trace order, which also controls drawing order

The Matplotlib toolbar supplies interactive zoom, pan, home/reset, and quick-save controls.

## Reproducibility

Use **Save Recipe** to write a JSON file. The recipe stores the source CSV and every style choice. It can be reopened in the GUI or rendered without opening the GUI:

```powershell
py -3.14 tools\figure_editor\figure_editor.py my_figure.json --render my_figure.svg
```

PNG is convenient for slides. SVG or PDF is preferable when a final vector edit is needed in PowerPoint, Inkscape, or Illustrator.

## Scope

The editor intentionally handles one axes and one CSV per recipe. Study runners already write aligned waveform CSVs, so this covers the normal overlay workflow without hiding the data transformation. Multi-panel scientific figures should remain script-generated, then each important panel can be exported as a dedicated CSV-backed figure when manual styling is needed.
