# pybis2spice Snapshot Validation

This snapshot was copied from the working `C:\Users\simom\Desktop\spice\pybis2spice` tree on 2026-05-20.

## Why this copy exists

The goal is to keep a local, project-adjacent converter snapshot that matches the ngspice comparison work in this repository.

In particular, this snapshot includes the ngspice input-driven output path that follows the SPISim-style runtime flow:

- precomputed waveform-derived `Ku/Kd`
- runtime edge detection from the real input
- runtime elapsed-time extraction using short T-lines
- runtime `Ku/Kd` lookup from elapsed time

## Relevant converter capabilities in this snapshot

- `subcircuit_type="NgSpice"`
- `subcircuit_type="InputDriven"`

The input-driven model exposes:

- `OUT IN EN VCC VSS`

and is the intended path for PRBS/channel simulation in ngspice.

This snapshot also includes:

- backward-compatible aliases for the old ngspice input-driven names
- batch conversion helper:
  - `subcircuit.generate_spice_models_for_all_models(...)`

The GUI default subcircuit choice is now the input-driven path, and the GUI also includes a
`Create All Models` action for batch conversion across all models in the selected IBIS file/component.

## Validation performed

### Automated tests

From the source tree, the following passed:

- `python -m unittest`
- `python -m compileall pybis2spice gui test`

The current unit-test count is `19`.

Unit coverage now includes:

- path-stable test IBIS loading
- scalar `V_fixture` fallback handling
- capture of `enable`, `vinl`, and `vinh`
- exact-zero package `R/L/C` preservation
- tolerant parsing for IBIS numeric tokens like `.133pF`
- ngspice generic model syntax rewrite smoke
- input-driven model text generation
- input-driven fallback for input-model generation
- batch conversion for all models on a selected component
- input-driven ngspice end-to-end smoke simulation

### Project-level correlation work

The same converter code was also exercised in the `IBIS_Comparison` validation work, including:

- simple `R_fixture=50`, `V_fixture=0` IBIS-vs-pybis comparisons
- refspice / pybis / IBIS overlays
- timing-offset constancy study across simple and channel benches

## Notes

- This is a vendor-style snapshot, not a git clone.
- No virtual environment is included here.
- Use the existing Python environment from the main workspace when running tests or conversions.
