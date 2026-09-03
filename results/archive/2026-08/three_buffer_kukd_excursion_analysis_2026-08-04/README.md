# Three-Buffer Ku/Kd Excursion Audit

This report uses cached long-transition waveforms only; no simulator was run.

## Finding

- `GUP/GDN` are capacitor-backed normalized hidden states and remain inside 0 to 1.
- `Ku/Kd` are effective multipliers applied to static IBIS pullup/pulldown I/V curves. They are not probabilities or physical gate voltages, so the IBIS decomposition does not require them to remain inside 0 to 1.
- The excursions are already present in the HSPICE native-IBIS coefficients. They are strongest for fast `io_buf`, moderate for `ex2`, and small for `inv_chain`.
- The coefficient extraction solves a two-fixture current-balance system. Fast `dV/dt`, `C_comp` subtraction, clamp current, and mismatch between dynamic transistor behavior and static I/V tables can require a coefficient below 0 or above 1.
- The gate-state model clamps the hidden state before applying its directional PWL map, but it intentionally does not clip the mapped coefficient. Its rate residual can also add a signed `dG/dt` correction. Clipping would erase the native negative Kd excursion that the reconstruction gate was designed to preserve.

## Files

- `plots/three_buffer_kukd_excursions_vs_gate_states.png`
- `coefficient_excursion_summary.csv`

The plotted traces are copied from `results/three_buffer_gup_gdn_waveforms_2026-08-04/source_data`.
