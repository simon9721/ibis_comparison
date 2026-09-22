# Vector-Fit Side Overlays

Study folder: `results\sparam_vector_fit_campaign_v1_2026-06-12_expanded_pilot`
Correlation CSV: `results\sparam_vector_fit_campaign_v1_2026-06-12_expanded_pilot\plots\side_overlays\vector_fit_side_overlay_cases.csv`

- RX-side figures: `6`
- TX-side figures: `6`
- Total figures: `12`

Each figure compares HSPICE native S-parameter simulation against ngspice running the exported vector-fit `.sp` model.

The y-axis uses the signal scale instead of a tight residual scale, so small millivolt-level errors do not look artificially huge.

For very low-swing RX outputs, plots switch to mV scale with a 1 mV minimum span. That is why the Ch10 RX figures now show the small HSPICE pulse instead of appearing as a flat zero line.

## Cases Included

- `Clarity_example_4ef781de`, `raw_vector_3r3c_lin`: selected vector-fit case. Frequency fit/passivity looked good, ngspice smoke downgraded it to `WARN`, and HSPICE shows it works better at the slow `500 ps` edge than at `5 ps` / `50 ps`.
- `Ch10_35_5F3N_f4_cdb7d8f1`, `raw_vector_12r12c_lin`: forced demo case. It was not selected because full S-matrix/reflection error failed the gates. It is useful for showing quality variation: RX-path frequency fit was very small, but the RX waveform is also extremely low swing and the full/reflection fit is poor.

## Files

- `rx/`
- `tx/`
- `index.csv`
- `testbenches/`

`testbenches/` may contain copied vector-fit `.sp` models, HSPICE decks, ngspice decks, and Touchstone inputs used to produce the figures.
