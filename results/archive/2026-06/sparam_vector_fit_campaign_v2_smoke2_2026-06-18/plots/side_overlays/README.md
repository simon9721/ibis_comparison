# Vector-Fit Side Overlays

Study folder: `results\sparam_vector_fit_campaign_v2_smoke2_2026-06-18`
Correlation CSV: `results\sparam_vector_fit_campaign_v2_smoke2_2026-06-18\vf_hspice_correlation.csv`

- RX-side figures: `3`
- TX-side figures: `3`
- Total figures: `6`

Each figure compares HSPICE native S-parameter simulation against ngspice running the exported vector-fit `.sp` model.

The y-axis uses the signal scale instead of a tight residual scale, so small millivolt-level errors do not look artificially huge.

## Files

- `rx/`
- `tx/`
- `index.csv`
- `testbenches/`

`testbenches/` may contain copied vector-fit `.sp` models, HSPICE decks, ngspice decks, and Touchstone inputs used to produce the figures.
