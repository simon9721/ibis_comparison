# Figure Editor Demo

- `editable_overlay_recipe.json`: reusable styling recipe.
- `editable_overlay.png`: PNG rendered from the recipe.
- `editable_overlay_cli.svg`: vector export rendered headlessly from the same recipe.
- `campaign_recipe_render.svg`: vector export from an automatically generated realistic-pulse campaign recipe.

Open the recipe in the editor:

```powershell
scripts\launch_figure_editor.cmd results\figure_editor_demo_2026-07-30\editable_overlay_recipe.json
```

The source data remains the aligned waveform CSV from the three-buffer comparison study. Change trace color, line weight, label, draw order, fonts, axes, legend, grid, or canvas size, then save a new recipe and export.
